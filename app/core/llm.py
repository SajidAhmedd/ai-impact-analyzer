"""
Ollama LLM integration with dependency injection.

WHY DEPENDENCY INJECTION:
- Single LLM instance shared across the app
- Easy to swap models (just change config)
- Easy to mock for testing
- Lazy loading (only created when first needed)

WHY OLLAMA:
- Runs locally (free, private)
- Supports Llama 3, Mistral, and other open models
- Compatible with LangChain
"""

from functools import lru_cache
from langchain_ollama import ChatOllama
import structlog

from app.config import get_settings

# Set up structured logging
logger = structlog.get_logger()


@lru_cache
def get_llm() -> ChatOllama:
    """
    Returns a cached ChatOllama instance.

    WHY ChatOllama (not just Ollama):
    - ChatOllama is for chat/instruction models (like Llama 3)
    - Supports system messages, chat history
    - Better for conversational/analysis tasks

    WHY @lru_cache:
    - LLM connection is expensive to create
    - We want ONE instance reused everywhere
    - First call creates it, subsequent calls return cached version

    Usage:
        from app.core.llm import get_llm

        llm = get_llm()
        response = llm.invoke("What is AI?")
        print(response.content)
    """
    settings = get_settings()

    logger.info(
        "Initializing LLM",
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=settings.LLM_TEMPERATURE
    )

    return ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=settings.LLM_TEMPERATURE,
    )


def check_ollama_connection() -> bool:
    """
    Verify Ollama is running and accessible.

    Call this at startup to fail fast if Ollama isn't available.

    Returns:
        True if Ollama is accessible, False otherwise
    """
    try:
        llm = get_llm()
        # Simple test query
        response = llm.invoke("Say 'ok' and nothing else.")
        logger.info("Ollama connection successful", response=response.content[:50])
        return True
    except Exception as e:
        logger.error("Ollama connection failed", error=str(e))
        return False