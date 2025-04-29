from sheets.client import SheetsManager, COL_STATUS


class _FakeWorksheet:
    def __init__(self, records):
        self._records = records

    def get_all_records(self):
        return self._records


class _FakeSpreadsheet:
    def __init__(self, records):
        self._ws = _FakeWorksheet(records)

    def worksheet(self, title):  # noqa: D401
        return self._ws


def test_get_statistics(monkeypatch):
    # Arrange
    records = [
        {COL_STATUS: "Выполнено"},
        {COL_STATUS: "Не выполнено"},
        {COL_STATUS: "Выполнено"},
    ]

    fake_spreadsheet = _FakeSpreadsheet(records)

    # Создаём экземпляр SheetsManager без выполнения __init__, чтобы избежать реального подключения к Google
    manager = object.__new__(SheetsManager)  # type: ignore[arg-type]

    # Подменяем приватный метод _get_spreadsheet, чтобы он возвращал фейковый объект
    monkeypatch.setattr(manager, "_get_spreadsheet", lambda user_id: fake_spreadsheet)

    # Act
    stats = manager.get_statistics(user_id=123)

    # Assert
    assert "Выполнено 2 из 3" in stats
