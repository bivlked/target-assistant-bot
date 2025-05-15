"""Tests for the synchronous SheetsManager (sheets.client.SheetsManager)."""

import pytest
from unittest.mock import MagicMock, call  # Добавляем call
import gspread  # Добавляем импорт gspread для WorksheetNotFound
from typing import Tuple  # Добавляем Tuple для аннотации

# Импортируем SheetsManager и константы
from sheets.client import (
    SheetsManager,
    COL_STATUS,
    GOAL_INFO_SHEET,
    PLAN_SHEET,
    COL_DATE,
    COL_TASK,
)  # Добавлены COL_DATE, COL_TASK

# Моки _DummyWorksheet, _DummySpreadsheet, _DummyGSpreadClient теперь приходят из conftest.py (неявно)
# и используются через фикстуру patch_gspread, которая применяется автоматически.

# --- Tests ---


@pytest.fixture
def manager_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> Tuple[SheetsManager, MagicMock]:
    """Provides a SheetsManager instance with its _get_spreadsheet method mocked
    to return a controllable MagicMock spreadsheet object for most tests.
    The underlying gspread client (gc) is already mocked by conftest.patch_gspread.
    """
    # SheetsManager() будет использовать мокнутый gc из conftest.patch_gspread
    manager = SheetsManager()

    # Для большинства тестов мы хотим контролировать, что возвращает _get_spreadsheet,
    # чтобы не зависеть от логики создания/открытия реальных (даже мокнутых) спредов в gc.
    mock_spreadsheet_obj = MagicMock()  # Это будет мок для gspread.Spreadsheet
    monkeypatch.setattr(
        manager, "_get_spreadsheet", lambda user_id: mock_spreadsheet_obj
    )
    return manager, mock_spreadsheet_obj  # Возвращаем и менеджер, и мок спреда


# Тест, перенесенный из test_sheets.py
def test_get_statistics_sync(manager_instance: tuple[SheetsManager, MagicMock]):
    """Tests SheetsManager.get_statistics."""
    manager, mock_spreadsheet = manager_instance

    records = [
        {COL_STATUS: "Выполнено"},
        {COL_STATUS: "Не выполнено"},
        {COL_STATUS: "Выполнено"},
        {COL_STATUS: "Частично выполнено"},
        {COL_STATUS: "Выполнено"},
    ]

    mock_worksheet = MagicMock()
    mock_worksheet.get_all_records.return_value = records
    mock_spreadsheet.worksheet.return_value = mock_worksheet

    stats = manager.get_statistics(user_id=123)

    assert "Выполнено 3" in stats
    assert "из 5" in stats
    assert "(60%)" in stats
    mock_spreadsheet.worksheet.assert_called_once_with(PLAN_SHEET)
    mock_worksheet.get_all_records.assert_called_once()


def test_save_goal_info_formats_and_autowidth(
    manager_instance: tuple[SheetsManager, MagicMock]
):
    """Tests formatting and auto-width calls during save_goal_info."""
    manager, mock_spreadsheet = manager_instance

    mock_ws_goal_info = MagicMock()
    mock_spreadsheet.worksheet.return_value = mock_ws_goal_info

    url = manager.save_goal_info(1, {"Глобальная цель": "Test"})
    # assert url.startswith("http://dummy/TargetAssistant_1") # URL теперь не мокается так просто
    # Вместо этого, проверим вызовы моков, которые отвечают за данные и форматирование

    mock_spreadsheet.worksheet.assert_called_with(GOAL_INFO_SHEET)
    mock_ws_goal_info.update.assert_called_once()
    # Проверка форматирования (A:A bold) и auto_resize (1,3)
    # Это требует, чтобы mock_ws_goal_info.format и columns_auto_resize были MagicMock
    # (они будут, так как mock_ws_goal_info - это MagicMock)
    # Однако, наш _DummyWorksheet из conftest.py имел атрибуты formatted и auto_resized.
    # Чтобы это работало с MagicMock, нам нужно либо проверять call_args, либо сделать
    # mock_ws_goal_info экземпляром _DummyWorksheet из conftest.
    # Пока оставим так, но это место для улучшения, если нужно точно проверять форматирование.
    # Для этого теста, мы просто убедимся, что методы были вызваны.
    mock_ws_goal_info.format.assert_any_call("A:A", {"textFormat": {"bold": True}})
    if hasattr(
        mock_ws_goal_info, "columns_auto_resize"
    ):  # gspread < 5.12 не имеет этого
        mock_ws_goal_info.columns_auto_resize.assert_any_call(1, 3)


def test_save_plan_freeze_and_format(manager_instance: tuple[SheetsManager, MagicMock]):
    """Tests formatting, freeze, and auto-width calls during save_plan."""
    manager, mock_spreadsheet = manager_instance

    mock_ws_plan = MagicMock()
    mock_spreadsheet.worksheet.return_value = mock_ws_plan

    plan = [{"Дата": "01.05.25", "День недели": "Чт", "Задача": "T", "Статус": "-"}]
    manager.save_plan(2, plan)

    mock_spreadsheet.worksheet.assert_called_with(PLAN_SHEET)
    mock_ws_plan.update.assert_called_once()  # Проверяем вызов update
    # Аналогично test_save_goal_info, для точной проверки форматирования нужны более сложные моки
    # или проверки call_args.
    mock_ws_plan.format.assert_any_call(
        "A1:D1",
        {
            "textFormat": {"bold": True},
            "horizontalAlignment": "CENTER",
            "backgroundColor": {"red": 1, "green": 0.898, "blue": 0.8},
        },
    )
    if hasattr(mock_ws_plan, "columns_auto_resize"):
        mock_ws_plan.columns_auto_resize.assert_any_call(1, 4)
    if hasattr(mock_ws_plan, "freeze"):
        mock_ws_plan.freeze.assert_any_call(rows=1)


def test_clear_user_data(manager_instance: tuple[SheetsManager, MagicMock]):
    """Tests that clear_user_data calls clear() on both relevant worksheets."""
    manager, mock_spreadsheet = manager_instance

    mock_ws_goal_info = MagicMock(name="GoalInfoWorksheet")
    mock_ws_plan = MagicMock(name="PlanWorksheet")

    # Настроить worksheet(), чтобы он возвращал разные моки для разных имен
    def worksheet_side_effect(sheet_title):
        if sheet_title == GOAL_INFO_SHEET:
            return mock_ws_goal_info
        elif sheet_title == PLAN_SHEET:
            return mock_ws_plan
        raise ValueError(f"Unexpected sheet title: {sheet_title}")

    mock_spreadsheet.worksheet = MagicMock(side_effect=worksheet_side_effect)

    manager.clear_user_data(user_id=123)

    mock_ws_goal_info.clear.assert_called_once()
    mock_ws_plan.clear.assert_called_once()
    assert mock_spreadsheet.worksheet.call_count == 2  # Вызван для обоих листов


def test_get_goal_info_sync(manager_instance: tuple[SheetsManager, MagicMock]):
    """Tests SheetsManager.get_goal_info."""
    manager, mock_spreadsheet = manager_instance
    user_id = 123

    expected_data_from_sheet = [
        ["Глобальная цель", "Выучить Python"],
        ["Срок выполнения", "3 месяца"],
        ["Затраты в день", "1 час"],
    ]
    expected_parsed_info = {
        "Глобальная цель": "Выучить Python",
        "Срок выполнения": "3 месяца",
        "Затраты в день": "1 час",
    }

    mock_ws_goal_info = MagicMock()
    mock_ws_goal_info.get_all_values.return_value = expected_data_from_sheet
    mock_spreadsheet.worksheet.return_value = mock_ws_goal_info

    result = manager.get_goal_info(user_id)

    assert result == expected_parsed_info
    mock_spreadsheet.worksheet.assert_called_once_with(GOAL_INFO_SHEET)
    mock_ws_goal_info.get_all_values.assert_called_once()


def test_get_task_for_date_found(manager_instance: tuple[SheetsManager, MagicMock]):
    """Tests get_task_for_date when the task is found."""
    manager, mock_spreadsheet = manager_instance
    user_id = 123
    target_date_str = "15.05.2025"

    all_records = [
        {COL_DATE: "14.05.2025", COL_TASK: "Old task", COL_STATUS: "Выполнено"},
        {
            COL_DATE: target_date_str,
            COL_TASK: "Target task",
            COL_STATUS: "Не выполнено",
        },
        {COL_DATE: "16.05.2025", COL_TASK: "Future task", COL_STATUS: "Не выполнено"},
    ]
    expected_task_row = all_records[1]

    mock_ws_plan = MagicMock()
    mock_ws_plan.get_all_records.return_value = all_records
    mock_spreadsheet.worksheet.return_value = mock_ws_plan

    task = manager.get_task_for_date(user_id, target_date_str)

    assert task == expected_task_row
    mock_spreadsheet.worksheet.assert_called_once_with(PLAN_SHEET)
    mock_ws_plan.get_all_records.assert_called_once()


def test_get_task_for_date_not_found(manager_instance: tuple[SheetsManager, MagicMock]):
    """Tests get_task_for_date when the task is not found."""
    manager, mock_spreadsheet = manager_instance
    user_id = 124
    target_date_str = "17.05.2025"

    all_records = [
        {COL_DATE: "14.05.2025", COL_TASK: "Old task", COL_STATUS: "Выполнено"},
    ]
    mock_ws_plan = MagicMock()
    mock_ws_plan.get_all_records.return_value = all_records
    mock_spreadsheet.worksheet.return_value = mock_ws_plan

    task = manager.get_task_for_date(user_id, target_date_str)

    assert task is None
    mock_spreadsheet.worksheet.assert_called_once_with(PLAN_SHEET)
    mock_ws_plan.get_all_records.assert_called_once()


def test_update_task_status(manager_instance: tuple[SheetsManager, MagicMock]):
    """Tests update_task_status finds the correct row and calls update_cell."""
    manager, mock_spreadsheet = manager_instance
    user_id = 125
    target_date_str = "15.05.2025"
    new_status = "Выполнено"

    all_records_before_update = [
        {COL_DATE: "14.05.2025", COL_TASK: "Old task", COL_STATUS: "Выполнено"},
        {
            COL_DATE: target_date_str,
            COL_TASK: "Target task",
            COL_STATUS: "Не выполнено",
        },
        {COL_DATE: "16.05.2025", COL_TASK: "Future task", COL_STATUS: "Не выполнено"},
    ]
    # SheetsManager.update_task_status ищет по get_all_records, затем вызывает update_cell
    # update_cell принимает номер строки (1-based) и колонки (1-based)
    # COL_STATUS - это 4-я колонка (D)
    # Если наш target_date_str на второй строке данных (idx=1), то это 3-я строка в таблице (с заголовком)
    expected_row_index_in_sheet = 3

    mock_ws_plan = MagicMock()
    mock_ws_plan.get_all_records.return_value = all_records_before_update
    mock_spreadsheet.worksheet.return_value = mock_ws_plan

    manager.update_task_status(user_id, target_date_str, new_status)

    mock_spreadsheet.worksheet.assert_called_once_with(PLAN_SHEET)
    mock_ws_plan.get_all_records.assert_called_once()
    mock_ws_plan.update_cell.assert_called_once_with(
        expected_row_index_in_sheet, 4, new_status
    )


def test_delete_spreadsheet(
    manager_instance: tuple[SheetsManager, MagicMock], monkeypatch: pytest.MonkeyPatch
):
    """Tests that delete_spreadsheet calls gc.del_spreadsheet."""
    manager, mock_main_spreadsheet_obj = (
        manager_instance  # mock_main_spreadsheet_obj не используется здесь
    )
    user_id = 777
    sheet_id_to_delete = "test_sheet_id_123"

    # Мокаем gc.open, чтобы он вернул объект с нужным id
    mock_opened_spreadsheet = MagicMock()
    mock_opened_spreadsheet.id = sheet_id_to_delete
    monkeypatch.setattr(
        manager.gc, "open", MagicMock(return_value=mock_opened_spreadsheet)
    )

    # Мокаем gc.del_spreadsheet, чтобы проверить его вызов
    monkeypatch.setattr(manager.gc, "del_spreadsheet", MagicMock())

    manager.delete_spreadsheet(user_id)

    manager.gc.open.assert_called_once_with(f"TargetAssistant_{user_id}")
    manager.gc.del_spreadsheet.assert_called_once_with(sheet_id_to_delete)


def test_delete_spreadsheet_not_found(
    manager_instance: tuple[SheetsManager, MagicMock], monkeypatch: pytest.MonkeyPatch
):
    """Tests that delete_spreadsheet handles SpreadsheetNotFound gracefully."""
    manager, _ = manager_instance
    user_id = 888

    # Мокаем gc.open, чтобы он выбросил SpreadsheetNotFound
    monkeypatch.setattr(
        manager.gc,
        "open",
        MagicMock(side_effect=pytest.importorskip("gspread").SpreadsheetNotFound),
    )
    # Мокаем gc.del_spreadsheet, он не должен быть вызван
    mock_del_spreadsheet = MagicMock()
    monkeypatch.setattr(manager.gc, "del_spreadsheet", mock_del_spreadsheet)

    manager.delete_spreadsheet(user_id)  # Должен просто завершиться без ошибок

    manager.gc.open.assert_called_once_with(f"TargetAssistant_{user_id}")
    mock_del_spreadsheet.assert_not_called()


def test_batch_update_task_statuses(manager_instance: tuple[SheetsManager, MagicMock]):
    """Tests batch_update_task_statuses correctly calls update_cell for each update."""
    manager, mock_spreadsheet = manager_instance
    user_id = 999
    updates = {"10.05.2025": "Выполнено", "12.05.2025": "Частично выполнено"}

    all_records = [
        {
            COL_DATE: "10.05.2025",
            COL_TASK: "Task A",
            COL_STATUS: "Не выполнено",
        },  # -> row 2 in sheet
        {COL_DATE: "11.05.2025", COL_TASK: "Task B", COL_STATUS: "Не выполнено"},
        {
            COL_DATE: "12.05.2025",
            COL_TASK: "Task C",
            COL_STATUS: "Не выполнено",
        },  # -> row 4 in sheet
    ]
    # Ожидаемые номера строк (1-based) в таблице, учитывая строку заголовка
    expected_calls_to_update_cell = [
        call(2, 4, "Выполнено"),  # Используем call
        call(4, 4, "Частично выполнено"),  # Используем call
    ]

    mock_ws_plan = MagicMock()
    mock_ws_plan.get_all_records.return_value = all_records
    mock_spreadsheet.worksheet.return_value = mock_ws_plan

    manager.batch_update_task_statuses(user_id, updates)

    mock_spreadsheet.worksheet.assert_called_once_with(PLAN_SHEET)
    mock_ws_plan.get_all_records.assert_called_once()
    # Проверяем, что update_cell был вызван для каждого элемента в updates с правильными аргументами
    # Так как порядок в словаре updates не гарантирован, а вызовы update_cell будут в этом порядке,
    # лучше проверить наличие вызовов, а не их точный порядок, если это возможно, или отсортировать.
    # MagicMock.call_args_list хранит все вызовы.
    # В данном случае порядок важен, так как он соответствует ключам в updates.
    assert mock_ws_plan.update_cell.call_count == len(expected_calls_to_update_cell)
    mock_ws_plan.update_cell.assert_has_calls(
        expected_calls_to_update_cell, any_order=False
    )


def test_get_spreadsheet_url(manager_instance: tuple[SheetsManager, MagicMock]):
    """Tests get_spreadsheet_url returns the URL from the mocked spreadsheet."""
    manager, mock_spreadsheet = manager_instance
    user_id = 1001
    expected_url = "http://dummy_url_from_mock_spreadsheet"
    mock_spreadsheet.url = expected_url  # Устанавливаем атрибут url у нашего мока

    url = manager.get_spreadsheet_url(user_id)

    assert url == expected_url
    # Проверяем, что _get_spreadsheet был вызван для получения объекта mock_spreadsheet
    # Фикстура manager_instance уже мокает _get_spreadsheet, чтобы он возвращал mock_spreadsheet
    # Поэтому здесь достаточно проверить, что метод был вызван и URL совпадает.
    # manager._get_spreadsheet.assert_called_once_with(user_id) # Это не сработает, так как _get_spreadsheet - это лямбда в фикстуре
    # Вместо этого, мы знаем, что если URL получен, то _get_spreadsheet был вызван успешно.


def test_create_spreadsheet_scenario_new_sheet(monkeypatch: pytest.MonkeyPatch):
    """Tests SheetsManager.create_spreadsheet when a new sheet is created."""
    user_id = 2002
    expected_sheet_name = f"TargetAssistant_{user_id}"

    # Мокаем gc всего SheetsManager, который приходит из conftest.py
    # SheetsManager() создаст gc = gspread.authorize(creds), который уже мокнут в conftest
    # и является экземпляром _DummyGSpreadClient.
    manager = SheetsManager()  # gc здесь будет _DummyGSpreadClient из conftest

    # 1. Настраиваем gc.open(), чтобы он выбросил SpreadsheetNotFound
    mock_gc_open = MagicMock(
        side_effect=pytest.importorskip("gspread").SpreadsheetNotFound
    )
    monkeypatch.setattr(manager.gc, "open", mock_gc_open)

    # 2. Настраиваем gc.create(), чтобы он вернул мок спреда
    mock_created_spreadsheet = MagicMock(name="MockCreatedSpreadsheet")
    mock_ws_info = MagicMock(name="InfoSheet")
    mock_ws_plan = MagicMock(name="PlanSheet")
    # sheet1 будет удален, так что его можно просто мокнуть
    mock_sheet1 = MagicMock(name="DefaultSheet1")

    # Настроим worksheet(), add_worksheet(), del_worksheet() для mock_created_spreadsheet
    def worksheet_side_effect(title):
        if title == GOAL_INFO_SHEET:
            return mock_ws_info
        if title == PLAN_SHEET:
            return mock_ws_plan
        if title == "Sheet1":
            return mock_sheet1  # Для sh.sheet1 перед удалением
        raise ValueError(
            f"Unexpected worksheet title {title} in create_spreadsheet test"
        )

    mock_created_spreadsheet.worksheet = MagicMock(side_effect=worksheet_side_effect)
    mock_created_spreadsheet.add_worksheet = MagicMock(
        side_effect=lambda title, rows, cols: worksheet_side_effect(title)
    )
    mock_created_spreadsheet.del_worksheet = MagicMock()
    # Свойство sheet1 должно быть доступно
    # Вместо прямого моканья sheet1, мы сделаем так, чтобы worksheet("Sheet1") его вернул, если нужно.
    # Или можно сделать его атрибутом:
    mock_created_spreadsheet.sheet1 = mock_sheet1

    monkeypatch.setattr(
        manager.gc, "create", MagicMock(return_value=mock_created_spreadsheet)
    )

    # 3. Мокаем sh.share() у mock_created_spreadsheet (он будет возвращен gc.create)
    mock_created_spreadsheet.share = MagicMock()

    # Act
    manager.create_spreadsheet(user_id)

    # Assert
    mock_gc_open.assert_called_once_with(expected_sheet_name)
    manager.gc.create.assert_called_once_with(expected_sheet_name)

    # Проверяем создание листов и удаление Sheet1
    # add_worksheet должен быть вызван дважды
    assert mock_created_spreadsheet.add_worksheet.call_count == 2
    mock_created_spreadsheet.add_worksheet.assert_any_call(
        title=GOAL_INFO_SHEET, rows=10, cols=3
    )
    mock_created_spreadsheet.add_worksheet.assert_any_call(
        title=PLAN_SHEET, rows=400, cols=4
    )
    mock_created_spreadsheet.del_worksheet.assert_called_once_with(mock_sheet1)

    mock_created_spreadsheet.share.assert_called_with(
        "", perm_type="anyone", role="writer", with_link=True
    )


def test_create_spreadsheet_scenario_sheet_exists(monkeypatch: pytest.MonkeyPatch):
    """Tests SheetsManager.create_spreadsheet when the sheet already exists."""
    user_id = 2003
    expected_sheet_name = f"TargetAssistant_{user_id}"

    manager = SheetsManager()  # gc будет _DummyGSpreadClient из conftest

    # 1. Настраиваем gc.open(), чтобы он ВЕРНУЛ мок спреда (не выбрасывал ошибку)
    mock_existing_spreadsheet = MagicMock(name="MockExistingSpreadsheet")
    monkeypatch.setattr(
        manager.gc, "open", MagicMock(return_value=mock_existing_spreadsheet)
    )

    # 2. gc.create() НЕ должен быть вызван
    mock_gc_create = MagicMock()
    monkeypatch.setattr(manager.gc, "create", mock_gc_create)

    # 3. Мокаем sh.share() у mock_existing_spreadsheet
    mock_existing_spreadsheet.share = MagicMock()

    # Мокаем worksheet, add_worksheet, del_worksheet на mock_existing_spreadsheet,
    # чтобы убедиться, что они НЕ вызываются для изменения структуры, но worksheet вызывается для проверки
    mock_ws_info_existing = MagicMock(name="ExistingInfoSheet")
    mock_ws_plan_existing = MagicMock(name="ExistingPlanSheet")

    def existing_worksheet_side_effect(title):
        if title == GOAL_INFO_SHEET:
            return mock_ws_info_existing
        if title == PLAN_SHEET:
            return mock_ws_plan_existing
        raise gspread.WorksheetNotFound  # Используем импортированный gspread

    mock_existing_spreadsheet.worksheet = MagicMock(
        side_effect=existing_worksheet_side_effect
    )
    mock_existing_spreadsheet.add_worksheet = MagicMock()
    mock_existing_spreadsheet.del_worksheet = MagicMock()

    # Act
    manager.create_spreadsheet(user_id)  # Внутри вызывается _get_spreadsheet

    # Assert
    manager.gc.open.assert_called_once_with(expected_sheet_name)
    mock_gc_create.assert_not_called()  # gc.create() не должен быть вызван

    # Проверяем, что структура существующей таблицы не менялась (add/del не вызывались)
    mock_existing_spreadsheet.add_worksheet.assert_not_called()
    mock_existing_spreadsheet.del_worksheet.assert_not_called()
    # worksheet вызывался для проверки наличия нужных листов (GOAL_INFO_SHEET, PLAN_SHEET)
    assert mock_existing_spreadsheet.worksheet.call_count >= 2
    mock_existing_spreadsheet.worksheet.assert_any_call(GOAL_INFO_SHEET)
    mock_existing_spreadsheet.worksheet.assert_any_call(PLAN_SHEET)

    # Share должен быть вызван и для существующей таблицы
    mock_existing_spreadsheet.share.assert_called_with(
        "", perm_type="anyone", role="writer", with_link=True
    )


# TODO: Add more tests for get_extended_statistics (если не покрыто в другом файле), _format_goal_sheet (косвенно)
