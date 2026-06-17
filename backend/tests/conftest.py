"""Test fixtures for RAGuard backend."""

import os
import sys
import shutil
import tempfile
import importlib
import pytest

# Ensure backend is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def client():
    """Create FastAPI TestClient with isolated temp database."""
    fd, db_path = tempfile.mkstemp(suffix='.db', prefix='raguard_test_')
    os.close(fd)
    chroma_dir = tempfile.mkdtemp(prefix="chroma_test_")

    # Set env before any app imports
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["DEEPSEEK_API_KEY"] = "test-key"
    os.environ["SILICONFLOW_API_KEY"] = "test-key"
    os.environ["CHROMA_DATA_PATH"] = chroma_dir

    # Reload config to pick up new env
    import app.config
    import app.database.sqlite
    import app.database.chroma_client as chroma_mod
    importlib.reload(app.config)
    importlib.reload(app.database.sqlite)
    importlib.reload(chroma_mod)

    from app.main import app
    from fastapi.testclient import TestClient
    from app.database.sqlite import close_db
    from app.database.chroma_client import reset_collection

    close_db()

    with TestClient(app) as tc:
        yield tc

    # Cleanup
    close_db()
    reset_collection()
    try:
        os.unlink(db_path)
    except OSError:
        pass
    try:
        shutil.rmtree(chroma_dir, ignore_errors=True)
    except OSError:
        pass
