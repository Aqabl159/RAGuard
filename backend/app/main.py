"""RAGuard — FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.formparsers import MultiPartParser

from app.api.router import api_router
from app.database.sqlite import init_db, close_db
from app.config import settings

# Override Starlette's default 1MB multipart upload limit
_original_init = MultiPartParser.__init__

def _patched_init(self, *args, **kwargs):
    kwargs.setdefault("max_part_size", 50 * 1024 * 1024)  # 50MB
    _original_init(self, *args, **kwargs)

MultiPartParser.__init__ = _patched_init


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: initialize DB on startup, close on shutdown."""
    # Startup
    init_db()
    # Initialize Langfuse if configured
    from app.observability.langfuse import get_langfuse_handler
    handler = get_langfuse_handler()
    if handler:
        print(f"[Langfuse] Tracing enabled → {settings.LANGFUSE_HOST}")
    else:
        print("[Langfuse] Not configured — tracing disabled")

    yield

    # Shutdown
    close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="RAGuard",
        description="RAG Knowledge Base Conflict Detection & Auto-Repair Engine",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow frontend dev server and localhost
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:80",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:80",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount all API routes
    app.include_router(api_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
