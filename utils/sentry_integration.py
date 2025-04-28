import logging
import os

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration


def setup_sentry() -> None:
    """Инициализирует Sentry, если переменная SENTRY_DSN задана."""
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return

    log_level = os.getenv("SENTRY_LOG_LEVEL", "ERROR").upper()

    sentry_logging = LoggingIntegration(level=logging.INFO, event_level=getattr(logging, log_level, logging.ERROR))

    sentry_sdk.init(
        dsn=dsn,
        integrations=[sentry_logging],
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        send_default_pii=False,
    ) 