"""Document-related Pydantic schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    filename: str
    title: Optional[str] = None
    doc_type: str = Field(..., pattern="^(pdf|docx|markdown)$")


class DocumentCreate(DocumentBase):
    pass


class DocumentResponse(DocumentBase):
    id: str
    status: str
    page_count: Optional[int] = None
    file_size: Optional[int] = None
    chunk_count: Optional[int] = None
    conflict_count: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    pages: int


class ChunkResponse(BaseModel):
    id: str
    document_id: str
    content: str
    chunk_index: int
    page_number: Optional[int] = None
    token_count: Optional[int] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    # V2 structured metadata
    section_path: Optional[str] = None       # "Policies > Refunds > Conditions"
    heading_level: int = 0                   # 0=no heading, 1=h1, 2=h2, 3=h3
    prev_chunk_id: Optional[str] = None      # Same-document predecessor
    next_chunk_id: Optional[str] = None      # Same-document successor


class ChunkListResponse(BaseModel):
    items: list[ChunkResponse]
    total: int
    page: int
    pages: int
