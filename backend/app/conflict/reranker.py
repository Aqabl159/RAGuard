"""SiliconFlow BGE Reranker API client."""

import httpx
from app.config import settings


async def rerank_pairs(
    pairs: list[dict],
    threshold: float | None = None,
) -> list[dict]:
    """Rerank candidate pairs using BGE Reranker via SiliconFlow.

    For each pair, chunk A's content is the query, chunk B's is the document.
    Pairs below the threshold are filtered out.

    Args:
        pairs: List of candidate pair dicts (from candidate_generator).
        threshold: Minimum relevance score (default from settings).

    Returns:
        Filtered and scored pairs, with "rerank_score" field added.
    """
    threshold = threshold or settings.RERANKER_THRESHOLD
    if not pairs:
        return []

    headers = {
        "Authorization": f"Bearer {settings.SILICONFLOW_API_KEY}",
        "Content-Type": "application/json",
    }

    results = []
    async with httpx.AsyncClient(timeout=120.0) as client:
        for pair in pairs:
            payload = {
                "model": settings.RERANKER_MODEL,
                "query": pair["content_a"][:512],
                "documents": [pair["content_b"][:512]],
            }

            try:
                response = await client.post(
                    f"{settings.SILICONFLOW_BASE_URL}/rerank",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()

                if data.get("results"):
                    score = data["results"][0].get("relevance_score", 0)
                    if score >= threshold:
                        pair["rerank_score"] = score
                        results.append(pair)
            except Exception:
                continue

    return results
