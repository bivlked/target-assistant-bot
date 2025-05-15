import sys
from pathlib import Path
import importlib  # Keep for now, review usage later
from typing import Dict, Any, List, Tuple  # Added Any, List, Tuple

import pytest
import gspread  # Import gspread at the top

# Добавляем корень репозитория в sys.path, чтобы импорты 'utils', 'sheets' работали при запуске CI.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------- Фикстуры для моков gspread -----------------


class _DummyCell:  # Added for more precise type hinting if needed
    value: Any

    def __init__(self, value: Any):
        self.value = value


class _DummyWorksheet:
    """Mock for gspread.Worksheet."""

    def __init__(self, title: str):
        """Initializes a dummy worksheet.

        Args:
            title: The title of the worksheet.
        """
        self.title = title
        self.formatted: List[Tuple[str, Any]] = []
        self.auto_resized: List[Tuple[int, int]] = []
        self.frozen: bool = False
        self.data: List[List[Any]] = []  # Stores the latest written data (list of rows)

    # Methods called by SheetsManager
    def format(self, rng: str, fmt: Any) -> None:
        """Simulates formatting a cell range."""
        self.formatted.append((rng, fmt))

    def columns_auto_resize(self, start_col_idx: int, end_col_idx: int) -> None:
        """Simulates auto-resizing columns."""
        self.auto_resized.append((start_col_idx, end_col_idx))

    def freeze(self, rows: int = 1) -> None:
        """Simulates freezing rows."""
        self.frozen = True

    def update(self, rng: str, rows: List[List[Any]]) -> None:
        """Simulates updating a range with new rows. Stores data for later retrieval."""
        # For simplicity, assuming rng covers the start of self.data or overwrites it.
        # A more complex mock might handle specific ranges.
        self.data = rows

    def update_title(self, new_title: str) -> None:
        """Simulates updating the worksheet title."""
        self.title = new_title

    # Required by get_extended_statistics
    def get_all_records(self) -> List[Dict[str, Any]]:
        """Simulates gspread's get_all_records()."""
        if not self.data or len(self.data) < 1:
            return []
        header = self.data[0]
        return [dict(zip(header, row_values)) for row_values in self.data[1:]]

    def get_all_values(self) -> List[List[Any]]:
        """Simulates gspread's get_all_values()."""
        return self.data

    def update_cell(self, row: int, col: int, val: Any) -> None:
        """Simulates updating a single cell. Simplistic mutation for tests."""
        # Ensure the data list has enough rows
        while len(self.data) < row:
            self.data.append([])
        # Ensure the specific row has enough columns
        while len(self.data[row - 1]) < col:
            self.data[row - 1].append(
                None
            )  # Pad with None or a specific empty cell marker
        self.data[row - 1][col - 1] = val


class _DummySpreadsheet:
    """Mock for gspread.Spreadsheet."""

    def __init__(self, name: str):
        """Initializes a dummy spreadsheet.
        Args:
            name: The name of the spreadsheet.
        """
        self.name = name
        self.url = f"http://dummy/{name}"
        self.worksheets: Dict[str, _DummyWorksheet] = {
            "Sheet1": _DummyWorksheet("Sheet1")
        }
        self.sheet1 = self.worksheets["Sheet1"]

    # Methods mimicking gspread API
    def worksheet(self, title: str) -> _DummyWorksheet:
        """Simulates getting a worksheet by title."""
        if title not in self.worksheets:
            raise gspread.WorksheetNotFound()  # Use direct gspread exception
        return self.worksheets[title]

    def add_worksheet(self, title: str, rows: int, cols: int) -> _DummyWorksheet:
        """Simulates adding a new worksheet."""
        ws = _DummyWorksheet(title)
        self.worksheets[title] = ws
        return ws

    def del_worksheet(self, ws: _DummyWorksheet) -> None:
        """Simulates deleting a worksheet."""
        self.worksheets.pop(ws.title, None)

    def share(self, *args: Any, **kwargs: Any) -> None:
        """Simulates sharing a spreadsheet (no-op)."""
        pass


class _DummyGSpreadClient:
    """Mock for the gspread client object returned by gspread.authorize()."""

    def __init__(self):
        """Initializes the dummy client."""
        self.spreads: Dict[str, _DummySpreadsheet] = {}

    def open(self, name: str) -> _DummySpreadsheet:
        """Simulates opening a spreadsheet by name."""
        if name not in self.spreads:
            raise gspread.SpreadsheetNotFound()  # Use direct gspread exception
        return self.spreads[name]

    def create(self, name: str) -> _DummySpreadsheet:
        """Simulates creating a new spreadsheet."""
        sp = _DummySpreadsheet(name)
        self.spreads[name] = sp
        return sp

    def del_spreadsheet(self, file_id: str) -> None:
        """(Mock) Simulates deleting a spreadsheet by ID."""
        pass


@pytest.fixture(autouse=True)
def patch_gspread(monkeypatch: pytest.MonkeyPatch):
    """Global fixture: patches gspread to avoid network calls and use dummies."""

    # It's generally better to use the actual exceptions if gspread is a test dependency.
    # However, if aiming for extreme isolation or if gspread might not be in a minimal
    # test environment, defining local dummy exceptions can be a strategy.
    # For now, we assume gspread IS a test dependency from requirements.txt.
    # So, gspread.SpreadsheetNotFound and gspread.WorksheetNotFound will be used directly.

    dummy_client = _DummyGSpreadClient()

    monkeypatch.setattr("gspread.authorize", lambda creds: dummy_client)
    monkeypatch.setattr(
        "google.oauth2.service_account.Credentials.from_service_account_file",
        lambda *a, **kw: None,  # type: ignore[misc]
    )

    # --- Credentials path mock ---
    from pathlib import Path
    import config as _cfg  # Renamed to avoid conflict if config is a fixture name

    dummy_file = Path.cwd() / "dummy_credentials.json"
    if not dummy_file.exists():
        dummy_file.write_text("{}")

    # Also create the fallback file that GoogleConfig looks for by default,
    # so tests don't fail even if monkeypatching _raw_path doesn't apply as expected.
    fallback_file = PROJECT_ROOT / "google_credentials.json"
    if not fallback_file.exists():
        fallback_file.write_text("{}")

    # Override the path within the GoogleConfig instance
    monkeypatch.setattr(_cfg.google, "_raw_path", str(dummy_file), raising=True)

    yield
