"""Health check endpoints."""

from fastapi import APIRouter
from app.database.chroma_client import get_chroma_client
from app.models.common import HealthResponse

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
async def health_check():
    """Overall system health check."""
    services = {}

    # Check Chroma (embedded)
    try:
        client = get_chroma_client()
        # Verify it works by listing collections
        client.list_collections()
        services["chroma"] = "connected"
    except Exception:
        services["chroma"] = "disconnected"

    # Check Langfuse
    try:
        from app.observability.langfuse import get_langfuse_handler
        handler = get_langfuse_handler()
        if handler:
            services["langfuse"] = "configured"
        else:
            services["langfuse"] = "not_configured"
    except Exception:
        services["langfuse"] = "not_configured"

    return HealthResponse(
        status="ok",
        version="0.1.0",
        services=services,
    )


@router.get("/api/health/chroma")
async def chroma_health():
    """Chroma-specific health check."""
    try:
        client = get_chroma_client()
        collections = client.list_collections()
        return {"status": "connected", "collections": len(collections)}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}
