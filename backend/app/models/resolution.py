"""Resolution-related Pydantic schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ResolutionResponse(BaseModel):
    id: str
    conflict_id: str
    graph_thread_id: Optional[str] = None
    proposed_action: str
    proposed_content: Optional[str] = None
    reasoning: str
    status: str
    human_decision: Optional[str] = None
    human_notes: Optional[str] = None
    human_modified_content: Optional[str] = None
    created_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None


class ResolutionListResponse(BaseModel):
    items: list[ResolutionResponse]
    total: int
    page: int
    pages: int


class ApproveRequest(BaseModel):
    action_override: Optional[str] = None


class RejectRequest(BaseModel):
    notes: Optional[str] = None


class ModifyRequest(BaseModel):
    modified_content: str
    modified_action: Optional[str] = None
    notes: Optional[str] = None


class RepairActionResponse(BaseModel):
    id: str
    resolution_id: str
    action_type: str
    chunk_id: Optional[str] = None
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    executed_at: Optional[datetime] = None
    success: bool = True
    error_message: Optional[str] = None


class RepairActionListResponse(BaseModel):
    items: list[RepairActionResponse]
    total: int
    page: int
    pages: int
