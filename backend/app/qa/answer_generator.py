"""DeepSeek LLM answer generation for Q&A."""

from openai import OpenAI
from app.config import settings
from app.models.qa import ConflictWarningInfo, SourceInfo


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
    return _client


SYSTEM_PROMPT_NO_CONFLICT = """你是一个企业知识库智能助手。请严格基于提供的参考文档内容回答问题。

规则：
1. 只使用提供的参考文档中的信息
2. 如果参考文档中没有相关信息，请明确说明"根据现有知识库无法回答此问题"
3. 在回答中引用具体的文档来源
4. 用中文回答，保持简洁专业
5. 不要编造信息"""

SYSTEM_PROMPT_WITH_CONFLICT = """你是一个企业知识库智能助手。你的回答必须特别谨慎，因为当前检索到的知识源中存在信息冲突。

规则：
1. 如实向用户说明检索到的信息存在矛盾
2. 清晰列出互相矛盾的不同说法及来源
3. 不要选择性地只呈现一种说法
4. 建议用户联系知识库管理员确认正确版本
5. 用中文回答，保持中立专业"""


async def generate_answer(
    query: str,
    chunks: list[dict],
    conflict_warning: ConflictWarningInfo | None = None,
) -> tuple[str, list[SourceInfo]]:
    """Generate an answer using DeepSeek based on retrieved chunks.

    Args:
        query: User's question.
        chunks: Retrieved context chunks (from retriever + reranker).
        conflict_warning: Conflict detection result (if any).

    Returns:
        Tuple of (answer_text, list_of_source_infos).
    """
    client = _get_client()

    # Build context
    context_parts = []
    sources = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(f"[来源{i}] {chunk['content']}")
        sources.append(SourceInfo(
            chunk_id=chunk.get("id", ""),
            document_id=chunk.get("document_id", ""),
            document_title=chunk.get("filename", ""),
            content=chunk["content"][:200],
            score=chunk.get("score", 0),
        ))

    context = "\n\n---\n\n".join(context_parts)

    # Choose system prompt based on conflict presence
    has_conflict = conflict_warning and conflict_warning.has_conflict
    system_prompt = SYSTEM_PROMPT_WITH_CONFLICT if has_conflict else SYSTEM_PROMPT_NO_CONFLICT

    # Build user message
    if has_conflict:
        user_message = f"""用户问题：{query}

参考文档（注意：以下文档之间可能存在信息冲突）：
{context}

冲突说明：
{conflict_warning.description}

请回答用户问题，注意如实呈现冲突信息。"""
    else:
        user_message = f"""用户问题：{query}

参考文档：
{context}

请基于以上参考文档回答用户问题。"""

    response = client.chat.completions.create(
        model=settings.DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
        max_tokens=2048,
    )

    answer = response.choices[0].message.content or "无法生成回答"
    return answer, sources


async def generate_answer_stream(
    query: str,
    chunks: list[dict],
    conflict_warning: ConflictWarningInfo | None = None,
):
    """Generate a streaming answer."""
    client = _get_client()

    context_parts = []
    sources = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(f"[来源{i}] {chunk['content']}")
        sources.append(SourceInfo(
            chunk_id=chunk.get("id", ""),
            document_id=chunk.get("document_id", ""),
            document_title=chunk.get("filename", ""),
            content=chunk["content"][:200],
            score=chunk.get("score", 0),
        ))

    context = "\n\n---\n\n".join(context_parts)
    has_conflict = conflict_warning and conflict_warning.has_conflict
    system_prompt = SYSTEM_PROMPT_WITH_CONFLICT if has_conflict else SYSTEM_PROMPT_NO_CONFLICT

    if has_conflict:
        user_message = f"用户问题：{query}\n\n参考文档（注意冲突）：\n{context}\n\n冲突说明：{conflict_warning.description}"
    else:
        user_message = f"用户问题：{query}\n\n参考文档：\n{context}"

    stream = client.chat.completions.create(
        model=settings.DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
        max_tokens=2048,
        stream=True,
    )

    # Yield sources first, then tokens
    yield {"type": "sources", "data": [s.model_dump() for s in sources]}
    if conflict_warning and conflict_warning.has_conflict:
        yield {"type": "conflict", "data": conflict_warning.model_dump()}

    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield {"type": "token", "data": chunk.choices[0].delta.content}

    yield {"type": "done", "data": None}
