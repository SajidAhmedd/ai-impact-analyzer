"""
API Key Authentication for FastAPI.

Provides secure API key validation using constant-time comparison
to prevent timing attacks.

Usage:
    from app.auth import get_api_key

    @app.get("/protected")
    async def protected_route(api_key: str = Depends(get_api_key)):
        return {"message": "Authenticated!"}
"""

import secrets
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
import structlog

from app.config import get_settings

logger = structlog.get_logger()

# Define the API key header scheme
APIKeyHeader = APIKeyHeader(
    name=get_settings().API_KEY_HEADER,
    auto_error=False,  # We handle the error ourselves for better messages
    description="API key for authentication. Get your key from the admin."
)


def verify_api_key(api_key: str) -> bool:
    """
    Verify an API key using constant-time comparison.

    Uses secrets.compare_digest to prevent timing attacks.

    Args:
        api_key: The API key to verify

    Returns:
        True if valid, False otherwise
    """
    settings = get_settings()
    expected_key = settings.API_KEY

    # Use constant-time comparison to prevent timing attacks
    return secrets.compare_digest(api_key, expected_key)


async def get_api_key(
    api_key_header: Optional[str] = Security(APIKeyHeader),
) -> str:
    """
    FastAPI dependency to validate API key from header.

    This is used as a dependency in route definitions:

        @app.get("/protected")
        async def route(api_key: str = Depends(get_api_key)):
            ...

    Args:
        api_key_header: API key from X-API-Key header

    Returns:
        The validated API key

    Raises:
        HTTPException: 401 if no key provided, 403 if invalid key
    """
    settings = get_settings()

    # Check if auth is disabled (dev mode only)
    if not settings.AUTH_ENABLED:
        logger.warning("Authentication is DISABLED - not for production use!")
        return "auth-disabled"

    # Check if API key was provided
    if api_key_header is None:
        logger.warning("API request without API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide it in the X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validate the API key
    if not verify_api_key(api_key_header):
        logger.warning("Invalid API key attempt", key_prefix=api_key_header[:8] + "...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    logger.debug("API key validated successfully")
    return api_key_header


def generate_api_key(length: int = 32) -> str:
    """
    Generate a secure random API key.

    Args:
        length: Length of the key in bytes (will be hex encoded, so 2x chars)

    Returns:
        A secure random API key string

    Usage:
        new_key = generate_api_key()
        print(f"Your new API key: {new_key}")
    """
    return secrets.token_hex(length)
