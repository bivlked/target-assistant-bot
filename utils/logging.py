"""Logging setup for the application using structlog and standard logging."""

import logging
from typing import Optional
import structlog


def setup_logging(log_level: str | int = "INFO") -> structlog.BoundLogger:
    """Sets up standard logging and structlog.

    Args:
        log_level: The logging level (str or int).

    Returns:
        BoundLogger: The root structlog logger to which context can be bound.
    """
    # Basic configuration for stdlib logging (for third-party libraries)
    logging.basicConfig(
        level=log_level, format="%(asctime)s %(levelname)-8s %(name)s: %(message)s"
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # Handles context in async code
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),  # For development; consider JSONRenderer for prod
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level) if isinstance(log_level, str) else log_level
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()
