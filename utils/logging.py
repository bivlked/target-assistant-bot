import logging
from typing import Optional
import structlog


def setup_logging(log_level: str | int = "INFO") -> structlog.BoundLogger:
    """Настраивает стандартное logging и structlog.

    Args:
        log_level: Уровень логирования (str или int).

    Returns:
        BoundLogger: корневой логгер structlog, к которому можно биндить контекст.
    """
    # Базовая настройка stdlib logging (для сторонних библиотек)
    logging.basicConfig(
        level=log_level, format="%(asctime)s %(levelname)-8s %(name)s: %(message)s"
    )

    # Настройка structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level) if isinstance(log_level, str) else log_level
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()
