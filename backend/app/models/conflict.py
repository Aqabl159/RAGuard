"""Conflict-related Pydantic schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ConflictChunkInfo(BaseModel):
    chunk_id: str
    document_id: str
    document_title: Optional[str] = None
    content: str
    claim: str
    role: str  # source_a | source_b
    similarity_score: Optional[float] = None


class ConflictResponse(BaseModel):
    id: str
    scan_job_id: Optional[str] = None
    conflict_type: str
    summary: str
    description: Optional[str] = None
    status: str
    severity: str
    detection_method: str = "llm"
    detected_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    # Enriched fields
    source_a: Optional[ConflictChunkInfo] = None
    source_b: Optional[ConflictChunkInfo] = None


class ConflictDetailResponse(ConflictResponse):
    pass


class ConflictListResponse(BaseModel):
    items: list[ConflictResponse]
    total: int
    page: int
    pages: int


class ConflictStatsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    by_severity: dict[str, int]
    by_type: dict[str, int]


class ScanJobResponse(BaseModel):
    id: str
    status: str
    total_pairs: int = 0
    conflict_pairs: int = 0
    conflicts_found: int = 0
    threshold: float = 0.85
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ScanJobListResponse(BaseModel):
    items: list[ScanJobResponse]
    total: int
    page: int
    pages: int
