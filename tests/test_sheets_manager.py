from typing import Dict

import pytest

import importlib


# ----------------- Dummies -----------------
class DummyWorksheet:
    def __init__(self, title, rows=100, cols=10):
        self.title = title
        self.rows = rows
        self.cols = cols
        self.data = []
        self.formatted = []
        self.auto_resized = []
        self.frozen = False

    # API used in SheetsManager
    def update_title(self, new):  # noqa: D401
        self.title = new

    def update(self, _range, rows):  # noqa: D401
        self.data = rows

    def format(self, rng, fmt):  # noqa: D401
        self.formatted.append((rng, fmt))

    def columns_auto_resize(self, start, end):  # noqa: D401
        self.auto_resized.append((start, end))

    def freeze(self, rows=1):  # noqa: D401
        self.frozen = True

    def clear(self):  # noqa: D401
        self.data = []

    def get_all_values(self):  # noqa: D401
        return self.data

    def get_all_records(self):  # noqa: D401
        # assume first row header present
        if not self.data:
            return []
        header = self.data[0]
        return [dict(zip(header, row)) for row in self.data[1:]]

    def update_cell(self, row, col, val):  # noqa: D401
        pass


class DummySpreadsheet:
    def __init__(self, name):
        self.name = name
        self.worksheets: Dict[str, DummyWorksheet] = {
            "Sheet1": DummyWorksheet("Sheet1")
        }
        self.url = f"http://dummy/{name}"
        self.sheet1 = self.worksheets["Sheet1"]

    # API
    def share(self, *args, **kwargs):  # noqa: D401
        pass

    def worksheet(self, title):  # noqa: D401
        if title not in self.worksheets:
            raise importlib.import_module("gspread").WorksheetNotFound()
        return self.worksheets[title]

    def add_worksheet(self, title, rows, cols):  # noqa: D401
        ws = DummyWorksheet(title, rows, cols)
        self.worksheets[title] = ws
        return ws

    def del_worksheet(self, ws):  # noqa: D401
        self.worksheets.pop(ws.title, None)


class DummyGSpreadClient:
    def __init__(self):
        self.spreads: Dict[str, DummySpreadsheet] = {}

    def open(self, name):  # noqa: D401
        if name not in self.spreads:
            raise importlib.import_module("gspread").SpreadsheetNotFound()
        return self.spreads[name]

    def create(self, name):  # noqa: D401
        sp = DummySpreadsheet(name)
        self.spreads[name] = sp
        return sp

    def del_spreadsheet(self, _id):  # noqa: D401
        pass


# ----------------- Tests -----------------


@pytest.fixture(autouse=True)
def patch_gspread(monkeypatch):
    """Патчим gspread.authorize и Credentials для изоляции от сети."""

    # Импортируем gspread, создаём фиктивные исключения
    import gspread

    class _NotFound(Exception):
        pass

    gspread.SpreadsheetNotFound = _NotFound  # type: ignore[attr-defined]
    gspread.WorksheetNotFound = _NotFound  # type: ignore[attr-defined]

    dummy_gc = DummyGSpreadClient()
    monkeypatch.setattr("gspread.authorize", lambda creds: dummy_gc)

    # Credentials
    monkeypatch.setattr(
        "google.oauth2.service_account.Credentials.from_service_account_file",
        lambda *a, **kw: None,
    )

    yield


def _make_manager():
    from sheets.client import SheetsManager  # re-import after patching

    return SheetsManager()


def test_save_goal_info_formats_and_autowidth():
    mgr = _make_manager()

    url = mgr.save_goal_info(1, {"Глобальная цель": "Test"})
    assert url.startswith("http://dummy/TargetAssistant_1")

    sp = mgr._get_spreadsheet(1)
    ws = sp.worksheet("Информация о цели")

    # format bold column A recorded
    assert any(rng.startswith("A") for rng, _ in ws.formatted)
    # автоширина вызвана
    assert ws.auto_resized and ws.auto_resized[0] == (1, 3)


def test_save_plan_freeze_and_format():
    mgr = _make_manager()
    plan = [{"Дата": "01.05.25", "День недели": "Чт", "Задача": "T", "Статус": "-"}]
    mgr.save_plan(2, plan)

    sp = mgr._get_spreadsheet(2)
    ws = sp.worksheet("План")

    # Шапка отформатирована
    assert any("A1:D1" in rng for rng, _ in ws.formatted)
    # freeze применён
    assert ws.frozen
    # автоширина 1..4 вызвана
    assert (1, 4) in ws.auto_resized
