"""DeepSeek LLM resolution generation prompts."""

import json
from openai import OpenAI
from app.config import settings


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
    return _client


CLAIM_EXTRACTION_PROMPT = """你是一个合同/文档分析专家。请分析以下两个文本块，提取每个块中的具体事实性主张。

**文本 A：**
{text_a}

**文本 B：**
{text_b}

请以 JSON 格式返回：
{{
  "claims_a": ["主张1", "主张2", ...],
  "claims_b": ["主张1", "主张2", ...]
}}"""


CONTRADICTION_ANALYSIS_PROMPT = """块 A 的主张：
{claims_a}

块 B 的主张：
{claims_b}

这些主张是否互相矛盾？请从以下维度分析：
1. 直接否定（A 说 X，B 说 非X）
2. 数值不一致（A 说 7天，B 说 30天）
3. 时间冲突（A 说 2023年生效，B 说 2024年生效）
4. 定义不匹配（同一术语的不同定义）
5. 条件与绝对陈述冲突

请以 JSON 格式返回：
{{
  "is_contradictory": true/false,
  "analysis": "详细分析...",
  "contradiction_type": "factual_contradiction|numerical_discrepancy|temporal_conflict|definition_mismatch|conditional_vs_absolute",
  "confidence": "high|medium|low"
}}"""


RESOLUTION_GENERATION_PROMPT = """你是一个知识库管理专家。请针对以下矛盾提出解决方案。

**上下文：**
矛盾类型：{conflict_type}

**文本 A**（来自文档「{doc_title_a}」）：
{text_a}

**文本 B**（来自文档「{doc_title_b}」）：
{text_b}

**矛盾分析：**
{analysis}

请选择一个行动方案并给出详细理由：
- **replace_both**：用新的一致内容替换两个文本块
- **keep_a_remove_b**：保留 A，移除/标记 B 为过时
- **keep_b_remove_a**：保留 B，移除/标记 A 为过时
- **merge**：将两个块合并为一个一致版本
- **manual_rewrite**：需要人工完全重写，机器无法确定正确版本

请以 JSON 格式返回：
{{
  "proposed_action": "merge",
  "proposed_content": "合并或重写后的文本内容（如果是 replace_both 或 merge）",
  "reasoning": "为什么这个方案最合适，给出具体的逻辑推理"
}}"""


async def extract_claims(text_a: str, text_b: str) -> dict:
    """Extract factual claims from both chunks."""
    client = _get_client()
    prompt = CLAIM_EXTRACTION_PROMPT.format(text_a=text_a[:1500], text_b=text_b[:1500])

    response = client.chat.completions.create(
        model=settings.DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": "你是一个严谨的文档分析专家。始终以 JSON 格式返回结果。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=1024,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    return json.loads(content) if content else {}


async def analyze_contradiction(claims_a: list[str], claims_b: list[str]) -> dict:
    """Analyze whether the extracted claims contradict each other."""
    client = _get_client()
    prompt = CONTRADICTION_ANALYSIS_PROMPT.format(
        claims_a=json.dumps(claims_a, ensure_ascii=False),
        claims_b=json.dumps(claims_b, ensure_ascii=False),
    )

    response = client.chat.completions.create(
        model=settings.DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": "你是一个严谨的矛盾分析专家。始终以 JSON 格式返回结果。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=1024,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    return json.loads(content) if content else {}


async def generate_resolution(
    conflict_type: str,
    doc_title_a: str,
    doc_title_b: str,
    text_a: str,
    text_b: str,
    analysis: str,
) -> dict:
    """Generate a resolution proposal for the conflict."""
    client = _get_client()
    prompt = RESOLUTION_GENERATION_PROMPT.format(
        conflict_type=conflict_type,
        doc_title_a=doc_title_a,
        doc_title_b=doc_title_b,
        text_a=text_a[:1500],
        text_b=text_b[:1500],
        analysis=analysis,
    )

    response = client.chat.completions.create(
        model=settings.DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": "你是一个严谨的知识库管理专家。始终以 JSON 格式返回结果。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=2048,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    return json.loads(content) if content else {}
