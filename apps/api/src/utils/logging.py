"""Logging configuration for the application.

This module provides centralized logging configuration.
Import `get_logger` to create loggers in other modules.
"""

import logging
import sys
from functools import lru_cache


def configure_logging() -> None:
    """Configure logging for the application.

    This should be called once at application startup.
    Configures the root logger and sets appropriate levels.
    """
    # Configure root logger for Cloud Run (captures stdout)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,  # Override any existing configuration
    )

    # Set log level for our application modules
    logging.getLogger("src").setLevel(logging.INFO)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)


@lru_cache(maxsize=None)
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given module name.

    Uses caching to return the same logger instance for repeated calls.

    Args:
        name: The module name, typically __name__

    Returns:
        Configured logger instance

    Example:
        from src.utils.logging import get_logger
        logger = get_logger(__name__)
        logger.info("This is an info message")
    """
    return logging.getLogger(name)
