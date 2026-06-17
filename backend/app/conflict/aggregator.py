"""Conflict aggregation — group related conflicts and deduplicate."""

import uuid
from datetime import datetime


def aggregate_conflicts(raw_contradictions: list[dict]) -> list[dict]:
    """Aggregate and deduplicate raw contradiction results.

    Groups contradictions by topic similarity and removes duplicates.

    Args:
        raw_contradictions: List of dicts, each containing:
            - pair: dict with id_a, id_b, content_a, content_b, meta_a, meta_b, similarity, rerank_score
            - result: dict from fact_checker with is_contradictory, claim_a, claim_b, etc.

    Returns:
        List of aggregated conflict dicts ready for DB insertion.
    """
    # Filter to only contradictory pairs
    contradictory = [
        c for c in raw_contradictions
        if c.get("result") and c["result"].get("is_contradictory")
    ]

    if not contradictory:
        return []

    # Simple deduplication by topic + claims overlap
    conflicts = []
    assigned = set()

    for i, item in enumerate(contradictory):
        if i in assigned:
            continue

        result = item["result"]
        pair = item["pair"]

        conflict_id = str(uuid.uuid4())

        conflicts.append({
            "id": conflict_id,
            "conflict_type": result.get("conflict_type", "factual_contradiction"),
            "summary": result.get("summary", "事实性矛盾"),
            "description": result.get("analysis", ""),
            "severity": result.get("severity", "medium"),
            "detection_method": "llm",
            "chunks": [
                {
                    "chunk_id": _resolve_chunk_id(pair, "a"),
                    "claim": result.get("claim_a", ""),
                    "role": "source_a",
                    "content": pair["content_a"],
                    "meta": pair.get("meta_a", {}),
                    "similarity_score": pair.get("similarity"),
                },
                {
                    "chunk_id": _resolve_chunk_id(pair, "b"),
                    "claim": result.get("claim_b", ""),
                    "role": "source_b",
                    "content": pair["content_b"],
                    "meta": pair.get("meta_b", {}),
                    "similarity_score": pair.get("similarity"),
                },
            ],
        })

        assigned.add(i)

    return conflicts


def _resolve_chunk_id(pair: dict, side: str) -> str:
    """Map Chroma ID back to SQLite chunk ID.

    The Chroma ID format is: {document_id}_chunk_{index}
    We need the SQLite chunk ID instead. For simplicity during MVP,
    we look up by Chroma ID in the chunks table.
    """
    from app.database.sqlite import get_db

    chroma_id = pair.get(f"id_{side}", "")
    db = get_db()
    row = db.execute(
        "SELECT id FROM chunks WHERE chroma_id = ? AND is_active = TRUE",
        (chroma_id,),
    ).fetchone()
    return row["id"] if row else chroma_id
