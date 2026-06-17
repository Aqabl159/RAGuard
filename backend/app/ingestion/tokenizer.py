"""Unified token counting module using tiktoken cl100k_base.

Provides consistent token measurement across all subsystems:
- Chunking: size checks and truncation
- QA: token usage tracking
- Reranker: 512-token input truncation
"""

import tiktoken

_ENCODING = None


def _get_enc():
    """Lazy-load the tiktoken encoding (singleton)."""
    global _ENCODING
    if _ENCODING is None:
        _ENCODING = tiktoken.get_encoding("cl100k_base")
    return _ENCODING


def count_tokens(text: str) -> int:
    """Return exact token count for mixed CN/EN text."""
    if not text:
        return 0
    return len(_get_enc().encode(text))


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to max_tokens, guaranteed not to split mid-token."""
    if not text or max_tokens <= 0:
        return ""
    enc = _get_enc()
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return enc.decode(tokens[:max_tokens])


def split_at_token_boundary(text: str, target_tokens: int) -> tuple[str, str]:
    """Split text into two parts at the nearest token boundary.

    First part is as close to target_tokens as possible (may be shorter).
    Returns (first_part, remainder).
    """
    if not text:
        return "", ""
    enc = _get_enc()
    tokens = enc.encode(text)
    if len(tokens) <= target_tokens:
        return text, ""
    return enc.decode(tokens[:target_tokens]), enc.decode(tokens[target_tokens:])


def estimate_tokens(text: str) -> int:
    """Estimate token count (backward-compatible alias for count_tokens)."""
    return count_tokens(text)
