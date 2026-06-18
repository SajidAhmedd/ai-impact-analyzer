"""
Structured logging configuration.

WHY STRUCTURED LOGGING:
- JSON format is machine-parseable
- Context is preserved (user_id, request_id, etc.)
- Easy to search and filter in log aggregators
- Better than print() or basic logging
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
import structlog

from app.config import get_settings


def setup_logging() -> None:
    """
    Configure structured logging for the application.

    Call this once at application startup.
    """
    settings = get_settings()

    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Log file path with date
    log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not settings.DEBUG else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.

    Usage:
        from app.observability.logger import get_logger

        logger = get_logger(__name__)
        logger.info("Processing document", filename="policy.pdf", chunks=5)
    """
    return structlog.get_logger(name)


class LogContext:
    """
    Context manager for adding temporary context to logs.

    Usage:
        with LogContext(request_id="abc123", user="john"):
            logger.info("Processing request")  # includes request_id and user
    """

    def __init__(self, **kwargs):
        self.context = kwargs
        self.token = None

    def __enter__(self):
        self.token = structlog.contextvars.bind_contextvars(**self.context)
        return self

    def __exit__(self, *args):
        structlog.contextvars.unbind_contextvars(*self.context.keys())