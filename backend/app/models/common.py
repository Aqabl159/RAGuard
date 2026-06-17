"""Common/shared Pydantic schemas."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict[str, str]


class ErrorResponse(BaseModel):
    detail: str
    code: str


class PaginationParams(BaseModel):
    page: int = 1
    per_page: int = 20
