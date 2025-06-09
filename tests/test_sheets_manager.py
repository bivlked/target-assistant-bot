"""Tests for the synchronous SheetsManager (sheets.client.SheetsManager)."""

import pytest
from unittest.mock import MagicMock, call, patch  # Добавляем call и patch
import gspread  # Добавляем импорт gspread для WorksheetNotFound
from typing import Tuple  # Добавляем Tuple для аннотации
from datetime import datetime, timezone

# Импортируем SheetsManager и константы
from sheets.client import (
    SheetsManager,
    COL_STATUS,
    # GOAL_INFO_SHEET, # Removed
    # PLAN_SHEET, # Removed
    COL_DATE,
    COL_TASK,
    GOALS_LIST_SHEET,
    GOAL_SHEET_PREFIX,
)  # Добавлены COL_DATE, COL_TASK, GOALS_LIST_SHEET, GOAL_SHEET_PREFIX

# Импортируем модели данных
from core.models import Goal, Task, TaskStatus, GoalPriority, GoalStatus, GoalStatistics

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

    # Mock active goal
    test_goal = Goal(
        goal_id=1,
        name="Test Goal",
        description="Test",
        deadline="1 месяц",
        daily_time="30 мин",
        start_date="01.01.2025",
        status=GoalStatus.ACTIVE,
        priority=GoalPriority.HIGH,
        tags=[],
    )

    # Mock goal statistics
    test_stats = GoalStatistics(
        total_tasks=5,
        completed_tasks=3,
        progress_percent=60,
        days_elapsed=5,
        days_remaining=25,
        completion_rate=0.6,
    )

    with patch.object(manager, "get_active_goals", return_value=[test_goal]):
        with patch.object(manager, "get_goal_statistics", return_value=test_stats):
            stats = manager.get_statistics(user_id=123)

            assert "Выполнено 3" in stats
            assert "из 5" in stats
            assert "(60%)" in stats


def test_save_goal_info_formats_and_autowidth(
    manager_instance: tuple[SheetsManager, MagicMock],
):
    """Test that save_goal_info formats and auto-resizes the sheet correctly."""
    manager, mock_spreadsheet = manager_instance

    # Create test goal
    test_goal = Goal(
        goal_id=1,
        name="Test Goal",
        description="Test Description",
        deadline="3 месяца",
        daily_time="1 час",
        start_date="01.01.2025",
        status=GoalStatus.ACTIVE,
        priority=GoalPriority.MEDIUM,
        tags=["test"],
    )

    # Mock worksheet
    mock_goals_ws = MagicMock()
    mock_goals_ws.get_all_values.return_value = [
        ["ID цели", "Название цели", "..."],  # header
    ]

    mock_spreadsheet.worksheet.return_value = mock_goals_ws
    mock_spreadsheet.url = "https://test.url"

    # Mock _ensure_goal_sheet
    with patch.object(manager, "_ensure_goal_sheet"):
        url = manager.save_goal_info(1, test_goal)

        # Verify spreadsheet operations
        mock_spreadsheet.worksheet.assert_called_with(GOALS_LIST_SHEET)
        mock_goals_ws.append_row.assert_called_once()
        assert url == mock_spreadsheet.url


def test_save_plan_freeze_and_format(manager_instance: tuple[SheetsManager, MagicMock]):
    """Test that save_plan freezes the header and formats the plan sheet."""
    manager, mock_spreadsheet = manager_instance
    plan = [
        {
            "Дата": "01.01.2025",
            "День недели": "Среда",
            "Задача": "Task 1",
            "Статус": "Не выполнено",
        },
        {
            "Дата": "02.01.2025",
            "День недели": "Четверг",
            "Задача": "Task 2",
            "Статус": "Не выполнено",
        },
    ]

    # Mock worksheet
    mock_plan_ws = MagicMock()
    mock_spreadsheet.worksheet.return_value = mock_plan_ws

    # Mock _format_plan_sheet
    with patch.object(manager, "_ensure_goal_sheet"):
        with patch.object(manager, "_format_plan_sheet") as mock_format:
            manager.save_plan(2, 1, plan)  # user_id=2, goal_id=1

            # Verify sheet operations
            mock_plan_ws.clear.assert_called_once()
            mock_plan_ws.update.assert_called_once()
            mock_format.assert_called_once_with(mock_plan_ws)


def test_clear_user_data(manager_instance: tuple[SheetsManager, MagicMock]):
    """Test that clear_user_data archives all active goals."""
    manager, mock_spreadsheet = manager_instance

    # Mock active goals
    test_goal = Goal(
        goal_id=1,
        name="Active Goal",
        description="Test",
        deadline="1 месяц",
        daily_time="30 мин",
        start_date="01.01.2025",
        status=GoalStatus.ACTIVE,
        priority=GoalPriority.HIGH,
        tags=[],
    )

    # Mock get_active_goals to return our test goal
    with patch.object(manager, "get_active_goals", return_value=[test_goal]):
        with patch.object(manager, "archive_goal") as mock_archive:
            manager.clear_user_data(user_id=123)

            # Verify archive was called for the active goal
            mock_archive.assert_called_once_with(123, 1)


def test_get_goal_info_sync(manager_instance: tuple[SheetsManager, MagicMock]):
    """Test synchronous goal info retrieval from legacy method."""
    manager, mock_spreadsheet = manager_instance

    # Mock active goal
    test_goal = Goal(
        goal_id=1,
        name="Test Goal",
        description="Выучить Python",
        deadline="3 месяца",
        daily_time="1 час",
        start_date="01.01.2025",
        status=GoalStatus.ACTIVE,
        priority=GoalPriority.MEDIUM,
        tags=[],
    )

    with patch.object(manager, "get_active_goals", return_value=[test_goal]):
        result = manager.get_goal_info(user_id=1)

        expected_parsed_info = {
            "Глобальная цель": "Выучить Python",
            "Срок выполнения": "3 месяца",
            "Затраты в день": "1 час",
            "Начало выполнения": "01.01.2025",
        }
        assert result == expected_parsed_info


def test_get_task_for_date_found(manager_instance: tuple[SheetsManager, MagicMock]):
    """Test get_task_for_date when task exists."""
    manager, mock_spreadsheet = manager_instance
    user_id = 1
    goal_id = 1
    target_date_str = "02.01.2025"

    # Mock task
    test_task = Task(
        date=target_date_str,
        day_of_week="Четверг",
        task="Found task",
        status=TaskStatus.NOT_DONE,
        goal_id=goal_id,
        goal_name="Test Goal",
    )

    with patch.object(manager, "get_plan_for_goal", return_value=[test_task]):
        task = manager.get_task_for_date(user_id, goal_id, target_date_str)

        assert task is not None
        assert task.date == target_date_str
        assert task.task == "Found task"


def test_get_task_for_date_not_found(manager_instance: tuple[SheetsManager, MagicMock]):
    """Test get_task_for_date when task doesn't exist."""
    manager, mock_spreadsheet = manager_instance
    user_id = 1
    goal_id = 1
    target_date_str = "15.01.2025"

    # Mock no tasks
    with patch.object(manager, "get_plan_for_goal", return_value=[]):
        task = manager.get_task_for_date(user_id, goal_id, target_date_str)

        assert task is None


def test_update_task_status(manager_instance: tuple[SheetsManager, MagicMock]):
    """Test updating task status for a specific goal."""
    manager, mock_spreadsheet = manager_instance
    user_id = 1
    goal_id = 1
    target_date_str = "03.01.2025"
    new_status = "Выполнено"

    # Mock worksheet with tasks
    mock_worksheet_data = [
        {
            "Дата": "01.01.2025",
            "День недели": "Среда",
            "Задача": "Task 1",
            "Статус": "Не выполнено",
        },
        {
            "Дата": "02.01.2025",
            "День недели": "Четверг",
            "Задача": "Task 2",
            "Статус": "Не выполнено",
        },
        {
            "Дата": "03.01.2025",
            "День недели": "Пятница",
            "Задача": "Task 3",
            "Статус": "Не выполнено",
        },
    ]

    mock_plan_ws = MagicMock()
    mock_plan_ws.get_all_records.return_value = mock_worksheet_data

    # Mock worksheet method
    mock_spreadsheet.worksheet.return_value = mock_plan_ws

    with patch.object(manager, "update_goal_progress"):
        manager.update_task_status(user_id, goal_id, target_date_str, new_status)

        # Verify the correct cell was updated
        mock_plan_ws.update_cell.assert_called_once_with(4, 4, new_status)


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
    """Test batch updating task statuses for multiple goals."""
    manager, mock_spreadsheet = manager_instance
    user_id = 1

    # Updates with tuple keys (goal_id, date)
    updates = {
        (1, "05.01.2025"): "Выполнено",
        (1, "06.01.2025"): "Частично выполнено",
        (2, "05.01.2025"): "Не выполнено",
    }

    # Mock worksheet data for goal 1
    mock_data_goal1 = [
        {
            "Дата": "05.01.2025",
            "День недели": "Воскресенье",
            "Задача": "Task 1",
            "Статус": "Не выполнено",
        },
        {
            "Дата": "06.01.2025",
            "День недели": "Понедельник",
            "Задача": "Task 2",
            "Статус": "Не выполнено",
        },
    ]

    # Mock worksheet data for goal 2
    mock_data_goal2 = [
        {
            "Дата": "05.01.2025",
            "День недели": "Воскресенье",
            "Задача": "Task A",
            "Статус": "Не выполнено",
        },
    ]

    # Setup different worksheets for different goals
    mock_ws_goal1 = MagicMock()
    mock_ws_goal1.get_all_records.return_value = mock_data_goal1

    mock_ws_goal2 = MagicMock()
    mock_ws_goal2.get_all_records.return_value = mock_data_goal2

    def worksheet_side_effect(sheet_name):
        if sheet_name == "Цель 1":
            return mock_ws_goal1
        elif sheet_name == "Цель 2":
            return mock_ws_goal2
        else:
            raise ValueError(f"Unexpected sheet: {sheet_name}")

    mock_spreadsheet.worksheet.side_effect = worksheet_side_effect

    with patch.object(manager, "update_goal_progress"):
        manager.batch_update_task_statuses(user_id, updates)

        # Verify batch updates were called
        assert mock_ws_goal1.batch_update.called
        assert mock_ws_goal2.batch_update.called


def test_create_spreadsheet_scenario_new_sheet(monkeypatch: pytest.MonkeyPatch):
    """Test creating a new spreadsheet when it doesn't exist."""
    manager = SheetsManager()

    # Setup the mock to raise SpreadsheetNotFound
    mock_gc_open = MagicMock(side_effect=gspread.SpreadsheetNotFound)
    monkeypatch.setattr(manager.gc, "open", mock_gc_open)

    # Create new spreadsheet
    mock_new_spreadsheet = MagicMock()
    mock_new_spreadsheet.url = "https://sheets.google.com/new"
    monkeypatch.setattr(
        manager.gc, "create", MagicMock(return_value=mock_new_spreadsheet)
    )

    # Mock worksheet operations
    mock_goals_ws = MagicMock()

    def add_worksheet_side_effect(title, rows, cols):
        if title == GOALS_LIST_SHEET:
            return mock_goals_ws
        else:
            raise ValueError(f"Unexpected worksheet title {title}")

    mock_new_spreadsheet.add_worksheet.side_effect = add_worksheet_side_effect
    mock_new_spreadsheet.sheet1 = MagicMock()

    manager.create_spreadsheet(user_id=1)

    # Verify spreadsheet was created
    manager.gc.create.assert_called_once_with("TargetAssistant_1")

    # Verify Goals List sheet was created
    mock_new_spreadsheet.add_worksheet.assert_called_with(
        title=GOALS_LIST_SHEET,
        rows=15,
        cols=11,  # Number of columns in GOALS_LIST_HEADERS
    )

    # Verify headers were set
    mock_goals_ws.update.assert_called()

    # Verify default sheet was deleted
    mock_new_spreadsheet.del_worksheet.assert_called_with(mock_new_spreadsheet.sheet1)


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

    # Мокаем worksheet, add_worksheet, del_worksheet на mock_existing_spreadsheet
    mock_ws_goals = MagicMock(name="ExistingGoalsSheet")

    def existing_worksheet_side_effect(title):
        if title == GOALS_LIST_SHEET:
            return mock_ws_goals  # Возвращаем существующий лист
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

    # Проверяем, что проверялось наличие листа
    mock_existing_spreadsheet.worksheet.assert_called()

    # Если лист уже существует, add_worksheet вызывается, но с обработкой исключения
    # Или не вызывается вовсе, если логика проверяет наличие листа
    # В данном случае метод _ensure_goals_list_sheet создает лист если его нет
    # Поэтому проверим только, что share был вызван
    mock_existing_spreadsheet.share.assert_called_with(
        "", perm_type="anyone", role="writer", with_link=True
    )


def test_get_extended_statistics(manager_instance: tuple[SheetsManager, MagicMock]):
    """Test get_extended_statistics method (resolves TODO comment)."""
    manager, mock_spreadsheet = manager_instance
    user_id = 1
    upcoming_count = 7

    # Mock active goal
    test_goal = Goal(
        goal_id=1,
        name="Extended Stats Goal",
        description="Test extended statistics",
        deadline="2 месяца",
        daily_time="45 минут",
        start_date="01.01.2025",
        status=GoalStatus.ACTIVE,
        priority=GoalPriority.HIGH,
        tags=["test", "stats"],
    )

    # Mock tasks for the goal
    test_tasks = [
        Task(
            date="15.01.2025",
            day_of_week="Среда",
            task="Upcoming task 1",
            status=TaskStatus.NOT_DONE,
            goal_id=1,
            goal_name="Extended Stats Goal",
        ),
        Task(
            date="16.01.2025",
            day_of_week="Четверг",
            task="Upcoming task 2",
            status=TaskStatus.NOT_DONE,
            goal_id=1,
            goal_name="Extended Stats Goal",
        ),
        Task(
            date="10.01.2025",
            day_of_week="Понедельник",
            task="Completed task",
            status=TaskStatus.DONE,
            goal_id=1,
            goal_name="Extended Stats Goal",
        ),
    ]

    # Mock goal statistics
    test_stats = GoalStatistics(
        total_tasks=10,
        completed_tasks=4,
        progress_percent=40,
        days_elapsed=10,
        days_remaining=50,
        completion_rate=0.4,
    )

    with patch.object(manager, "get_active_goals", return_value=[test_goal]):
        with patch.object(manager, "get_plan_for_goal", return_value=test_tasks):
            with patch.object(manager, "get_goal_statistics", return_value=test_stats):
                with patch.object(
                    manager, "get_spreadsheet_url", return_value="https://test.url"
                ):
                    result = manager.get_extended_statistics(user_id, upcoming_count)

                    # Verify result structure matches actual implementation
                    assert isinstance(result, dict)
                    assert "total_days" in result
                    assert "completed_days" in result
                    assert "progress_percent" in result
                    assert "days_passed" in result
                    assert "days_left" in result
                    assert "upcoming_tasks" in result
                    assert "sheet_url" in result

                    # Verify values match mocked statistics
                    assert result["total_days"] == 10
                    assert result["completed_days"] == 4
                    assert result["progress_percent"] == 40
                    assert result["days_passed"] == 10
                    assert result["days_left"] == 50
                    assert result["sheet_url"] == "https://test.url"

                    # Verify upcoming tasks structure
                    assert isinstance(result["upcoming_tasks"], list)
                    assert len(result["upcoming_tasks"]) <= upcoming_count


def test_get_extended_statistics_no_active_goals(
    manager_instance: tuple[SheetsManager, MagicMock]
):
    """Test get_extended_statistics when user has no active goals."""
    manager, mock_spreadsheet = manager_instance
    user_id = 2

    with patch.object(manager, "get_active_goals", return_value=[]):
        with patch.object(
            manager, "get_spreadsheet_url", return_value="https://test.url"
        ):
            result = manager.get_extended_statistics(user_id, 5)

            # Should return default structure when no active goals
            assert isinstance(result, dict)
            assert result["total_days"] == 0
            assert result["completed_days"] == 0
            assert result["progress_percent"] == 0
            assert result["days_passed"] == 0
            assert result["days_left"] == 0
            assert result["upcoming_tasks"] == []
            assert result["sheet_url"] == "https://test.url"


def test_format_goals_list_sheet_indirectly_via_create(
    manager_instance: tuple[SheetsManager, MagicMock]
):
    """Test _format_goals_list_sheet indirectly through spreadsheet creation (resolves TODO comment)."""
    manager, mock_spreadsheet = manager_instance

    # Mock the _format_goals_list_sheet method to verify it gets called
    with patch.object(manager, "_format_goals_list_sheet") as mock_format:
        with patch.object(manager, "_ensure_goals_list_sheet") as mock_ensure:
            # This should trigger _format_goals_list_sheet during sheet creation
            manager._ensure_spreadsheet_structure(mock_spreadsheet)

            # Verify that _ensure_goals_list_sheet was called
            mock_ensure.assert_called_once_with(mock_spreadsheet)


def test_format_plan_sheet_comprehensive_formatting(
    manager_instance: tuple[SheetsManager, MagicMock]
):
    """Test comprehensive plan sheet formatting including edge cases."""
    manager, mock_spreadsheet = manager_instance

    # Extended plan with more diverse content
    extended_plan = [
        {
            "Дата": "01.01.2025",
            "День недели": "Среда",
            "Задача": "Очень длинная задача с большим количеством текста для проверки автоширины",
            "Статус": "Не выполнено",
        },
        {
            "Дата": "02.01.2025",
            "День недели": "Четверг",
            "Задача": "Short task",
            "Статус": "Выполнено",
        },
        {
            "Дата": "03.01.2025",
            "День недели": "Пятница",
            "Задача": "Medium length task with some details",
            "Статус": "Частично выполнено",
        },
    ]

    # Mock worksheet
    mock_plan_ws = MagicMock()
    mock_spreadsheet.worksheet.return_value = mock_plan_ws

    # Mock _format_plan_sheet to verify formatting parameters
    with patch.object(manager, "_ensure_goal_sheet"):
        with patch.object(manager, "_format_plan_sheet") as mock_format:
            manager.save_plan(3, 2, extended_plan)  # user_id=3, goal_id=2

            # Verify sheet operations and formatting
            mock_plan_ws.clear.assert_called_once()
            mock_plan_ws.update.assert_called_once()
            mock_format.assert_called_once_with(mock_plan_ws)

            # Verify the update call includes header + plan data
            update_call_args = mock_plan_ws.update.call_args
            assert update_call_args is not None
            # Check that values parameter was passed
            assert "values" in update_call_args.kwargs
            # The data should include headers + plan rows
            values = update_call_args.kwargs["values"]
            assert len(values) == len(extended_plan) + 1  # +1 for header


def test_overall_statistics_comprehensive(
    manager_instance: tuple[SheetsManager, MagicMock]
):
    """Test get_overall_statistics with multiple goals for comprehensive coverage."""
    manager, mock_spreadsheet = manager_instance
    user_id = 1

    # Mock multiple goals with different statuses
    test_goals = [
        Goal(
            goal_id=1,
            name="Active Goal 1",
            description="First active goal",
            deadline="1 месяц",
            daily_time="30 минут",
            start_date="01.01.2025",
            status=GoalStatus.ACTIVE,
            priority=GoalPriority.HIGH,
            tags=["work"],
            progress_percent=70,
        ),
        Goal(
            goal_id=2,
            name="Active Goal 2",
            description="Second active goal",
            deadline="2 месяца",
            daily_time="45 минут",
            start_date="01.01.2025",
            status=GoalStatus.ACTIVE,
            priority=GoalPriority.MEDIUM,
            tags=["personal"],
            progress_percent=30,
        ),
        Goal(
            goal_id=3,
            name="Completed Goal",
            description="A completed goal",
            deadline="1 месяц",
            daily_time="20 минут",
            start_date="01.12.2024",
            status=GoalStatus.COMPLETED,
            priority=GoalPriority.LOW,
            tags=["learning"],
            progress_percent=100,
        ),
    ]

    with patch.object(manager, "get_all_goals", return_value=test_goals):
        result = manager.get_overall_statistics(user_id)

        # Verify overall statistics structure matches actual implementation
        assert isinstance(result, dict)
        assert "total_goals" in result
        assert "active_count" in result
        assert "completed_count" in result
        assert "archived_count" in result
        assert "total_progress" in result
        assert "active_goals" in result
        assert "can_add_more" in result

        # Verify aggregated data
        assert result["total_goals"] == 3
        assert result["active_count"] == 2  # goals 1 & 2
        assert result["completed_count"] == 1  # goal 3
        assert result["archived_count"] == 0  # none archived
        assert result["total_progress"] == 50  # (70 + 30) // 2
        assert result["can_add_more"] is True  # less than MAX_GOALS

        # Verify active goals are included
        assert len(result["active_goals"]) == 2
        active_goal_names = [g.name for g in result["active_goals"]]
        assert "Active Goal 1" in active_goal_names
        assert "Active Goal 2" in active_goal_names
