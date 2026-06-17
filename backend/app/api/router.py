"""API router aggregation — mount all sub-routers."""

from fastapi import APIRouter

# Phase 1
from app.api.health import router as health_router
from app.api.documents import router as documents_router

# Phase 2
from app.api.scans import router as scans_router
from app.api.conflicts import router as conflicts_router

# Phase 3
from app.api.resolutions import router as resolutions_router
from app.api.governance import router as governance_router

# Phase 4
from app.api.qa import router as qa_router
from app.api.evaluation import router as evaluation_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(documents_router)
api_router.include_router(scans_router)
api_router.include_router(conflicts_router)
api_router.include_router(resolutions_router)
api_router.include_router(governance_router)
api_router.include_router(qa_router)
api_router.include_router(evaluation_router)
