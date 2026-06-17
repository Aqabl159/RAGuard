"""QA orchestration: retrieve → guard → rerank → generate."""

from app.qa.retriever import retrieve_chunks
from app.qa.conflict_guard import check_conflicts
from app.qa.answer_generator import generate_answer
from app.models.qa import ConflictWarningInfo, SourceInfo


async def run_qa_pipeline(query: str) -> dict:
    """Run the full QA pipeline.

    Steps:
    1. Retrieve top-10 chunks from Chroma
    2. Rerank with Jina Reranker (keep top-5)
    3. Check for conflicts among retrieved chunks
    4. Generate answer with DeepSeek (with or without conflict context)

    Returns:
        Dict with: answer, sources, conflict_warning (if applicable).
    """
    # Step 1: Retrieve
    chunks = await retrieve_chunks(query, top_k=10)
    if not chunks:
        return {
            "content": "知识库中没有找到相关信息，请先上传相关文档。",
            "sources": [],
            "conflict_warning": None,
        }

    # Step 2: Rerank
    try:
        from app.conflict.reranker import rerank_pairs

        # Build query-document pairs for reranker
        rerank_pairs_input = []
        for chunk in chunks:
            rerank_pairs_input.append({
                "content_a": query,
                "content_b": chunk["content"],
                "_chunk": chunk,
            })

        ranked = await rerank_pairs(rerank_pairs_input, threshold=0)
        if ranked:
            chunks = [r["_chunk"] for r in ranked[:5]]
        else:
            chunks = chunks[:5]
    except Exception:
        chunks = chunks[:5]

    # Step 3: Conflict guard
    chunk_ids = [c["id"] for c in chunks]
    conflict_warning = check_conflicts(chunk_ids)

    # Step 4: Generate answer
    answer_text, sources = await generate_answer(query, chunks, conflict_warning)

    return {
        "content": answer_text,
        "sources": sources,
        "conflict_warning": conflict_warning if conflict_warning.has_conflict else None,
    }
