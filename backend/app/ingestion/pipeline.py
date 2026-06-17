"""Document ingestion pipeline orchestrator.

V2: Uses structured parser + semantic chunker with section-aware metadata.
"""

import asyncio
import hashlib
import os
import time
import uuid
from pathlib import Path
from datetime import datetime

from app.config import settings
from app.database.sqlite import get_db
from app.database.chroma_client import get_collection
from app.ingestion.parser import parse_document
from app.ingestion.chunker import chunk_document
from app.ingestion.tokenizer import count_tokens
from app.ingestion.embedder import embed_texts


async def process_document(document_id: str) -> None:
    """Full ingestion pipeline for a single document.

    Steps:
    1. Mark document as 'processing'
    2. Parse the file → ParsedDocument (with section tree)
    3. Chunk via semantic-aware chunker → list[ChunkResult]
    4. Generate embeddings
    5. Store chunks + embeddings in Chroma (with V2 metadata)
    6. Store chunks in SQLite (with section_path, heading_level, prev/next links)
    7. Mark document as 'indexed' or 'failed'
    """
    db = get_db()

    # Load document record
    row = db.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
    if not row:
        return

    doc = dict(row)
    file_path = doc["file_path"]
    print(f"[Ingest] Starting processing: {doc['filename']} ({doc['file_size']} bytes)")

    try:
        t0 = time.time()

        # Step 1: Mark as processing
        db.execute(
            "UPDATE documents SET status = 'processing', updated_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), document_id),
        )
        db.commit()
        t1 = time.time()
        print(f"[Ingest] Status set to 'processing' ({t1-t0:.1f}s)")

        # Step 2: Parse (V2: returns ParsedDocument with sections)
        parsed = parse_document(file_path, doc["doc_type"])
        text_len = len(parsed.text)
        section_count = len(parsed.sections)
        t2 = time.time()
        print(f"[Ingest] Parsed {doc['doc_type']}: {text_len} chars, {parsed.page_count} pages, "
              f"{section_count} top-level sections ({t2-t1:.1f}s)")
        if not parsed.text.strip():
            raise ValueError("Document contains no extractable text")

        db.execute(
            """UPDATE documents
               SET title = COALESCE(?, title), page_count = ?, updated_at = ?
               WHERE id = ?""",
            (parsed.title, parsed.page_count, datetime.utcnow().isoformat(), document_id),
        )
        db.commit()

        # Step 3: Chunk (V2: semantic-aware, returns ChunkResult list)
        chunk_results = await chunk_document(parsed)
        t3 = time.time()
        print(f"[Ingest] Split into {len(chunk_results)} chunks ({t3-t2:.1f}s)")
        if not chunk_results:
            raise ValueError("No chunks generated from document")

        # Step 4: Embed
        print(f"[Ingest] Generating embeddings for {len(chunk_results)} chunks...")
        texts = [c.content for c in chunk_results]
        embeddings = await embed_texts(texts)
        t4 = time.time()
        print(f"[Ingest] Got {len(embeddings)} embeddings ({t4-t3:.1f}s)")

        # Step 5: Store in Chroma (V2 metadata: section_path, heading_level, token_count)
        print(f"[Ingest] Storing in Chroma...")
        collection = get_collection()
        chroma_ids: list[str] = []
        chunk_ids: list[str] = []
        metadatas: list[dict] = []

        for cr in chunk_results:
            chunk_id = str(uuid.uuid4())
            chroma_id = f"{document_id}_chunk_{cr.chunk_index}"
            chunk_ids.append(chunk_id)
            chroma_ids.append(chroma_id)
            metadatas.append({
                "document_id": document_id,
                "chunk_index": cr.chunk_index,
                "doc_type": doc["doc_type"],
                "filename": doc["filename"],
                # V2 fields
                "section_path": cr.section_path,
                "heading_level": cr.heading_level,
                "token_count": cr.token_count,
            })

        def _chroma_add():
            collection.add(
                ids=chroma_ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=texts,
            )

        await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, _chroma_add),
            timeout=30.0,
        )
        t5 = time.time()
        print(f"[Ingest] Chroma storage done ({t5-t4:.1f}s)")

        # Fill prev/next links across all chunks in this document
        for i in range(len(chunk_ids)):
            if i > 0:
                chunk_results[i].prev_chunk_id = chunk_ids[i - 1]
            if i < len(chunk_ids) - 1:
                chunk_results[i].next_chunk_id = chunk_ids[i + 1]

        # Step 6: Store chunks in SQLite with V2 metadata
        print(f"[Ingest] Storing chunks in SQLite...")
        now = datetime.utcnow().isoformat()
        for cr, chunk_id, chroma_id in zip(chunk_results, chunk_ids, chroma_ids):
            db.execute(
                """INSERT INTO chunks
                   (id, document_id, content, chunk_index, chroma_id,
                    token_count, section_path, heading_level,
                    prev_chunk_id, next_chunk_id, page_number, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    chunk_id, document_id, cr.content, cr.chunk_index, chroma_id,
                    cr.token_count, cr.section_path, cr.heading_level,
                    cr.prev_chunk_id, cr.next_chunk_id, cr.page_number, now,
                ),
            )

        # Mark as indexed
        db.execute(
            "UPDATE documents SET status = 'indexed', updated_at = ? WHERE id = ?",
            (now, document_id),
        )
        db.commit()
        t6 = time.time()
        print(f"[Ingest] SQLite storage done ({t6-t5:.1f}s)")
        print(f"[Ingest] SUCCESS: {doc['filename']} indexed with {len(chunk_results)} chunks "
              f"(total {t6-t0:.1f}s)")

    except Exception as e:
        import traceback
        traceback.print_exc()
        db.execute(
            "UPDATE documents SET status = 'failed', error_message = ?, updated_at = ? WHERE id = ?",
            (str(e), datetime.utcnow().isoformat(), document_id),
        )
        db.commit()
        print(f"[Ingest] FAILED: {doc['filename']} — {e}")


def create_document_record(
    filename: str,
    doc_type: str,
    file_path: str,
    file_size: int,
    checksum: str,
) -> str:
    """Create a new document record in SQLite and return its ID.

    Also checks for duplicate documents by checksum.
    """
    db = get_db()

    # Check for duplicates
    existing = db.execute(
        "SELECT id, status FROM documents WHERE checksum = ? AND status NOT IN ('deleted', 'failed')",
        (checksum,),
    ).fetchone()
    if existing:
        # If the old document got stuck in 'processing' (e.g. server restart),
        # delete it so the user can re-upload.
        if existing["status"] == "processing":
            db.execute("DELETE FROM documents WHERE id = ?", (existing["id"],))
            db.commit()
        else:
            raise ValueError(
                f"Duplicate document detected (checksum match with document {existing['id']}, "
                f"status: {existing['status']})"
            )

    doc_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    db.execute(
        """INSERT INTO documents
           (id, filename, doc_type, file_path, file_size, checksum, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
        (doc_id, filename, doc_type, file_path, file_size, checksum, now, now),
    )
    db.commit()
    return doc_id


def compute_checksum(file_path: str) -> str:
    """Compute MD5 checksum of a file."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
