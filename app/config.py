"""
Application configuration using Pydantic Settings.

WHY THIS APPROACH:
- Pydantic Settings automatically reads from environment variables
- Provides type validation (e.g., ensures LOG_LEVEL is a string)
- Gives default values as fallbacks
- Single source of truth for all config

HOW IT WORKS:
1. First checks for .env file
2. Then checks actual environment variables
3. Falls back to defaults defined here
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All application settings in one place.

    Access via: settings = get_settings()
    Then use: settings.OLLAMA_MODEL
    """

    # Ollama Configuration
    # These control which LLM and embedding model we use
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    # Provider selection
    # LLM_PROVIDER: "ollama" (local), "groq" or "gemini" (hosted, used for the public demo)
    # LLM_FALLBACK_PROVIDER: optional provider to retry on when the primary fails (e.g. rate limits)
    # EMBEDDINGS_PROVIDER: "ollama" (local) or "fastembed" (runs in-process, no server needed)
    LLM_PROVIDER: str = "ollama"
    LLM_FALLBACK_PROVIDER: str = ""
    EMBEDDINGS_PROVIDER: str = "ollama"

    # Groq Configuration
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"

    # Google Gemini Configuration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3-flash-preview"

    # FastEmbed Configuration (only used when EMBEDDINGS_PROVIDER=fastembed)
    FASTEMBED_MODEL: str = "BAAI/bge-small-en-v1.5"

    # Model Parameters
    # Temperature: 0 = deterministic, 1 = creative
    # For analysis tasks, we want low temperature (consistent outputs)
    LLM_TEMPERATURE: float = 0.1

    # ChromaDB Configuration
    # Where the vector database stores its data
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"
    CHROMA_COLLECTION_NAME: str = "documents"

    # Retrieval Configuration
    # How many documents to retrieve for context
    RETRIEVAL_TOP_K: int = 5

    # Load data/documents into an empty vector store at startup (used by the hosted demo)
    SEED_SAMPLE_DOCUMENTS: bool = False

    # Application Settings
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    # Authentication Settings
    # API_KEY: Main API key for authentication (required in production)
    # Set via environment variable or .env file
    API_KEY: str = "dev-api-key-change-in-production"
    API_KEY_HEADER: str = "X-API-Key"
    AUTH_ENABLED: bool = True  # Set to False to disable auth (dev only)

    # Tell Pydantic to look for a .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore extra env vars not defined here
    )


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    WHY @lru_cache:
    - Settings are read once and reused
    - Avoids reading .env file on every call
    - Standard pattern for FastAPI dependency injection

    Usage:
        from app.config import get_settings
        settings = get_settings()
        print(settings.OLLAMA_MODEL)  # "llama3"
    """
    return Settings()