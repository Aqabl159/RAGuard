"""DeepSeek LLM-based factual contradiction detection."""

import json
from openai import OpenAI
from app.config import settings


# Singleton DeepSeek client
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
    return _client


CONTRADICTION_PROMPT = """你是一个企业知识库审计专家。请比较以下两个文本片段，判断它们之间是否存在事实性矛盾。

**文本 A** (来源: {source_a}):
{text_a}

**文本 B** (来源: {source_b}):
{text_b}

请分析：
1. 两个文本是否讨论同一主题或相关事实？
2. A 中提取的事实主张是什么？
3. B 中提取的事实主张是什么？
4. 这些主张之间是否存在矛盾？（考虑：直接否定、数值不一致、时效冲突、定义不匹配、条件与绝对陈述冲突）
5. 如果存在矛盾，严重程度如何？(low/medium/high/critical)

请以 JSON 格式返回（不要包含其他内容）：
{{
  "is_contradictory": true/false,
  "topic": "两个文本讨论的主题（如果不相关则写'不相关'）",
  "claim_a": "文本 A 中的关键事实主张",
  "claim_b": "文本 B 中的关键事实主张",
  "analysis": "矛盾分析或解释为什么没有矛盾",
  "conflict_type": "factual_contradiction|numerical_discrepancy|temporal_conflict|definition_mismatch|conditional_vs_absolute",
  "severity": "low|medium|high|critical",
  "summary": "一句话总结（中文，不超过30字）"
}}"""


async def check_contradiction(
    text_a: str,
    text_b: str,
    meta_a: dict | None = None,
    meta_b: dict | None = None,
) -> dict | None:
    """Use DeepSeek to check if two text chunks contain factual contradictions.

    Args:
        text_a: Content of first chunk.
        text_b: Content of second chunk.
        meta_a: Optional Chroma metadata for chunk A (filename, section_path).
        meta_b: Optional Chroma metadata for chunk B.

    Returns:
        Dict with contradiction analysis, or None if the check fails.
    """
    client = _get_client()

    # Build source labels for context
    def _source_label(meta: dict | None) -> str:
        if not meta:
            return "未知来源"
        filename = meta.get("filename", "未知文件")
        section = meta.get("section_path", "")
        if section:
            return f"{filename} > {section}"
        return filename

    source_a = _source_label(meta_a)
    source_b = _source_label(meta_b)

    prompt = CONTRADICTION_PROMPT.format(
        source_a=source_a,
        source_b=source_b,
        text_a=text_a[:1500],
        text_b=text_b[:1500],
    )

    try:
        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "你是一个严谨的知识库审计专家。始终以 JSON 格式返回分析结果。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if content:
            result = json.loads(content)
            return result
    except Exception:
        pass

    return None
