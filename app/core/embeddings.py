"""
Embedding model for converting text to vectors.

WHAT ARE EMBEDDINGS:
- Text → List of numbers (vector) representing meaning
- Similar text = similar vectors
- Used for semantic search (find documents similar to a query)

WHY nomic-embed-text:
- Designed for RAG applications
- Good balance of speed and quality
- Runs locally via Ollama
- 768-dimensional vectors
"""

from functools import lru_cache
from langchain_ollama import OllamaEmbeddings
import structlog

from app.config import get_settings

logger = structlog.get_logger()


@lru_cache
def get_embeddings() -> OllamaEmbeddings:
    """
    Returns a cached OllamaEmbeddings instance.

    WHY CACHE:
    - Embedding model loads into memory
    - Expensive to initialize repeatedly
    - One instance handles all embedding requests

    Usage:
        from app.core.embeddings import get_embeddings

        embeddings = get_embeddings()
        vector = embeddings.embed_query("Hello world")
        print(len(vector))  # 768 dimensions
    """
    settings = get_settings()

    logger.info(
        "Initializing embedding model",
        model=settings.OLLAMA_EMBED_MODEL,
        base_url=settings.OLLAMA_BASE_URL
    )

    return OllamaEmbeddings(
        model=settings.OLLAMA_EMBED_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
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