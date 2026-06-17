"""Candidate pair generation via Chroma full scan + cosine similarity."""

import numpy as np
from app.database.chroma_client import get_collection
from app.config import settings


def get_all_embeddings() -> tuple[list[str], list[list[float]], list[dict]]:
    """Fetch all embeddings, ids, and metadata from Chroma collection.

    Returns:
        Tuple of (ids, embeddings, metadatas).
    """
    collection = get_collection()
    result = collection.get(
        include=["embeddings", "metadatas"],
    )
    ids = result["ids"]
    embeddings = result.get("embeddings", [])
    metadatas = result.get("metadatas", [])
    return ids, embeddings, metadatas


def compute_cosine_similarity_matrix(embeddings: list[list[float]]) -> np.ndarray:
    """Compute pairwise cosine similarity matrix.

    Args:
        embeddings: List of embedding vectors.

    Returns:
        N×N upper-triangular similarity matrix.
    """
    if not embeddings:
        return np.array([])

    embs = np.array(embeddings, dtype=np.float32)
    # Normalize
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    embs = embs / norms
    # Dot product = cosine similarity for normalized vectors
    sim_matrix = np.dot(embs, embs.T)
    return sim_matrix


def generate_candidate_pairs(
    threshold: float | None = None,
    top_k_per_chunk: int = 5,
) -> list[dict]:
    """Generate candidate conflict pairs from Chroma collection.

    For each chunk, find the top-k most similar chunks (excluding self).
    Return only pairs above the similarity threshold.

    Args:
        threshold: Minimum cosine similarity (default from settings).
        top_k_per_chunk: Max candidates per chunk.

    Returns:
        List of candidate pair dicts with keys:
        id_a, id_b, content_a, content_b, meta_a, meta_b, similarity.
    """
    threshold = threshold or settings.SIMILARITY_THRESHOLD
    ids, embeddings, metadatas = get_all_embeddings()

    if len(ids) < 2:
        return []

    sim_matrix = compute_cosine_similarity_matrix(embeddings)
    n = len(ids)

    # Also fetch documents for content
    collection = get_collection()
    docs_result = collection.get(ids=ids, include=["documents"])
    documents = docs_result.get("documents", [])

    pairs = []
    seen = set()

    for i in range(n):
        # Get top-k indices sorted by similarity (descending)
        row = sim_matrix[i]
        # Exclude self
        row[i] = -1.0
        top_indices = np.argsort(row)[::-1][:top_k_per_chunk]

        for j in top_indices:
            similarity = float(row[j])
            if similarity < threshold:
                continue

            # Canonical ordering to avoid duplicates
            key = (min(i, j), max(i, j))
            if key in seen:
                continue
            seen.add(key)

            pairs.append({
                "id_a": ids[i],
                "id_b": ids[j],
                "content_a": documents[i] if i < len(documents) else "",
                "content_b": documents[j] if j < len(documents) else "",
                "meta_a": metadatas[i] if metadatas else {},
                "meta_b": metadatas[j] if metadatas else {},
                "similarity": similarity,
            })

    # Sort by similarity descending
    pairs.sort(key=lambda p: p["similarity"], reverse=True)
    return pairs
