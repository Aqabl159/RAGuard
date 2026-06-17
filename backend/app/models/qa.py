"""QA / Chat related Pydantic schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SourceInfo(BaseModel):
    chunk_id: str
    document_id: str
    document_title: Optional[str] = None
    content: str
    score: float


class ConflictWarningInfo(BaseModel):
    has_conflict: bool
    conflict_ids: list[str] = []
    description: Optional[str] = None
    conflicting_chunks: list[dict] = []


class QAMessageRequest(BaseModel):
    content: str


class QAMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    sources: Optional[list[SourceInfo]] = None
    conflict_warning: Optional[ConflictWarningInfo] = None
    tokens_used: Optional[int] = None
    latency_ms: Optional[int] = None
    created_at: Optional[datetime] = None


class QASessionCreate(BaseModel):
    title: Optional[str] = None


class QASessionResponse(BaseModel):
    id: str
    title: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    message_count: Optional[int] = None


class QASessionListResponse(BaseModel):
    items: list[QASessionResponse]
    total: int
    page: int
    pages: int
