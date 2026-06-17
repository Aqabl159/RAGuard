"""Langfuse observability integration.

Provides CallbackHandler singleton and @observe decorator for tracing
LLM calls and pipeline operations.
"""

from app.config import settings

_langfuse_handler = None


def get_langfuse_handler():
    """Get or create the Langfuse CallbackHandler.

    Returns None if Langfuse credentials are not configured.
    """
    global _langfuse_handler

    if _langfuse_handler is not None:
        return _langfuse_handler

    if not settings.LANGFUSE_SECRET_KEY or not settings.LANGFUSE_PUBLIC_KEY:
        return None

    try:
        from langfuse.callback import CallbackHandler

        _langfuse_handler = CallbackHandler(
            secret_key=settings.LANGFUSE_SECRET_KEY,
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            host=settings.LANGFUSE_HOST,
        )
    except ImportError:
        return None

    return _langfuse_handler


def get_langfuse_traced_llm(llm):
    """Wrap an LLM instance with Langfuse tracing.

    Args:
        llm: An OpenAI-compatible chat model instance.

    Returns:
        The LLM instance configured with Langfuse callback, or the
        original LLM if Langfuse is not available.
    """
    handler = get_langfuse_handler()
    if handler is None:
        return llm
    return llm.with_config({"callbacks": [handler]})


# For later use: DeepSeek LLM adapter
# from openai import OpenAI
# from app.config import settings
#
# deepseek_client = OpenAI(
#     api_key=settings.DEEPSEEK_API_KEY,
#     base_url=settings.DEEPSEEK_BASE_URL,
# )
