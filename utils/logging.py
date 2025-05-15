"""Logging setup for the application using structlog and standard logging."""

import logging
from typing import Optional
import structlog


def setup_logging(log_level: str | int = "INFO") -> structlog.BoundLogger:
    """Sets up standard logging and structlog with JSON output.

    Args:
        log_level: The logging level (str or int).

    Returns:
        BoundLogger: The root structlog logger to which context can be bound.
    """
    # Basic configuration for stdlib logging (for third-party libraries)
    # This will now primarily handle the JSON output from structlog.
    logging.basicConfig(
        level=log_level, format="%(message)s"  # Format to output structlog's JSON as is
    )

    # Configure structlog
    shared_processors = [
        structlog.contextvars.merge_contextvars,  # Handles context in async code
        structlog.stdlib.add_logger_name,  # Adds logger name, like stdlib
        structlog.stdlib.add_log_level,  # Adds log level
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,  # Prepare for stdlib formatter
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        processor=structlog.processors.JSONRenderer(),  # The actual JSON rendering
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level) if isinstance(log_level, str) else log_level
        ),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()
