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
        self.formatted = []
        self.auto_resized = []
        self.frozen = False
        self.data = []  # хранение последних записанных данных

    # методы, вызываемые SheetsManager
    def format(self, rng, fmt):  # noqa: D401
        self.formatted.append((rng, fmt))

    def columns_auto_resize(self, start, end):  # noqa: D401
        self.auto_resized.append((start, end))

    def freeze(self, rows=1):  # noqa: D401
        self.frozen = True

    def update(self, rng, rows):  # noqa: D401
        # сохраняем данные для последующего чтения
        self.data = rows

    def update_title(self, new):  # noqa: D401
        self.title = new

    # для get_extended_statistics требуется
    def get_all_records(self):  # noqa: D401
        if not self.data:
            return []
        header = self.data[0]
        return [dict(zip(header, row)) for row in self.data[1:]]

    def get_all_values(self):  # noqa: D401
        return self.data

    def update_cell(self, row, col, val):  # noqa: D401
        # simplistic mutation for tests
        try:
            self.data[row - 1][col - 1] = val
        except Exception:
            pass


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

    # --- Заглушка credentials path ---
    from pathlib import Path
    import config as _cfg

    dummy_file = Path.cwd() / "dummy_credentials.json"
    if not dummy_file.exists():
        dummy_file.write_text("{}")

    # Создаём также fallback-файл, который ищет GoogleConfig по умолчанию,
    # чтобы тесты не падали, даже если monkeypatch _raw_path не применится
    fallback_file = PROJECT_ROOT / "google_credentials.json"
    if not fallback_file.exists():
        fallback_file.write_text("{}")

    # Переписываем путь внутри экземпляра GoogleConfig
    monkeypatch.setattr(_cfg.google, "_raw_path", str(dummy_file), raising=True)

    yield
