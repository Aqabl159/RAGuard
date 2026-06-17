"""SiliconFlow BGE Embedding API client (OpenAI-compatible format)."""

import httpx
from app.config import settings


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of text chunks using BGE via SiliconFlow.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (each is a list of floats).
    """
    if not texts:
        return []

    headers = {
        "Authorization": f"Bearer {settings.SILICONFLOW_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.EMBEDDING_MODEL,
        "input": texts,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.SILICONFLOW_BASE_URL}/embeddings",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    embeddings = []
    for item in data.get("data", []):
        embeddings.append(item["embedding"])
    return embeddings


def embed_texts_sync(texts: list[str]) -> list[list[float]]:
    """Synchronous wrapper for embedding."""
    import asyncio
    return asyncio.run(embed_texts(texts))


async def embed_single(text: str) -> list[float]:
    """Generate embedding for a single text string."""
    results = await embed_texts([text])
    return results[0] if results else []
