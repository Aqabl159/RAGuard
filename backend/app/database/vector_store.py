"""Simple in-process vector store backed by SQLite + numpy.

Replaces Chroma for reliability on Windows. Embeddings are stored as
binary BLOBs in a SQLite table. Cosine similarity is computed via numpy.
"""

import struct
import numpy as np

from app.database.sqlite import get_db
from app.config import settings


def _ensure_table():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS vectors (
            id TEXT PRIMARY KEY,
            embedding BLOB NOT NULL,
            document_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL DEFAULT 0,
            filename TEXT DEFAULT ''
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_vectors_doc ON vectors(document_id)")
    db.commit()


def _pack(embedding: list[float]) -> bytes:
    """Pack a list of floats into a binary BLOB."""
    return struct.pack(f"<{len(embedding)}f", *embedding)


def _unpack(blob: bytes) -> list[float]:
    """Unpack a binary BLOB back to a list of floats."""
    n = len(blob) // 4
    return list(struct.unpack(f"<{n}f", blob))


def _to_numpy(embeddings: list[list[float]]) -> np.ndarray:
    arr = np.array(embeddings, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return arr / norms


def add_vectors(
    ids: list[str],
    embeddings: list[list[float]],
    document_id: str,
    chunk_indices: list[int],
    filename: str,
) -> None:
    """Insert multiple vectors into the store."""
    _ensure_table()
    db = get_db()
    for i, eid in enumerate(ids):
        blob = _pack(embeddings[i])
        db.execute(
            "INSERT OR REPLACE INTO vectors (id, embedding, document_id, chunk_index, filename) VALUES (?, ?, ?, ?, ?)",
            (eid, blob, document_id, chunk_indices[i], filename),
        )
    db.commit()


def delete_by_document(document_id: str) -> None:
    """Remove all vectors for a document."""
    _ensure_table()
    db = get_db()
    db.execute("DELETE FROM vectors WHERE document_id = ?", (document_id,))
    db.commit()


def get_all_vectors() -> tuple[list[str], list[list[float]], list[dict]]:
    """Return (ids, embeddings, metadatas) for all stored vectors."""
    _ensure_table()
    db = get_db()
    rows = db.execute("SELECT id, embedding, document_id, chunk_index, filename FROM vectors").fetchall()
    ids = []
    embeddings = []
    metadatas = []
    for r in rows:
        ids.append(r["id"])
        embeddings.append(_unpack(r["embedding"]))
        metadatas.append({
            "document_id": r["document_id"],
            "chunk_index": r["chunk_index"],
            "filename": r["filename"],
        })
    return ids, embeddings, metadatas


def count_vectors() -> int:
    _ensure_table()
    db = get_db()
    row = db.execute("SELECT COUNT(*) as cnt FROM vectors").fetchone()
    return row["cnt"] if row else 0


def query_similar(query_embedding: list[float], top_k: int = 10) -> list[dict]:
    """Find top-k most similar vectors by cosine similarity.

    Returns list of dicts with: id, score, document_id, filename.
    """
    ids, embeddings, metadatas = get_all_vectors()
    if not embeddings:
        return []

    query_vec = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
    query_vec = query_vec / np.linalg.norm(query_vec)

    store_vecs = _to_numpy(embeddings)
    scores = np.dot(query_vec, store_vecs.T)[0]

    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
        results.append({
            "id": ids[idx],
            "score": float(scores[idx]),
            "document_id": metadatas[idx]["document_id"],
            "filename": metadatas[idx]["filename"],
            "content": "",  # content stored separately in chunks table
        })
    return results


def clear_all() -> None:
    db = get_db()
    db.execute("DELETE FROM vectors")
    db.commit()
