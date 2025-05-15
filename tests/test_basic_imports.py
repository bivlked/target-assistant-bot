"""Basic smoke tests to ensure key modules can be imported without errors."""

import importlib
import pytest

# List of critical modules to check for import errors
modules_to_check = [
    "main",
    "sheets.client",  # Main synchronous Sheets client
    "sheets.async_client",  # Async Sheets client
    "llm.async_client",  # Async LLM client (primary one used)
    "core.goal_manager",
    "core.interfaces",
    "core.exceptions",
    "core.metrics",
    "handlers.common",
    "handlers.goal_setting",
    "handlers.task_management",
    "scheduler.tasks",
    "utils.cache",
    "utils.helpers",
    "utils.logging",
    "utils.period_parser",
    "utils.ratelimiter",
    "utils.retry_decorators",
    "utils.sentry_integration",
    "config",
    "texts",
]


@pytest.mark.parametrize("module_name", modules_to_check)
def test_import_module(module_name: str):
    """Checks that essential application modules can be imported without errors (smoke test)."""
    importlib.import_module(module_name)
