"""Governance dashboard API endpoints."""

from fastapi import APIRouter
from app.database.sqlite import get_db
from app.models.resolution import ResolutionResponse

router = APIRouter(prefix="/api/governance", tags=["Governance"])


@router.get("/pending")
async def get_pending_resolutions():
    """Get all resolutions pending human review, with full context."""
    db = get_db()

    rows = db.execute(
        """SELECT r.* FROM resolutions r
           WHERE r.status = 'pending_review'
           ORDER BY r.created_at DESC"""
    ).fetchall()

    results = []
    for row in rows:
        r = dict(row)

        # Get associated conflict
        conflict = db.execute(
            "SELECT * FROM conflicts WHERE id = ?", (r["conflict_id"],)
        ).fetchone()

        # Get chunks
        chunks = db.execute(
            """SELECT cc.*, c.content, c.document_id, d.title as document_title
               FROM conflict_chunks cc
               JOIN chunks c ON cc.chunk_id = c.id
               JOIN documents d ON c.document_id = d.id
               WHERE cc.conflict_id = ?
               ORDER BY cc.role""",
            (r["conflict_id"],),
        ).fetchall()

        results.append({
            "resolution": ResolutionResponse(**r),
            "conflict": dict(conflict) if conflict else None,
            "chunks": [dict(c) for c in chunks],
        })

    return {"items": results, "total": len(results)}


@router.get("/stats")
async def get_governance_stats():
    """Get governance dashboard statistics."""
    db = get_db()

    total = db.execute("SELECT COUNT(*) as cnt FROM conflicts").fetchone()["cnt"]

    by_status = {}
    for row in db.execute("SELECT status, COUNT(*) as cnt FROM conflicts GROUP BY status").fetchall():
        by_status[row["status"]] = row["cnt"]

    by_severity = {}
    for row in db.execute("SELECT severity, COUNT(*) as cnt FROM conflicts GROUP BY severity").fetchall():
        by_severity[row["severity"]] = row["cnt"]

    by_type = {}
    for row in db.execute("SELECT conflict_type, COUNT(*) as cnt FROM conflicts GROUP BY conflict_type").fetchall():
        by_type[row["conflict_type"]] = row["cnt"]

    pending_review = db.execute(
        "SELECT COUNT(*) as cnt FROM resolutions WHERE status = 'pending_review'"
    ).fetchone()["cnt"]

    return {
        "total": total,
        "by_status": by_status,
        "by_severity": by_severity,
        "by_type": by_type,
        "pending_review": pending_review,
    }
