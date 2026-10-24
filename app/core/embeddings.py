"""
Embedding model for converting text to vectors.

WHAT ARE EMBEDDINGS:
- Text → List of numbers (vector) representing meaning
- Similar text = similar vectors
- Used for semantic search (find documents similar to a query)

PROVIDERS (set EMBEDDINGS_PROVIDER):
- ollama: nomic-embed-text via a local Ollama server (768 dimensions)
- fastembed: BAAI/bge-small-en-v1.5 running in-process on CPU (384 dimensions),
  so the hosted demo needs no separate model server
"""

from functools import lru_cache
from langchain_core.embeddings import Embeddings
import structlog

from app.config import get_settings

logger = structlog.get_logger()


@lru_cache
def get_embeddings() -> Embeddings:
    """
    Returns a cached embedding model for the configured provider.

    WHY CACHE:
    - Embedding model loads into memory
    - Expensive to initialize repeatedly
    - One instance handles all embedding requests

    Usage:
        from app.core.embeddings import get_embeddings

        embeddings = get_embeddings()
        vector = embeddings.embed_query("Hello world")
        print(len(vector))
    """
    settings = get_settings()
    provider = settings.EMBEDDINGS_PROVIDER.lower()

    if provider == "fastembed":
        from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

        logger.info("Initializing embedding model", provider="fastembed", model=settings.FASTEMBED_MODEL)

        return FastEmbedEmbeddings(model_name=settings.FASTEMBED_MODEL)

    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        logger.info(
            "Initializing embedding model",
            provider="ollama",
            model=settings.OLLAMA_EMBED_MODEL,
            base_url=settings.OLLAMA_BASE_URL
        )

        return OllamaEmbeddings(
            model=settings.OLLAMA_EMBED_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )

    raise ValueError(
        f"Unknown EMBEDDINGS_PROVIDER: {settings.EMBEDDINGS_PROVIDER}. Use 'ollama' or 'fastembed'."
    )


def check_embeddings_connection() -> bool:
    """
    Verify embedding model is available.

    Returns:
        True if embedding model works, False otherwise
    """
    try:
        embeddings = get_embeddings()
        # Test with a simple string
        vector = embeddings.embed_query("test")
        logger.info(
            "Embedding model working",
            vector_dimensions=len(vector)
        )
        return True
    except Exception as e:
        logger.error("Embedding model failed", error=str(e))
        return False
