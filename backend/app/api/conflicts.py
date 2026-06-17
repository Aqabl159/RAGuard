"""Conflict management API endpoints."""

import math
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from app.database.sqlite import get_db
from app.models.conflict import (
    ConflictResponse,
    ConflictDetailResponse,
    ConflictListResponse,
    ConflictStatsResponse,
    ConflictChunkInfo,
)

router = APIRouter(prefix="/api/conflicts", tags=["Conflicts"])


def _row_to_response(row) -> ConflictResponse:
    """Build a ConflictResponse with enriched source_a/source_b info."""
    d = dict(row)
    db = get_db()

    # Fetch associated chunks
    chunks = db.execute(
        """SELECT cc.*, c.content, c.document_id, d.title as document_title
           FROM conflict_chunks cc
           JOIN chunks c ON cc.chunk_id = c.id
           JOIN documents d ON c.document_id = d.id
           WHERE cc.conflict_id = ?
           ORDER BY cc.role""",
        (d["id"],),
    ).fetchall()

    source_a = None
    source_b = None
    for ch in chunks:
        info = ConflictChunkInfo(
            chunk_id=ch["chunk_id"],
            document_id=ch["document_id"],
            document_title=ch["document_title"],
            content=ch["content"][:300] + ("..." if len(ch["content"] or "") > 300 else ""),
            claim=ch["claim"],
            role=ch["role"],
            similarity_score=ch["similarity_score"],
        )
        if ch["role"] == "source_a":
            source_a = info
        else:
            source_b = info

    return ConflictResponse(
        id=d["id"],
        scan_job_id=d.get("scan_job_id"),
        conflict_type=d["conflict_type"],
        summary=d["summary"],
        description=d.get("description"),
        status=d["status"],
        severity=d["severity"],
        detection_method=d.get("detection_method", "llm"),
        detected_at=d.get("detected_at"),
        resolved_at=d.get("resolved_at"),
        source_a=source_a,
        source_b=source_b,
    )


@router.get("", response_model=ConflictListResponse)
async def list_conflicts(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    severity: str | None = Query(None),
    conflict_type: str | None = Query(None),
    sort: str = Query("detected_at:desc"),
):
    """List conflicts with filtering, sorting, and pagination."""
    db = get_db()

    conditions = []
    params = []

    if status:
        conditions.append("c.status = ?")
        params.append(status)
    if severity:
        conditions.append("c.severity = ?")
        params.append(severity)
    if conflict_type:
        conditions.append("c.conflict_type = ?")
        params.append(conflict_type)

    where = " AND ".join(conditions) if conditions else "1=1"

    # Parse sort
    sort_field, sort_dir = sort.split(":") if ":" in sort else (sort, "desc")
    allowed_fields = {"detected_at", "severity", "status", "conflict_type"}
    if sort_field not in allowed_fields:
        sort_field = "detected_at"
    sort_dir = "DESC" if sort_dir.lower() == "desc" else "ASC"

    total = db.execute(
        f"SELECT COUNT(*) as cnt FROM conflicts c WHERE {where}", params
    ).fetchone()["cnt"]
    pages = max(1, math.ceil(total / per_page))

    offset = (page - 1) * per_page
    rows = db.execute(
        f"SELECT c.* FROM conflicts c WHERE {where} ORDER BY c.{sort_field} {sort_dir} LIMIT ? OFFSET ?",
        params + [per_page, offset],
    ).fetchall()

    items = [_row_to_response(r) for r in rows]
    return ConflictListResponse(items=items, total=total, page=page, pages=pages)


@router.get("/stats", response_model=ConflictStatsResponse)
async def get_conflict_stats():
    """Get conflict statistics for dashboard."""
    db = get_db()

    total = db.execute("SELECT COUNT(*) as cnt FROM conflicts").fetchone()["cnt"]

    by_status_rows = db.execute(
        "SELECT status, COUNT(*) as cnt FROM conflicts GROUP BY status"
    ).fetchall()
    by_status = {r["status"]: r["cnt"] for r in by_status_rows}

    by_severity_rows = db.execute(
        "SELECT severity, COUNT(*) as cnt FROM conflicts GROUP BY severity"
    ).fetchall()
    by_severity = {r["severity"]: r["cnt"] for r in by_severity_rows}

    by_type_rows = db.execute(
        "SELECT conflict_type, COUNT(*) as cnt FROM conflicts GROUP BY conflict_type"
    ).fetchall()
    by_type = {r["conflict_type"]: r["cnt"] for r in by_type_rows}

    return ConflictStatsResponse(
        total=total,
        by_status=by_status,
        by_severity=by_severity,
        by_type=by_type,
    )


@router.get("/{conflict_id}", response_model=ConflictDetailResponse)
async def get_conflict(conflict_id: str):
    """Get conflict details including full chunk texts."""
    db = get_db()
    row = db.execute("SELECT * FROM conflicts WHERE id = ?", (conflict_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Conflict not found")

    response = _row_to_response(row)

    # Override with full content
    chunks = db.execute(
        """SELECT cc.*, c.content as full_content, c.document_id, d.title as document_title
           FROM conflict_chunks cc
           JOIN chunks c ON cc.chunk_id = c.id
           JOIN documents d ON c.document_id = d.id
           WHERE cc.conflict_id = ?
           ORDER BY cc.role""",
        (conflict_id,),
    ).fetchall()

    for ch in chunks:
        info = ConflictChunkInfo(
            chunk_id=ch["chunk_id"],
            document_id=ch["document_id"],
            document_title=ch["document_title"],
            content=ch["full_content"],
            claim=ch["claim"],
            role=ch["role"],
            similarity_score=ch["similarity_score"],
        )
        if ch["role"] == "source_a":
            response.source_a = info
        else:
            response.source_b = info

    return response


@router.get("/{conflict_id}/chunks")
async def get_conflict_chunks(conflict_id: str):
    """Get the full chunk pair for a conflict."""
    db = get_db()

    conflict = db.execute("SELECT id FROM conflicts WHERE id = ?", (conflict_id,)).fetchone()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    chunks = db.execute(
        """SELECT cc.*, c.content as full_content, c.document_id, d.title as document_title
           FROM conflict_chunks cc
           JOIN chunks c ON cc.chunk_id = c.id
           JOIN documents d ON c.document_id = d.id
           WHERE cc.conflict_id = ?
           ORDER BY cc.role""",
        (conflict_id,),
    ).fetchall()

    result = {"chunk_a": None, "chunk_b": None, "claims": {"a": "", "b": ""}}
    for ch in chunks:
        side = "chunk_a" if ch["role"] == "source_a" else "chunk_b"
        result[side] = {
            "id": ch["chunk_id"],
            "document_id": ch["document_id"],
            "document_title": ch["document_title"],
            "content": ch["full_content"],
            "claim": ch["claim"],
        }
        if ch["role"] == "source_a":
            result["claims"]["a"] = ch["claim"]
        else:
            result["claims"]["b"] = ch["claim"]

    return result
