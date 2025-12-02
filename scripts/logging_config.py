"""
Centralized logging configuration for Prism scripts.

Usage:
    from scripts.logging_config import get_logger
    logger = get_logger(__name__)

    logger.info("Processing document")
    logger.warning("Low quality extraction")
    logger.error("Failed to process", exc_info=True)
"""

import logging
import sys
import os

# Track if logging has been configured
_configured = False


def setup_logging(level: str = None) -> None:
    """
    Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
               Defaults to INFO, or PRISM_LOG_LEVEL env var.
    """
    global _configured
    if _configured:
        return

    # Get level from arg, env var, or default to INFO
    if level is None:
        level = os.getenv("PRISM_LOG_LEVEL", "INFO")

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True  # Override any existing config
    )

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("azure").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for the given module.

    Ensures logging is configured before returning.

    Args:
        name: Module name (typically __name__)

    Returns:
        Configured logger instance
    """
    setup_logging()
    return logging.getLogger(name)
