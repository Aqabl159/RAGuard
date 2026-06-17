"""QA retrieval: embed query → Chroma similarity search."""

from app.database.chroma_client import get_collection
from app.ingestion.embedder import embed_single


async def retrieve_chunks(query: str, top_k: int = 10) -> list[dict]:
    """Retrieve top-k relevant chunks for a query.

    Steps:
    1. Embed the query using Jina AI
    2. Query Chroma for similar chunks
    3. Return results with metadata and scores

    Args:
        query: User's question.
        top_k: Number of chunks to retrieve.

    Returns:
        List of dicts with keys: id, content, score, metadata (document_id, filename, etc.)
    """
    # Step 1: Embed query
    query_embedding = await embed_single(query)
    if not query_embedding:
        return []

    # Step 2: Search Chroma
    collection = get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    # Step 3: Format results
    chunks = []
    if results["ids"] and results["ids"][0]:
        for i, chunk_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i] if results.get("distances") else 1.0
            # Convert cosine distance to similarity score
            score = 1.0 - distance

            metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
            content = results["documents"][0][i] if results.get("documents") else ""

            chunks.append({
                "id": chunk_id,
                "content": content,
                "score": score,
                "document_id": metadata.get("document_id", ""),
                "filename": metadata.get("filename", ""),
                # V2 structured metadata
                "section_path": metadata.get("section_path", ""),
                "heading_level": metadata.get("heading_level", 0),
            })

    return chunks
