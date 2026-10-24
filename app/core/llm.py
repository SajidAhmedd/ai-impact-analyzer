"""
LLM integration with dependency injection.

WHY DEPENDENCY INJECTION:
- Single LLM instance shared across the app
- Easy to swap models (just change config)
- Easy to mock for testing
- Lazy loading (only created when first needed)

PROVIDERS (set LLM_PROVIDER, optionally LLM_FALLBACK_PROVIDER):
- ollama: runs locally (free, private) - Llama 3, Mistral and other open models
- groq: hosted inference, free tier
- gemini: Google Gemini API, free tier

WHY A FALLBACK:
- Free tiers are rate-limited; if the primary provider rejects or fails a
  request, the same request is retried on the fallback provider instead of
  the analysis failing mid-demo.
"""

from functools import lru_cache
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable
import structlog

from app.config import get_settings

# Set up structured logging
logger = structlog.get_logger()


def _build_llm(provider: str) -> BaseChatModel:
    """Create a chat model for one provider."""
    settings = get_settings()
    provider = provider.lower()

    if provider == "groq":
        from langchain_groq import ChatGroq

        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY must be set to use the groq provider")

        logger.info("Initializing LLM", provider="groq", model=settings.GROQ_MODEL)
        return ChatGroq(
            model=settings.GROQ_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
            max_retries=1,
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY must be set to use the gemini provider")

        logger.info("Initializing LLM", provider="gemini", model=settings.GEMINI_MODEL)
        return ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
            max_retries=1,
        )

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        logger.info(
            "Initializing LLM",
            provider="ollama",
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL
        )
        return ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.LLM_TEMPERATURE,
        )

    raise ValueError(f"Unknown LLM provider: {provider}. Use 'ollama', 'groq' or 'gemini'.")


@lru_cache
def get_llm() -> Runnable:
    """
    Returns a cached chat model for the configured provider,
    wrapped with the fallback provider when one is configured.

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
    primary = _build_llm(settings.LLM_PROVIDER)

    fallback_provider = settings.LLM_FALLBACK_PROVIDER.strip()
    if not fallback_provider or fallback_provider.lower() == settings.LLM_PROVIDER.lower():
        return primary

    try:
        fallback = _build_llm(fallback_provider)
    except ValueError as e:
        logger.warning("Fallback LLM not configured", provider=fallback_provider, error=str(e))
        return primary

    return primary.with_fallbacks([fallback])


def check_llm_connection() -> bool:
    """
    Verify the configured LLM is reachable.

    Call this at startup to fail fast if the LLM isn't available.

    Returns:
        True if the LLM responds, False otherwise
    """
    try:
        llm = get_llm()
        # Simple test query
        response = llm.invoke("Say 'ok' and nothing else.")
        logger.info("LLM connection successful", response=response.content[:50])
        return True
    except Exception as e:
        logger.error("LLM connection failed", error=str(e))
        return False
