"""ChromaDB client — supports local disk (PersistentClient) or Docker HTTP (httpx).

Set CHROMA_HOST=localhost:8001 in .env to switch to Docker-hosted Chroma.
When in HTTP mode, uses direct REST API calls (no chromadb library needed).
"""

from __future__ import annotations

import uuid
import httpx
from app.config import settings

_client = None
_collection = None


# ────────────────────────────────────────────
# HTTP mode (Docker) — direct REST API client
# ────────────────────────────────────────────

class _ChromaHttpClient:
    """Minimal Chroma HTTP client using httpx.

    Talks directly to the Chroma v2 REST API.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.tenant = "default_tenant"
        self.database = "default_database"
        self._http = httpx.Client(timeout=30.0)
        self._ensure_database()

    def _ensure_database(self):
        """Create default tenant/database if not exist."""
        try:
            self._http.get(
                f"{self.base_url}/api/v2/tenants/{self.tenant}/databases/{self.database}"
            )
        except Exception:
            # Create database (and implicitly tenant)
            self._http.post(
                f"{self.base_url}/api/v2/tenants/{self.tenant}/databases",
                json={"name": self.database},
            )

    def _col_url(self, collection_id: str) -> str:
        return f"{self.base_url}/api/v2/tenants/{self.tenant}/databases/{self.database}/collections/{collection_id}"

    def get_collection(self, name: str) -> "_ChromaCollection":
        """Get an existing collection by name. Raises if not found."""
        # List collections and find by name
        resp = self._http.get(
            f"{self.base_url}/api/v2/tenants/{self.tenant}/databases/{self.database}/collections"
        )
        resp.raise_for_status()
        data = resp.json()
        for col in data:
            if col.get("name") == name:
                return _ChromaCollection(self, col["id"], name)
        raise Exception(f"Collection '{name}' not found")

    def create_collection(self, name: str, metadata: dict | None = None) -> "_ChromaCollection":
        """Create a new collection."""
        resp = self._http.post(
            f"{self.base_url}/api/v2/tenants/{self.tenant}/databases/{self.database}/collections",
            json={"name": name, "metadata": metadata or {}},
        )
        resp.raise_for_status()
        data = resp.json()
        return _ChromaCollection(self, data["id"], name)

    def delete_collection(self, name: str) -> None:
        """Delete a collection by name."""
        try:
            col = self.get_collection(name)
            self._http.delete(self._col_url(col.id))
            resp = None  # noqa
        except Exception:
            pass

    def list_collections(self) -> list[str]:
        """Return list of collection names."""
        resp = self._http.get(
            f"{self.base_url}/api/v2/tenants/{self.tenant}/databases/{self.database}/collections"
        )
        resp.raise_for_status()
        return [col["name"] for col in resp.json()]

    def close(self):
        self._http.close()


class _ChromaCollection:
    """Lightweight collection handle — wraps REST calls."""

    def __init__(self, client: _ChromaHttpClient, col_id: str, name: str):
        self._client = client
        self.id = col_id
        self.name = name

    def add(
        self,
        ids: list[str],
        embeddings: list[list[float]] | None = None,
        metadatas: list[dict] | None = None,
        documents: list[str] | None = None,
    ) -> None:
        body: dict = {"ids": ids}
        if embeddings is not None:
            body["embeddings"] = embeddings
        if metadatas is not None:
            body["metadatas"] = metadatas
        if documents is not None:
            body["documents"] = documents
        resp = self._client._http.post(
            f"{self._client._col_url(self.id)}/add", json=body
        )
        resp.raise_for_status()

    def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]] | None = None,
        metadatas: list[dict] | None = None,
        documents: list[str] | None = None,
    ) -> None:
        body: dict = {"ids": ids}
        if embeddings is not None:
            body["embeddings"] = embeddings
        if metadatas is not None:
            body["metadatas"] = metadatas
        if documents is not None:
            body["documents"] = documents
        resp = self._client._http.post(
            f"{self._client._col_url(self.id)}/upsert", json=body
        )
        resp.raise_for_status()

    def query(
        self,
        query_embeddings: list[list[float]] | None = None,
        n_results: int = 10,
        include: list[str] | None = None,
    ) -> dict:
        body: dict = {"n_results": n_results}
        if query_embeddings is not None:
            body["query_embeddings"] = query_embeddings
        if include is not None:
            body["include"] = include
        resp = self._client._http.post(
            f"{self._client._col_url(self.id)}/query", json=body
        )
        resp.raise_for_status()
        return resp.json()

    def get(
        self,
        ids: list[str] | None = None,
        include: list[str] | None = None,
    ) -> dict:
        body: dict = {}
        if ids is not None:
            body["ids"] = ids
        if include is not None:
            body["include"] = include
        resp = self._client._http.post(
            f"{self._client._col_url(self.id)}/get", json=body
        )
        resp.raise_for_status()
        return resp.json()

    def delete(self, ids: list[str] | None = None) -> None:
        body: dict = {}
        if ids is not None:
            body["ids"] = ids
        resp = self._client._http.post(
            f"{self._client._col_url(self.id)}/delete", json=body
        )
        resp.raise_for_status()

    def count(self) -> int:
        """Return number of items in the collection."""
        resp = self._client._http.post(
            f"{self._client._col_url(self.id)}/get",
            json={"include": ["metadatas"]},
        )
        resp.raise_for_status()
        data = resp.json()
        return len(data.get("ids", []))

    def modify(self, name: str | None = None, metadata: dict | None = None) -> None:
        body: dict = {}
        if name is not None:
            body["name"] = name
        if metadata is not None:
            body["metadata"] = metadata
        resp = self._client._http.put(
            f"{self._client._col_url(self.id)}", json=body
        )
        resp.raise_for_status()


# ────────────────────────────────────────
# Public API (same interface as before)
# ────────────────────────────────────────

def get_chroma_client():
    """Get or create the ChromaDB client.

    - CHROMA_HOST set       → HTTP client (Docker / remote server)
    - CHROMA_HOST empty     → PersistentClient (local disk, requires chromadb lib)
    """
    global _client
    if _client is None:
        if settings.chroma_use_http:
            _client = _ChromaHttpClient(
                base_url=f"http://{settings.CHROMA_HOST}"
            )
        else:
            import chromadb
            _client = chromadb.PersistentClient(
                path=settings.CHROMA_DATA_PATH,
            )
    return _client


def get_collection():
    """Get or create the knowledge base collection."""
    global _collection
    if _collection is None:
        client = get_chroma_client()
        if settings.chroma_use_http:
            try:
                _collection = client.get_collection(settings.CHROMA_COLLECTION_NAME)
            except Exception:
                _collection = client.create_collection(
                    name=settings.CHROMA_COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                )
        else:
            try:
                _collection = client.get_collection(name=settings.CHROMA_COLLECTION_NAME)
            except Exception:
                _collection = client.create_collection(
                    name=settings.CHROMA_COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                )
    return _collection


def reset_collection() -> None:
    """Reset the collection (useful for testing)."""
    global _collection
    client = get_chroma_client()
    client.delete_collection(settings.CHROMA_COLLECTION_NAME)
    _collection = None
