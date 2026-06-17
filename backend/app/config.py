"""Application configuration loaded from environment variables and .env file."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env path relative to project root (2 levels up from this file)
_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    """Central configuration for all services."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH) if _ENV_PATH.exists() else ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    RAGUARD_ENV: str = "development"
    DATABASE_URL: str = "sqlite:///data/raguard.db"

    # DeepSeek API
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # SiliconFlow API (BGE models)
    SILICONFLOW_API_KEY: str = ""
    SILICONFLOW_BASE_URL: str = "https://api.siliconflow.cn/v1"
    EMBEDDING_MODEL: str = "BAAI/bge-large-zh-v1.5"
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"

    # Chroma — supports local disk (PersistentClient) or Docker HTTP (HttpClient)
    CHROMA_HOST: str = ""          # e.g. "localhost:8001" for Docker; empty = local disk mode
    CHROMA_DATA_PATH: str = "./data/chroma_db"
    CHROMA_COLLECTION_NAME: str = "raguard_knowledge_base"

    @property
    def chroma_use_http(self) -> bool:
        return bool(self.CHROMA_HOST)

    # Langfuse
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_HOST: str = "http://localhost:3000"

    # Ingestion — chunking (new token-based settings)
    CHUNK_TARGET_TOKENS: int = 512       # Target tokens per chunk
    CHUNK_OVERLAP_TOKENS: int = 50       # Overlap in tokens
    CHUNK_SEMANTIC_THRESHOLD: float = 0.7  # Cosine similarity threshold for topic-switch detection
    CHUNK_USE_SEMANTIC: bool = True      # Enable semantic boundary detection
    MAX_FILE_SIZE_MB: int = 20

    # Deprecated — kept for backward compatibility
    CHUNK_SIZE: int = 512                # @deprecated: use CHUNK_TARGET_TOKENS
    CHUNK_OVERLAP: int = 50              # @deprecated: use CHUNK_OVERLAP_TOKENS

    # Conflict Detection
    SIMILARITY_THRESHOLD: float = 0.85
    RERANKER_THRESHOLD: float = 0.3
    SAME_SECTION_SIMILARITY_BONUS: float = -0.05  # Reduce threshold for same-section pairs (more likely related)

    @property
    def db_path(self) -> str:
        """Extract file path from SQLite URL."""
        if self.DATABASE_URL.startswith("sqlite:///"):
            return self.DATABASE_URL.replace("sqlite:///", "")
        return self.DATABASE_URL


# Global singleton — use get_settings() for lazy init
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create the settings singleton.

    Uses a lazy pattern to allow environment variable override before first access.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset the settings singleton (for testing)."""
    global _settings
    _settings = None


# Backward-compatible alias (re-evaluates on each import)
@property
def _settings_prop():
    return get_settings()


settings = get_settings()
