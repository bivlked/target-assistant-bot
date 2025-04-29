import importlib
import pytest

modules = [
    "main",
    "sheets.client",
    "llm.client",
    "core.goal_manager",
]


@pytest.mark.parametrize("module_name", modules)
def test_import_module(module_name):
    """Проверяем, что основные модули импортируются без ошибок (smoke-тест)."""
    importlib.import_module(module_name)
