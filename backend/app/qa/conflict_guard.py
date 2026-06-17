"""Conflict guard — check if retrieved chunks belong to known open conflicts."""

from app.database.sqlite import get_db
from app.models.qa import ConflictWarningInfo


def check_conflicts(chunk_ids: list[str]) -> ConflictWarningInfo:
    """Check if any of the retrieved chunk IDs belong to open conflicts.

    Uses the v_open_conflict_chunks view for efficient lookup.

    Args:
        chunk_ids: List of chunk IDs from retrieval results.

    Returns:
        ConflictWarningInfo with conflict details if any, else a clean info.
    """
    if not chunk_ids:
        return ConflictWarningInfo(has_conflict=False)

    db = get_db()

    # Query which of our chunk_ids are in open conflicts
    placeholders = ",".join(["?" for _ in chunk_ids])
    rows = db.execute(
        f"""SELECT DISTINCT cc.conflict_id, cc.chunk_id, cc.claim, cc.role, c.summary, c.severity
            FROM conflict_chunks cc
            JOIN v_open_conflict_chunks vocc ON cc.chunk_id = vocc.chunk_id
            JOIN conflicts c ON cc.conflict_id = c.id
            WHERE cc.chunk_id IN ({placeholders})""",
        chunk_ids,
    ).fetchall()

    if not rows:
        return ConflictWarningInfo(has_conflict=False)

    # Aggregate conflict info
    conflict_ids = list(set(r["conflict_id"] for r in rows))
    summaries = list(set(r["summary"] for r in rows))

    conflicting_chunks = []
    for r in rows:
        conflicting_chunks.append({
            "chunk_id": r["chunk_id"],
            "conflict_id": r["conflict_id"],
            "claim": r["claim"],
            "role": r["role"],
        })

    return ConflictWarningInfo(
        has_conflict=True,
        conflict_ids=conflict_ids,
        description="检索到的知识源中存在信息冲突。以下信息可能互相矛盾，请谨慎参考：\n" +
                     "\n".join(f"- {s}" for s in summaries[:3]),
        conflicting_chunks=conflicting_chunks,
    )
