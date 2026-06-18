"""
Prompt management module.

Loads prompts from external files for easier editing and versioning.
"""

from pathlib import Path
from functools import lru_cache
from typing import Optional
import structlog

logger = structlog.get_logger()

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


@lru_cache(maxsize=32)
def load_prompt(name: str, fallback: Optional[str] = None) -> str:
    """
    Load a prompt from the prompts directory.

    Args:
        name: Prompt name (without .txt extension)
        fallback: Fallback prompt if file not found

    Returns:
        Prompt text

    Usage:
        prompt = load_prompt("technical")
        # Loads from prompts/technical.txt
    """
    prompt_file = PROMPTS_DIR / f"{name}.txt"

    if prompt_file.exists():
        try:
            content = prompt_file.read_text(encoding="utf-8")
            logger.debug("Loaded prompt", name=name, path=str(prompt_file))
            return content
        except Exception as e:
            logger.error("Failed to load prompt", name=name, error=str(e))
            if fallback:
                return fallback
            raise

    if fallback:
        logger.warning("Prompt file not found, using fallback", name=name)
        return fallback

    raise FileNotFoundError(f"Prompt file not found: {prompt_file}")


def reload_prompts():
    """Clear the prompt cache to reload prompts from disk."""
    load_prompt.cache_clear()
    logger.info("Prompt cache cleared")


# Export common prompts
TECHNICAL_PROMPT = load_prompt("technical")
OPERATIONAL_PROMPT = load_prompt("operational")
RISK_PROMPT = load_prompt("risk")
SYNTHESIZER_PROMPT = load_prompt("synthesizer")
