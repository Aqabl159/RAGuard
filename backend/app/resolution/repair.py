"""Execute repair actions on Chroma and SQLite."""

import uuid
from datetime import datetime

from app.database.sqlite import get_db
from app.database.chroma_client import get_collection
from app.ingestion.embedder import embed_texts


async def apply_repair(
    resolution_id: str,
    proposed_action: str,
    proposed_content: str | None,
    human_modified_content: str | None,
    chunk_a_id: str,
    chunk_b_id: str,
) -> list[dict]:
    """Execute the repair plan.

    Args:
        resolution_id: Resolution record ID.
        proposed_action: One of replace_both, keep_a_remove_b, keep_b_remove_a, merge, manual_rewrite.
        proposed_content: LLM-proposed content for replace/merge actions.
        human_modified_content: Human-modified content (overrides proposed_content if provided).
        chunk_a_id: SQLite chunk ID for source A.
        chunk_b_id: SQLite chunk ID for source B.

    Returns:
        List of repair action result dicts.
    """
    effective_content = human_modified_content or proposed_content
    results = []

    if proposed_action == "keep_a_remove_b":
        results.append(_deactivate_chunk(chunk_b_id))
        results.append(_delete_chunk_from_chroma(chunk_b_id))

    elif proposed_action == "keep_b_remove_a":
        results.append(_deactivate_chunk(chunk_a_id))
        results.append(_delete_chunk_from_chroma(chunk_a_id))

    elif proposed_action == "replace_both":
        if effective_content:
            results.append(_update_chunk_content(chunk_a_id, effective_content))
            results.append(_update_chunk_content(chunk_b_id, effective_content))
            await _update_chroma_embeddings(chunk_a_id, effective_content)
            await _update_chroma_embeddings(chunk_b_id, effective_content)

    elif proposed_action == "merge":
        if effective_content:
            # Create new chunk with merged content
            new_chunk_id = _create_new_chunk(
                chunk_a_id, chunk_b_id, effective_content
            )
            await _create_chroma_embedding(new_chunk_id, effective_content)
            results.append({
                "action_type": "create_chunk",
                "chunk_id": new_chunk_id,
                "old_content": None,
                "new_content": effective_content,
                "success": True,
            })
            # Deactivate old chunks
            results.append(_deactivate_chunk(chunk_a_id))
            results.append(_deactivate_chunk(chunk_b_id))
            results.append(_delete_chunk_from_chroma(chunk_a_id))
            results.append(_delete_chunk_from_chroma(chunk_b_id))

    elif proposed_action == "manual_rewrite":
        if effective_content:
            new_chunk_id = _create_new_chunk(
                chunk_a_id, chunk_b_id, effective_content
            )
            await _create_chroma_embedding(new_chunk_id, effective_content)
            results.append({
                "action_type": "create_chunk",
                "chunk_id": new_chunk_id,
                "old_content": None,
                "new_content": effective_content,
                "success": True,
            })
            results.append(_deactivate_chunk(chunk_a_id))
            results.append(_deactivate_chunk(chunk_b_id))

    # Log all actions to repair_actions table
    db = get_db()
    now = datetime.utcnow().isoformat()
    for r in results:
        action_id = str(uuid.uuid4())
        db.execute(
            """INSERT INTO repair_actions (id, resolution_id, action_type, chunk_id, old_content, new_content, success, executed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                action_id, resolution_id,
                r["action_type"], r.get("chunk_id"),
                r.get("old_content", "")[:500] if r.get("old_content") else None,
                r.get("new_content", "")[:500] if r.get("new_content") else None,
                r.get("success", True),
                now,
            ),
        )
    db.commit()

    return results


def _deactivate_chunk(chunk_id: str) -> dict:
    """Soft-delete a chunk in SQLite."""
    db = get_db()
    db.execute(
        "UPDATE chunks SET is_active = FALSE WHERE id = ?",
        (chunk_id,),
    )
    db.commit()
    return {"action_type": "delete_chunk", "chunk_id": chunk_id, "success": True}


def _delete_chunk_from_chroma(chunk_id: str) -> dict:
    """Remove chunk embedding from Chroma."""
    db = get_db()
    row = db.execute("SELECT chroma_id FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
    if row and row["chroma_id"]:
        try:
            collection = get_collection()
            collection.delete(ids=[row["chroma_id"]])
            return {"action_type": "delete_chunk", "chunk_id": chunk_id, "success": True}
        except Exception as e:
            return {"action_type": "delete_chunk", "chunk_id": chunk_id, "success": False, "error_message": str(e)}
    return {"action_type": "delete_chunk", "chunk_id": chunk_id, "success": True}


def _update_chunk_content(chunk_id: str, new_content: str) -> dict:
    """Update chunk content in SQLite."""
    db = get_db()
    old = db.execute("SELECT content FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
    old_content = old["content"] if old else ""
    db.execute(
        "UPDATE chunks SET content = ? WHERE id = ?",
        (new_content, chunk_id),
    )
    db.commit()
    return {
        "action_type": "update_chunk",
        "chunk_id": chunk_id,
        "old_content": old_content,
        "new_content": new_content,
        "success": True,
    }


async def _update_chroma_embeddings(chunk_id: str, new_content: str):
    """Update chunk content and embedding in Chroma."""
    db = get_db()
    row = db.execute(
        "SELECT chroma_id, document_id FROM chunks WHERE id = ?", (chunk_id,)
    ).fetchone()
    if not row or not row["chroma_id"]:
        return

    doc_row = db.execute(
        "SELECT filename, doc_type FROM documents WHERE id = ?", (row["document_id"],)
    ).fetchone()
    if not doc_row:
        return

    embeddings = await embed_texts([new_content])
    collection = get_collection()

    # Upsert: update if exists, insert if not
    collection.upsert(
        ids=[row["chroma_id"]],
        embeddings=embeddings,
        metadatas=[{
            "document_id": row["document_id"],
            "filename": doc_row["filename"],
            "doc_type": doc_row["doc_type"],
        }],
        documents=[new_content],
    )


async def _create_chroma_embedding(chunk_id: str, content: str):
    """Create a new embedding in Chroma for a new chunk."""
    db = get_db()
    row = db.execute(
        "SELECT document_id FROM chunks WHERE id = ?", (chunk_id,)
    ).fetchone()
    if not row:
        return

    doc_row = db.execute(
        "SELECT filename, doc_type FROM documents WHERE id = ?", (row["document_id"],)
    ).fetchone()

    embeddings = await embed_texts([content])
    collection = get_collection()
    chroma_id = f"{row['document_id']}_chunk_repair_{chunk_id[:8]}"

    collection.add(
        ids=[chroma_id],
        embeddings=embeddings,
        metadatas=[{
            "document_id": row["document_id"],
            "filename": doc_row["filename"] if doc_row else "",
            "doc_type": doc_row["doc_type"] if doc_row else "",
        }],
        documents=[content],
    )

    db.execute("UPDATE chunks SET chroma_id = ? WHERE id = ?", (chroma_id, chunk_id))
    db.commit()


def _create_new_chunk(chunk_a_id: str, chunk_b_id: str, content: str) -> str:
    """Create a new chunk entry in SQLite for merged/rewritten content."""
    db = get_db()
    # Get document info from source chunk A
    row = db.execute(
        "SELECT document_id, chunk_index FROM chunks WHERE id = ?", (chunk_a_id,)
    ).fetchone()
    if not row:
        row = db.execute(
            "SELECT document_id, chunk_index FROM chunks WHERE id = ?", (chunk_b_id,)
        ).fetchone()

    document_id = row["document_id"] if row else ""
    new_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    db.execute(
        """INSERT INTO chunks (id, document_id, content, chunk_index, is_active, token_count, created_at)
           VALUES (?, ?, ?, 9999, TRUE, ?, ?)""",
        (new_id, document_id, content, len(content) // 2, now),
    )
    db.commit()
    return new_id
