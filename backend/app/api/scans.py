"""Scan job API endpoints."""

import asyncio
import math

from fastapi import APIRouter, HTTPException, Query
from app.database.sqlite import get_db
from app.conflict.scanner import run_scan, create_scan_job
from app.models.conflict import ScanJobResponse, ScanJobListResponse

router = APIRouter(prefix="/api/scans", tags=["Scans"])


@router.post("/start", status_code=202)
async def start_scan(threshold: float = Query(0.85, ge=0.5, le=1.0)):
    """Start an offline conflict scan.

    The scan runs asynchronously in the background. Use GET /api/scans/{id}
    to poll for progress.
    """
    scan_id = create_scan_job(threshold=threshold)
    asyncio.create_task(run_scan(scan_id, threshold=threshold))
    return {
        "scan_id": scan_id,
        "status": "pending",
        "message": "Scan started. Poll GET /api/scans/{scan_id} for progress.",
    }


@router.get("", response_model=ScanJobListResponse)
async def list_scans(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
):
    """List scan jobs, most recent first."""
    db = get_db()
    total = db.execute("SELECT COUNT(*) as cnt FROM scan_jobs").fetchone()["cnt"]
    pages = max(1, math.ceil(total / per_page))

    offset = (page - 1) * per_page
    rows = db.execute(
        "SELECT * FROM scan_jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (per_page, offset),
    ).fetchall()

    items = [ScanJobResponse(**dict(r)) for r in rows]
    return ScanJobListResponse(items=items, total=total, page=page, pages=pages)


@router.get("/{scan_id}", response_model=ScanJobResponse)
async def get_scan(scan_id: str):
    """Get scan job status and progress."""
    db = get_db()
    row = db.execute("SELECT * FROM scan_jobs WHERE id = ?", (scan_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return ScanJobResponse(**dict(row))
