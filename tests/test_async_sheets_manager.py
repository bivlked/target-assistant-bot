"""Tests for the asynchronous sheets client (sheets.async_client.AsyncSheetsManager)."""

import pytest
import pytest_asyncio  # Для асинхронных фикстур
from unittest.mock import MagicMock
from typing import Tuple, AsyncGenerator  # Добавляем AsyncGenerator

from sheets.async_client import AsyncSheetsManager
from sheets.client import SheetsManager  # Нужен для spec в MagicMock


@pytest_asyncio.fixture
async def async_manager_with_mock_sync() -> (
    AsyncGenerator[Tuple[AsyncSheetsManager, MagicMock], None]
):
    """Provides an AsyncSheetsManager instance with its _sync (SheetsManager) attribute mocked."""
    # Создаем экземпляр AsyncSheetsManager
    # Его __init__ создаст реальный self._sync = SheetsManager(),
    # который, в свою очередь, будет использовать моки gspread из conftest.py.
    # Но для тестирования AsyncSheetsManager нам нужно мокать сам self._sync.

    # Вместо того чтобы позволить AsyncSheetsManager создать реальный SheetsManager,
    # мы можем запатчить SheetsManager в модуле async_client перед созданием AsyncSheetsManager,
    # или запатчить атрибут _sync после создания.
    # Патчинг атрибута _sync после создания проще.

    async_mgr = AsyncSheetsManager(
        max_workers=1
    )  # Используем 1 воркер для предсказуемости тестов

    mock_sync_sheets_manager = MagicMock(spec=SheetsManager)
    # Настроим асинхронные моки для методов, которые возвращают корутины в SheetsManager (если такие есть)
    # Но SheetsManager синхронный, так что его методы не async.
    # AsyncSheetsManager вызывает их через to_thread, так что моки должны быть синхронными.

    # Пример мока для одного из методов _sync
    # mock_sync_sheets_manager.create_spreadsheet = MagicMock() # Обычный MagicMock для синхронного метода
    # Если бы SheetsManager.create_spreadsheet был async, то нужен был бы AsyncMock.

    async_mgr._sync = mock_sync_sheets_manager  # Подменяем _sync на наш мок

    yield async_mgr, mock_sync_sheets_manager

    await async_mgr.aclose()  # Закрываем executor после теста


@pytest.mark.asyncio
async def test_async_create_spreadsheet(
    async_manager_with_mock_sync: tuple[AsyncSheetsManager, MagicMock],
):
    """Tests that AsyncSheetsManager.create_spreadsheet calls the sync version correctly."""
    async_mgr, mock_sync = async_manager_with_mock_sync
    user_id = 123

    # Настраиваем мок для конкретного метода, который будет вызван
    mock_sync.create_spreadsheet = MagicMock()  # Это синхронный метод

    await async_mgr.create_spreadsheet(user_id)

    mock_sync.create_spreadsheet.assert_called_once_with(user_id)


@pytest.mark.asyncio
async def test_async_save_goal_info(
    async_manager_with_mock_sync: tuple[AsyncSheetsManager, MagicMock],
):
    async_mgr, mock_sync = async_manager_with_mock_sync
    user_id = 123
    goal_data = {"goal": "test goal"}
    expected_url = "http://fake.url/sheet"

    mock_sync.save_goal_info = MagicMock(return_value=expected_url)

    url = await async_mgr.save_goal_info(user_id, goal_data)

    assert url == expected_url
    mock_sync.save_goal_info.assert_called_once_with(user_id, goal_data)


@pytest.mark.asyncio
async def test_async_save_plan(
    async_manager_with_mock_sync: tuple[AsyncSheetsManager, MagicMock],
):
    async_mgr, mock_sync = async_manager_with_mock_sync
    user_id = 123
    plan_data = [{"task": "test task"}]

    mock_sync.save_plan = MagicMock()

    await async_mgr.save_plan(user_id, plan_data)

    mock_sync.save_plan.assert_called_once_with(user_id, plan_data)


@pytest.mark.asyncio
async def test_async_get_statistics(
    async_manager_with_mock_sync: tuple[AsyncSheetsManager, MagicMock],
):
    async_mgr, mock_sync = async_manager_with_mock_sync
    user_id = 123
    expected_stats = "stats string"

    mock_sync.get_statistics = MagicMock(return_value=expected_stats)

    stats = await async_mgr.get_statistics(user_id)

    assert stats == expected_stats
    mock_sync.get_statistics.assert_called_once_with(user_id)


@pytest.mark.asyncio
async def test_async_clear_user_data(
    async_manager_with_mock_sync: tuple[AsyncSheetsManager, MagicMock],
):
    async_mgr, mock_sync = async_manager_with_mock_sync
    user_id = 123
    mock_sync.clear_user_data = MagicMock()
    await async_mgr.clear_user_data(user_id)
    mock_sync.clear_user_data.assert_called_once_with(user_id)


@pytest.mark.asyncio
async def test_async_get_goal_info(
    async_manager_with_mock_sync: tuple[AsyncSheetsManager, MagicMock],
):
    async_mgr, mock_sync = async_manager_with_mock_sync
    user_id = 123
    expected_info = {"data": "goal_info"}
    mock_sync.get_goal_info = MagicMock(return_value=expected_info)
    info = await async_mgr.get_goal_info(user_id)
    assert info == expected_info
    mock_sync.get_goal_info.assert_called_once_with(user_id)


@pytest.mark.asyncio
async def test_async_get_task_for_date(
    async_manager_with_mock_sync: tuple[AsyncSheetsManager, MagicMock],
):
    async_mgr, mock_sync = async_manager_with_mock_sync
    user_id = 123
    date_str = "01.01.2025"
    expected_task = {"task": "some_task"}
    mock_sync.get_task_for_date = MagicMock(return_value=expected_task)
    task = await async_mgr.get_task_for_date(user_id, date_str)
    assert task == expected_task
    mock_sync.get_task_for_date.assert_called_once_with(user_id, date_str)


@pytest.mark.asyncio
async def test_async_update_task_status(
    async_manager_with_mock_sync: tuple[AsyncSheetsManager, MagicMock],
):
    async_mgr, mock_sync = async_manager_with_mock_sync
    user_id = 123
    date_str = "01.01.2025"
    status = "Выполнено"
    mock_sync.update_task_status = MagicMock()
    await async_mgr.update_task_status(user_id, date_str, status)
    mock_sync.update_task_status.assert_called_once_with(user_id, date_str, status)


@pytest.mark.asyncio
async def test_async_batch_update_task_statuses(
    async_manager_with_mock_sync: tuple[AsyncSheetsManager, MagicMock],
):
    async_mgr, mock_sync = async_manager_with_mock_sync
    user_id = 123
    updates = {"01.01.2025": "Выполнено"}
    mock_sync.batch_update_task_statuses = MagicMock()
    await async_mgr.batch_update_task_statuses(user_id, updates)
    mock_sync.batch_update_task_statuses.assert_called_once_with(user_id, updates)


@pytest.mark.asyncio
async def test_async_get_spreadsheet_url(
    async_manager_with_mock_sync: tuple[AsyncSheetsManager, MagicMock],
):
    async_mgr, mock_sync = async_manager_with_mock_sync
    user_id = 123
    expected_url = "http://sheet.url"
    mock_sync.get_spreadsheet_url = MagicMock(return_value=expected_url)
    url = await async_mgr.get_spreadsheet_url(user_id)
    assert url == expected_url
    mock_sync.get_spreadsheet_url.assert_called_once_with(user_id)


@pytest.mark.asyncio
async def test_async_get_extended_statistics(
    async_manager_with_mock_sync: tuple[AsyncSheetsManager, MagicMock],
):
    async_mgr, mock_sync = async_manager_with_mock_sync
    user_id = 123
    upcoming_count = 7
    expected_stats = {"data": "extended_stats"}
    mock_sync.get_extended_statistics = MagicMock(return_value=expected_stats)
    stats = await async_mgr.get_extended_statistics(user_id, upcoming_count)
    assert stats == expected_stats
    mock_sync.get_extended_statistics.assert_called_once_with(user_id, upcoming_count)


@pytest.mark.asyncio
async def test_async_delete_spreadsheet(
    async_manager_with_mock_sync: tuple[AsyncSheetsManager, MagicMock],
):
    async_mgr, mock_sync = async_manager_with_mock_sync
    user_id = 123
    mock_sync.delete_spreadsheet = MagicMock()
    await async_mgr.delete_spreadsheet(user_id)
    mock_sync.delete_spreadsheet.assert_called_once_with(user_id)


# TODO: Добавить аналогичные тесты для:
# - get_goal_info
# - get_task_for_date
# - update_task_status
# - batch_update_task_statuses
# - get_spreadsheet_url
# - get_extended_statistics
# - delete_spreadsheet

# TODO: Добавить тесты для всех остальных методов AsyncSheetsManager
