import sys
from pathlib import Path

# Добавляем корень репозитория в sys.path, чтобы импорты 'utils', 'sheets' работали при запуске CI.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------- Фикстуры для моков gspread -----------------

import importlib
from typing import Dict

import pytest


class _DummyWorksheet:
    def __init__(self, title):
        self.title = title


class _DummySpreadsheet:
    def __init__(self, name):
        self.name = name
        self.url = f"http://dummy/{name}"
        self.worksheets: Dict[str, _DummyWorksheet] = {
            "Sheet1": _DummyWorksheet("Sheet1")
        }
        self.sheet1 = self.worksheets["Sheet1"]

    # -- Методы, имитирующие gspread API --
    def worksheet(self, title):  # noqa: D401
        if title not in self.worksheets:
            raise importlib.import_module("gspread").WorksheetNotFound()
        return self.worksheets[title]

    def add_worksheet(self, title, rows, cols):  # noqa: D401
        ws = _DummyWorksheet(title)
        self.worksheets[title] = ws
        return ws

    def del_worksheet(self, ws):  # noqa: D401
        self.worksheets.pop(ws.title, None)

    def share(self, *args, **kwargs):  # noqa: D401
        pass


class _DummyGSpreadClient:
    def __init__(self):
        self.spreads: Dict[str, _DummySpreadsheet] = {}

    def open(self, name):  # noqa: D401
        if name not in self.spreads:
            raise importlib.import_module("gspread").SpreadsheetNotFound()
        return self.spreads[name]

    def create(self, name):  # noqa: D401
        sp = _DummySpreadsheet(name)
        self.spreads[name] = sp
        return sp


@pytest.fixture(autouse=True)
def patch_gspread(monkeypatch):
    """Глобальная фикстура: подменяет gspread, чтобы не обращаться к сети."""

    import gspread

    class _NotFound(Exception):
        pass

    gspread.SpreadsheetNotFound = _NotFound  # type: ignore[attr-defined]
    gspread.WorksheetNotFound = _NotFound  # type: ignore[attr-defined]

    dummy_client = _DummyGSpreadClient()

    monkeypatch.setattr("gspread.authorize", lambda creds: dummy_client)

    monkeypatch.setattr(
        "google.oauth2.service_account.Credentials.from_service_account_file",
        lambda *a, **kw: None,
    )

    yield
