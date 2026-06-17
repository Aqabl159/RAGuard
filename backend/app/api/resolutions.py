"""Resolution workflow API endpoints."""

import math
import traceback

from fastapi import APIRouter, HTTPException, Query
from app.database.sqlite import get_db
from app.resolution.state import ResolutionState, ChunkInfo
from app.resolution.graph import run_resolution, execute_decision
from app.models.resolution import (
    ResolutionResponse,
    ResolutionListResponse,
    ApproveRequest,
    RejectRequest,
    ModifyRequest,
    RepairActionResponse,
    RepairActionListResponse,
)

router = APIRouter(prefix="/api", tags=["Resolutions"])


def _load_conflict_for_resolution(conflict_id: str) -> dict:
    """Load conflict + chunk data needed to initialize ResolutionState."""
    db = get_db()

    conflict = db.execute(
        "SELECT * FROM conflicts WHERE id = ?", (conflict_id,)
    ).fetchone()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")

    chunks = db.execute(
        """SELECT cc.*, c.content, c.document_id, d.title as document_title
           FROM conflict_chunks cc
           JOIN chunks c ON cc.chunk_id = c.id
           JOIN documents d ON c.document_id = d.id
           WHERE cc.conflict_id = ?
           ORDER BY cc.role""",
        (conflict_id,),
    ).fetchall()

    chunk_a_raw = next((c for c in chunks if c["role"] == "source_a"), None)
    chunk_b_raw = next((c for c in chunks if c["role"] == "source_b"), None)

    if not chunk_a_raw or not chunk_b_raw:
        raise HTTPException(status_code=400, detail="Conflict has incomplete chunk data")

    return {
        "conflict": dict(conflict),
        "chunk_a": ChunkInfo(
            id=chunk_a_raw["chunk_id"],
            document_id=chunk_a_raw["document_id"],
            document_title=chunk_a_raw["document_title"] or "未知文档",
            content=chunk_a_raw["content"],
            claim=chunk_a_raw["claim"],
        ),
        "chunk_b": ChunkInfo(
            id=chunk_b_raw["chunk_id"],
            document_id=chunk_b_raw["document_id"],
            document_title=chunk_b_raw["document_title"] or "未知文档",
            content=chunk_b_raw["content"],
            claim=chunk_b_raw["claim"],
        ),
    }


@router.post("/conflicts/{conflict_id}/resolve", status_code=202)
async def start_resolution(conflict_id: str):
    """Start the resolution workflow for a conflict.

    Runs the full resolution generation pipeline synchronously and returns
    the resolution ID immediately.
    """
    data = _load_conflict_for_resolution(conflict_id)
    conflict = data["conflict"]

    initial_state: ResolutionState = {
        "conflict_id": conflict_id,
        "chunk_a": data["chunk_a"],
        "chunk_b": data["chunk_b"],
        "conflict_type": conflict["conflict_type"],
        "conflict_summary": conflict["summary"],
        "claims_extracted": False,
        "contradiction_analysis": None,
        "proposed_action": None,
        "proposed_content": None,
        "reasoning": None,
        "resolution_id": None,
        "human_decision": None,
        "human_notes": None,
        "human_modified_content": None,
        "repair_results": [],
        "error": None,
    }

    try:
        resolution_id = await run_resolution(initial_state)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Resolution generation failed: {str(e)}")

    # Fetch the created resolution
    db = get_db()
    row = db.execute("SELECT * FROM resolutions WHERE id = ?", (resolution_id,)).fetchone()
    return {
        "conflict_id": conflict_id,
        "resolution_id": resolution_id,
        "status": "completed",
        "resolution": ResolutionResponse(**dict(row)).model_dump() if row else None,
    }


@router.get("/resolutions/{resolution_id}", response_model=ResolutionResponse)
async def get_resolution(resolution_id: str):
    """Get a resolution by ID."""
    db = get_db()
    row = db.execute("SELECT * FROM resolutions WHERE id = ?", (resolution_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Resolution not found")
    return ResolutionResponse(**dict(row))


@router.get("/resolutions", response_model=ResolutionListResponse)
async def list_resolutions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    conflict_id: str | None = Query(None),
    status: str | None = Query(None),
):
    """List resolutions."""
    db = get_db()

    conditions = []
    params = []

    if conflict_id:
        conditions.append("r.conflict_id = ?")
        params.append(conflict_id)
    if status:
        conditions.append("r.status = ?")
        params.append(status)

    where = " AND ".join(conditions) if conditions else "1=1"

    total = db.execute(
        f"SELECT COUNT(*) as cnt FROM resolutions r WHERE {where}", params
    ).fetchone()["cnt"]
    pages = max(1, math.ceil(total / per_page))

    offset = (page - 1) * per_page
    rows = db.execute(
        f"SELECT r.* FROM resolutions r WHERE {where} ORDER BY r.created_at DESC LIMIT ? OFFSET ?",
        params + [per_page, offset],
    ).fetchall()

    items = [ResolutionResponse(**dict(r)) for r in rows]
    return ResolutionListResponse(items=items, total=total, page=page, pages=pages)


@router.post("/resolutions/{resolution_id}/approve")
async def approve_resolution(resolution_id: str, body: ApproveRequest = ApproveRequest()):
    """Approve a resolution and execute the repair."""
    db = get_db()
    row = db.execute(
        "SELECT r.*, c.id as cid FROM resolutions r "
        "JOIN conflicts c ON r.conflict_id = c.id "
        "WHERE r.id = ?", (resolution_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Resolution not found")
    if row["status"] != "pending_review":
        raise HTTPException(status_code=400, detail=f"Resolution is not pending review (current: {row['status']})")

    # Load chunk IDs from conflict_chunks
    chunks = db.execute(
        "SELECT chunk_id, role FROM conflict_chunks WHERE conflict_id = ? ORDER BY role",
        (row["cid"],),
    ).fetchall()
    chunk_a_id = next((c["chunk_id"] for c in chunks if c["role"] == "source_a"), "")
    chunk_b_id = next((c["chunk_id"] for c in chunks if c["role"] == "source_b"), "")

    try:
        result = await execute_decision(
            resolution_id=resolution_id,
            decision="approved",
            conflict_id=row["cid"],
            chunk_a_id=chunk_a_id,
            chunk_b_id=chunk_b_id,
            proposed_action=row["proposed_action"],
            proposed_content=row["proposed_content"],
            modified_action=body.action_override or "",
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Repair failed: {str(e)}")

    row2 = db.execute("SELECT * FROM resolutions WHERE id = ?", (resolution_id,)).fetchone()
    return {"resolution": ResolutionResponse(**dict(row2)).model_dump(), "result": result}


@router.post("/resolutions/{resolution_id}/reject")
async def reject_resolution(resolution_id: str, body: RejectRequest = RejectRequest()):
    """Reject a resolution and dismiss the conflict."""
    db = get_db()
    row = db.execute(
        "SELECT r.*, c.id as cid FROM resolutions r "
        "JOIN conflicts c ON r.conflict_id = c.id "
        "WHERE r.id = ?", (resolution_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Resolution not found")

    await execute_decision(
        resolution_id=resolution_id,
        decision="rejected",
        conflict_id=row["cid"],
        chunk_a_id="",
        chunk_b_id="",
        proposed_action=row["proposed_action"] or "",
        proposed_content=row["proposed_content"],
        human_notes=body.notes or "",
    )

    row2 = db.execute("SELECT * FROM resolutions WHERE id = ?", (resolution_id,)).fetchone()
    return ResolutionResponse(**dict(row2))


@router.post("/resolutions/{resolution_id}/modify")
async def modify_resolution(resolution_id: str, body: ModifyRequest):
    """Modify a resolution — saves modified content and action."""
    db = get_db()
    row = db.execute(
        "SELECT r.*, c.id as cid FROM resolutions r "
        "JOIN conflicts c ON r.conflict_id = c.id "
        "WHERE r.id = ?", (resolution_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Resolution not found")

    await execute_decision(
        resolution_id=resolution_id,
        decision="modified",
        conflict_id=row["cid"],
        chunk_a_id="",
        chunk_b_id="",
        proposed_action=row["proposed_action"] or "",
        proposed_content=row["proposed_content"],
        human_notes=body.notes or "",
        human_modified_content=body.modified_content,
        modified_action=body.modified_action or "",
    )

    row2 = db.execute("SELECT * FROM resolutions WHERE id = ?", (resolution_id,)).fetchone()
    return ResolutionResponse(**dict(row2))


@router.get("/repair-actions", response_model=RepairActionListResponse)
async def list_repair_actions(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    resolution_id: str | None = Query(None),
    conflict_id: str | None = Query(None),
):
    """List repair actions, optionally filtered by resolution or conflict."""
    db = get_db()

    conditions = []
    params = []

    if conflict_id:
        conditions.append("ra.resolution_id IN (SELECT id FROM resolutions WHERE conflict_id = ?)")
        params.append(conflict_id)
    if resolution_id:
        conditions.append("ra.resolution_id = ?")
        params.append(resolution_id)

    where = " AND ".join(conditions) if conditions else "1=1"

    total = db.execute(
        f"SELECT COUNT(*) as cnt FROM repair_actions ra WHERE {where}", params
    ).fetchone()["cnt"]
    pages = max(1, math.ceil(total / per_page))

    offset = (page - 1) * per_page
    rows = db.execute(
        f"SELECT ra.* FROM repair_actions ra WHERE {where} ORDER BY ra.executed_at DESC LIMIT ? OFFSET ?",
        params + [per_page, offset],
    ).fetchall()

    items = [RepairActionResponse(**dict(r)) for r in rows]
    return RepairActionListResponse(items=items, total=total, page=page, pages=pages)
