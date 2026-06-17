"""Document management API endpoints."""

import os
import asyncio
import math
import shutil
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from app.database.sqlite import get_db
from app.ingestion.pipeline import create_document_record, process_document, compute_checksum
from app.models.document import DocumentResponse, DocumentListResponse, ChunkResponse, ChunkListResponse
from app.models.common import ErrorResponse
from app.config import settings

router = APIRouter(prefix="/api/documents", tags=["Documents"])

UPLOAD_DIR = Path("data/uploads")


def _row_to_response(row) -> DocumentResponse:
    """Convert a SQLite row to a DocumentResponse."""
    d = dict(row)
    # Count chunks
    db = get_db()
    chunk_count = db.execute(
        "SELECT COUNT(*) as cnt FROM chunks WHERE document_id = ? AND is_active = TRUE",
        (d["id"],),
    ).fetchone()["cnt"]

    # Count conflicts
    conflict_count = db.execute(
        """SELECT COUNT(DISTINCT cc.conflict_id) as cnt
           FROM conflict_chunks cc
           JOIN chunks c ON cc.chunk_id = c.id
           WHERE c.document_id = ?""",
        (d["id"],),
    ).fetchone()["cnt"]

    return DocumentResponse(
        id=d["id"],
        filename=d["filename"],
        title=d.get("title"),
        doc_type=d["doc_type"],
        status=d["status"],
        page_count=d.get("page_count"),
        file_size=d.get("file_size"),
        chunk_count=chunk_count,
        conflict_count=conflict_count,
        error_message=d.get("error_message"),
        created_at=d.get("created_at"),
        updated_at=d.get("updated_at"),
    )


@router.post("/upload", status_code=201)
async def upload_documents(files: list[UploadFile] = File(...)):
    """Upload and ingest one or more documents.

    Accepts PDF, DOCX, and Markdown files. Maximum 10 files, each up to 20MB.
    Processing happens asynchronously — check document status via GET.
    """
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files per upload")

    results = []
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    for file in files:
        # Validate extension
        ext = Path(file.filename).suffix.lower()
        ext_map = {".pdf": "pdf", ".docx": "docx", ".md": "markdown"}
        if ext not in ext_map:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {ext}. Supported: .pdf, .docx, .md",
            )
        doc_type = ext_map[ext]

        # Read file content
        content = await file.read()
        file_size = len(content)

        if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {file.filename} ({file_size} bytes). Max: {settings.MAX_FILE_SIZE_MB}MB",
            )

        # Save to disk
        safe_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        file_path = UPLOAD_DIR / safe_name
        file_path.write_bytes(content)

        # Compute checksum and create record
        checksum = compute_checksum(str(file_path))

        try:
            doc_id = create_document_record(
                filename=file.filename,
                doc_type=doc_type,
                file_path=str(file_path),
                file_size=file_size,
                checksum=checksum,
            )
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

        # Start async processing
        asyncio.create_task(process_document(doc_id))

        results.append({
            "id": doc_id,
            "filename": file.filename,
            "doc_type": doc_type,
            "status": "pending",
        })

    return {"documents": results}


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    search: str | None = Query(None),
):
    """List documents with optional filtering and pagination."""
    db = get_db()

    conditions = ["status != 'deleted'"]
    params = []

    if status:
        conditions.append("status = ?")
        params.append(status)

    if search:
        conditions.append("(filename LIKE ? OR title LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = " AND ".join(conditions)

    total = db.execute(f"SELECT COUNT(*) as cnt FROM documents WHERE {where}", params).fetchone()["cnt"]
    pages = max(1, math.ceil(total / per_page))

    offset = (page - 1) * per_page
    rows = db.execute(
        f"SELECT * FROM documents WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [per_page, offset],
    ).fetchall()

    items = [_row_to_response(r) for r in rows]

    return DocumentListResponse(items=items, total=total, page=page, pages=pages)


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str):
    """Get a document by ID."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM documents WHERE id = ? AND status != 'deleted'", (doc_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    return _row_to_response(row)


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: str):
    """Soft-delete a document and its chunks."""
    db = get_db()
    row = db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    now = datetime.utcnow().isoformat()

    # Soft-delete chunks
    db.execute("UPDATE chunks SET is_active = FALSE WHERE document_id = ?", (doc_id,))

    # Remove from Chroma
    try:
        from app.database.chroma_client import get_collection
        collection = get_collection()
        chroma_rows = db.execute(
            "SELECT chroma_id FROM chunks WHERE document_id = ?", (doc_id,)
        ).fetchall()
        chroma_ids = [r["chroma_id"] for r in chroma_rows if r["chroma_id"]]
        if chroma_ids:
            collection.delete(ids=chroma_ids)
    except Exception:
        pass

    # Mark document as deleted
    db.execute(
        "UPDATE documents SET status = 'deleted', updated_at = ? WHERE id = ?",
        (now, doc_id),
    )
    db.commit()


@router.get("/{doc_id}/chunks", response_model=ChunkListResponse)
async def list_chunks(
    doc_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """List chunks for a document."""
    db = get_db()

    doc = db.execute("SELECT id FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    total = db.execute(
        "SELECT COUNT(*) as cnt FROM chunks WHERE document_id = ? AND is_active = TRUE",
        (doc_id,),
    ).fetchone()["cnt"]
    pages = max(1, math.ceil(total / per_page))

    offset = (page - 1) * per_page
    rows = db.execute(
        """SELECT * FROM chunks
           WHERE document_id = ? AND is_active = TRUE
           ORDER BY chunk_index LIMIT ? OFFSET ?""",
        (doc_id, per_page, offset),
    ).fetchall()

    items = [ChunkResponse(**dict(r)) for r in rows]
    return ChunkListResponse(items=items, total=total, page=page, pages=pages)


# ────────────────────────────────────────────
# V2: Reindex endpoints (after chunker upgrade)
# ────────────────────────────────────────────

@router.post("/{doc_id}/reindex", status_code=202)
async def reindex_document(doc_id: str):
    """Reindex a single document using the V2 chunker.

    Soft-deletes old chunks, clears Chroma vectors, and re-runs
    the full ingestion pipeline. Marks related conflicts as stale.
    """
    db = get_db()

    doc = db.execute("SELECT * FROM documents WHERE id = ? AND status != 'deleted'", (doc_id,)).fetchone()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc["status"] == "processing":
        raise HTTPException(status_code=409, detail="Document is currently being processed")

    now = datetime.utcnow().isoformat()

    # 1. Soft-delete old chunks
    db.execute("UPDATE chunks SET is_active = FALSE WHERE document_id = ?", (doc_id,))

    # 2. Delete Chroma vectors
    try:
        from app.database.chroma_client import get_collection
        collection = get_collection()
        chroma_rows = db.execute(
            "SELECT chroma_id FROM chunks WHERE document_id = ?", (doc_id,)
        ).fetchall()
        chroma_ids = [r["chroma_id"] for r in chroma_rows if r["chroma_id"]]
        if chroma_ids:
            collection.delete(ids=chroma_ids)
    except Exception:
        pass

    # 3. Mark related conflicts as stale
    db.execute(
        """UPDATE conflicts SET status = 'dismissed', resolved_at = ?
           WHERE id IN (
               SELECT DISTINCT cc.conflict_id
               FROM conflict_chunks cc
               JOIN chunks c ON cc.chunk_id = c.id
               WHERE c.document_id = ?
           ) AND status IN ('open', 'in_review')""",
        (now, doc_id),
    )
    db.commit()

    # 4. Reset document status and re-process
    db.execute(
        "UPDATE documents SET status = 'pending', updated_at = ? WHERE id = ?",
        (now, doc_id),
    )
    db.commit()

    asyncio.create_task(process_document(doc_id))

    return {"status": "accepted", "document_id": doc_id, "message": "Reindexing started"}


@router.post("/reindex-all", status_code=202)
async def reindex_all_documents():
    """Reindex all documents with 'indexed' status using the V2 chunker.

    Processes documents sequentially to avoid overwhelming the embedding API.
    """
    db = get_db()

    rows = db.execute(
        "SELECT id, filename FROM documents WHERE status = 'indexed' ORDER BY created_at"
    ).fetchall()

    if not rows:
        return {"status": "ok", "message": "No indexed documents to reindex", "count": 0}

    doc_list = [{"id": r["id"], "filename": r["filename"]} for r in rows]

    # Kick off background processing
    async def _reindex_all():
        for doc in doc_list:
            try:
                # Soft-delete old chunks
                db.execute("UPDATE chunks SET is_active = FALSE WHERE document_id = ?", (doc["id"],))
                # Clear Chroma
                try:
                    from app.database.chroma_client import get_collection
                    collection = get_collection()
                    chroma_rows = db.execute(
                        "SELECT chroma_id FROM chunks WHERE document_id = ?", (doc["id"],)
                    ).fetchall()
                    chroma_ids = [r["chroma_id"] for r in chroma_rows if r["chroma_id"]]
                    if chroma_ids:
                        collection.delete(ids=chroma_ids)
                except Exception:
                    pass
                # Mark conflicts stale
                now = datetime.utcnow().isoformat()
                db.execute(
                    """UPDATE conflicts SET status = 'dismissed', resolved_at = ?
                       WHERE id IN (
                           SELECT DISTINCT cc.conflict_id
                           FROM conflict_chunks cc
                           JOIN chunks c ON cc.chunk_id = c.id
                           WHERE c.document_id = ?
                       ) AND status IN ('open', 'in_review')""",
                    (now, doc["id"]),
                )
                db.execute(
                    "UPDATE documents SET status = 'pending', updated_at = ? WHERE id = ?",
                    (now, doc["id"]),
                )
                db.commit()
                print(f"[Reindex] Starting reindex for {doc['filename']} ({doc['id']})")
                await process_document(doc["id"])
            except Exception as e:
                print(f"[Reindex] Failed for {doc['filename']}: {e}")

    asyncio.create_task(_reindex_all())

    return {
        "status": "accepted",
        "message": f"Reindexing {len(doc_list)} documents",
        "count": len(doc_list),
        "documents": doc_list,
    }
