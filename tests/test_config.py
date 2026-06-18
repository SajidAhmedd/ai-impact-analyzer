"""Test configuration module."""

import pytest
from app.config import Settings


def test_settings_defaults():
    """Test that settings have sensible defaults."""
    settings = Settings()
    
    assert settings.OLLAMA_BASE_URL == "http://localhost:11434"
    assert settings.OLLAMA_MODEL == "llama3"
    assert settings.OLLAMA_EMBED_MODEL == "nomic-embed-text"


def test_settings_retrieval():
    """Test retrieval settings."""
    settings = Settings()
    
    assert settings.RETRIEVAL_TOP_K == 5
    assert settings.CHROMA_COLLECTION_NAME == "documents"


def test_settings_temperature():
    """Test LLM temperature is low for analysis tasks."""
    settings = Settings()
    
    assert settings.LLM_TEMPERATURE <= 0.3  # Should be deterministic
