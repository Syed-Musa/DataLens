"""Application configuration from environment variables."""

from pathlib import Path
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings

# Resolve .env relative to Backend directory so it loads regardless of CWD
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from .env or environment."""

    # App
    app_name: str = "DataLens - Intelligent Data Dictionary Agent"
    debug: bool = False

    # Target database (user-provided connection)
    database_url: str = "postgresql://postgres:tiger@localhost:5432/business_data"

    # Metadata store (internal PostgreSQL for storing DQ results, metadata)
    metadata_store_url: str | None = None  # Falls back to database_url if not set

    # AI
    groq_api_key: str | None = None

    # Logging
    log_level: str = "INFO"

    model_config = {
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @field_validator("groq_api_key", mode="before")
    @classmethod
    def empty_key_to_none(cls, v: str | None) -> str | None:
        """Treat empty string as missing so Groq is not called with invalid key."""
        if v is not None and isinstance(v, str) and v.strip() == "":
            return None
        return v


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
