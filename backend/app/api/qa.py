"""Q&A / Chat API endpoints."""

import uuid
import time
import math
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.database.sqlite import get_db
from app.qa.router import run_qa_pipeline
from app.models.qa import (
    QAMessageRequest,
    QAMessageResponse,
    QASessionCreate,
    QASessionResponse,
    QASessionListResponse,
)

router = APIRouter(prefix="/api/qa", tags=["QA"])


@router.post("/sessions", status_code=201, response_model=QASessionResponse)
async def create_session(body: QASessionCreate = QASessionCreate()):
    """Create a new QA session."""
    db = get_db()
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO qa_sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (session_id, body.title or "新对话", now, now),
    )
    db.commit()
    return QASessionResponse(id=session_id, title=body.title or "新对话", created_at=now, updated_at=now)


@router.get("/sessions", response_model=QASessionListResponse)
async def list_sessions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List QA sessions, most recent first."""
    db = get_db()
    total = db.execute("SELECT COUNT(*) as cnt FROM qa_sessions").fetchone()["cnt"]
    pages = max(1, math.ceil(total / per_page))

    offset = (page - 1) * per_page
    rows = db.execute(
        "SELECT * FROM qa_sessions ORDER BY updated_at DESC LIMIT ? OFFSET ?",
        (per_page, offset),
    ).fetchall()

    items = []
    for r in rows:
        msg_count = db.execute(
            "SELECT COUNT(*) as cnt FROM qa_messages WHERE session_id = ?", (r["id"],)
        ).fetchone()["cnt"]
        items.append(QASessionResponse(
            id=r["id"], title=r["title"],
            created_at=r["created_at"], updated_at=r["updated_at"],
            message_count=msg_count,
        ))

    return QASessionListResponse(items=items, total=total, page=page, pages=pages)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, messages_limit: int = Query(20, le=100)):
    """Get a session with recent messages."""
    db = get_db()
    session = db.execute("SELECT * FROM qa_sessions WHERE id = ?", (session_id,)).fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.execute(
        "SELECT * FROM qa_messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
        (session_id, messages_limit),
    ).fetchall()

    msg_count = db.execute(
        "SELECT COUNT(*) as cnt FROM qa_messages WHERE session_id = ?", (session_id,)
    ).fetchone()["cnt"]

    import json
    return {
        "session": QASessionResponse(
            id=session["id"], title=session["title"],
            created_at=session["created_at"], updated_at=session["updated_at"],
            message_count=msg_count,
        ),
        "messages": [
            QAMessageResponse(
                id=m["id"], session_id=m["session_id"], role=m["role"],
                content=m["content"],
                sources=json.loads(m["sources"]) if m["sources"] else None,
                conflict_warning=json.loads(m["conflict_warning"]) if m["conflict_warning"] else None,
                tokens_used=m["tokens_used"] if "tokens_used" in m.keys() and m["tokens_used"] else None,
                latency_ms=m["latency_ms"] if "latency_ms" in m.keys() and m["latency_ms"] else None,
                created_at=m["created_at"],
            ) for m in messages
        ],
    }


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str):
    """Delete a QA session and its messages."""
    db = get_db()
    db.execute("DELETE FROM qa_messages WHERE session_id = ?", (session_id,))
    db.execute("DELETE FROM qa_sessions WHERE id = ?", (session_id,))
    db.commit()


@router.post("/sessions/{session_id}/messages")
async def send_message(session_id: str, body: QAMessageRequest):
    """Send a message and get the QA response."""
    db = get_db()
    session = db.execute("SELECT * FROM qa_sessions WHERE id = ?", (session_id,)).fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    start_time = time.time()

    # Save user message
    msg_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    db.execute(
        "INSERT INTO qa_messages (id, session_id, role, content, created_at) VALUES (?, ?, 'user', ?, ?)",
        (msg_id, session_id, body.content, now),
    )

    # Run QA pipeline
    result = await run_qa_pipeline(body.content)
    latency_ms = int((time.time() - start_time) * 1000)

    # Build conflict warning serializable dict
    cw = result.get("conflict_warning")
    conflict_json = None
    if cw:
        conflict_json = {
            "has_conflict": cw.has_conflict,
            "conflict_ids": cw.conflict_ids,
            "description": cw.description,
            "conflicting_chunks": cw.conflicting_chunks,
        }

    # Save assistant message
    import json
    assistant_id = str(uuid.uuid4())
    sources_json = json.dumps(
        [s.model_dump() for s in result["sources"]], ensure_ascii=False
    ) if result.get("sources") else None
    conflict_warning_json = json.dumps(conflict_json, ensure_ascii=False) if conflict_json else None

    db.execute(
        """INSERT INTO qa_messages (id, session_id, role, content, sources, conflict_warning, tokens_used, latency_ms, created_at)
           VALUES (?, ?, 'assistant', ?, ?, ?, ?, ?, ?)""",
        (assistant_id, session_id, result["content"], sources_json, conflict_warning_json,
         len(result["content"]) // 2, latency_ms, now),
    )

    # Update session
    db.execute("UPDATE qa_sessions SET updated_at = ? WHERE id = ?", (now, session_id))
    db.commit()

    return {
        "message": QAMessageResponse(
            id=assistant_id, session_id=session_id, role="assistant",
            content=result["content"],
            sources=result.get("sources"),
            conflict_warning=cw,
            tokens_used=len(result["content"]) // 2,
            latency_ms=latency_ms,
            created_at=now,
        ),
        "answer": result,
    }
