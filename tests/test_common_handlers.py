"""Tests for the common handlers (start, help, cancel, reset, unknown)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from handlers.common import (
    start_handler,
    help_handler,
    cancel_handler,
    reset_handler,
    unknown_handler,
    confirm_reset,
    cancel_reset,
    WELCOME_TEXT,
    HELP_TEXT,
    CANCEL_TEXT,
    UNKNOWN_TEXT,
    RESET_SUCCESS_TEXT,
)


@pytest.fixture
def mock_update():
    """Create a mock Update object."""
    update = MagicMock()
    update.effective_user.id = 12345
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create a mock Context object."""
    context = MagicMock()
    context.bot = MagicMock()
    return context


@pytest.fixture
def mock_scheduler():
    """Create a mock Scheduler object."""
    scheduler = MagicMock()
    scheduler.add_user_jobs = MagicMock()
    return scheduler


@pytest.fixture
def mock_storage():
    """Create a mock AsyncStorageInterface."""
    storage = MagicMock()
    storage.create_spreadsheet = AsyncMock()
    storage.delete_spreadsheet = AsyncMock()
    return storage


@pytest.mark.asyncio
async def test_start_handler_flow(
    mock_update, mock_context, mock_scheduler, mock_storage
):
    """Test the /start command handler flow."""
    user_id = mock_update.effective_user.id

    # Mock dependencies
    with (
        patch("handlers.common.subscribe_user") as mock_subscribe,
        patch("handlers.common.get_async_storage") as mock_get_storage,
    ):
        mock_get_storage.return_value = mock_storage

        # Create and call handler
        handler = start_handler(mock_scheduler)
        await handler(mock_update, mock_context)

        # Verify user was subscribed
        mock_subscribe.assert_called_once_with(user_id)

        # Verify spreadsheet was created
        mock_storage.create_spreadsheet.assert_awaited_once_with(user_id)

        # Verify scheduler jobs were added
        mock_scheduler.add_user_jobs.assert_called_once_with(mock_context.bot, user_id)

        # Verify welcome message was sent with proper keyboard
        mock_update.message.reply_text.assert_awaited_once()
        call_args = mock_update.message.reply_text.call_args
        assert call_args[0][0] == WELCOME_TEXT

        # Check inline keyboard
        reply_markup = call_args[1]["reply_markup"]
        assert isinstance(reply_markup, InlineKeyboardMarkup)
        assert len(reply_markup.inline_keyboard) == 3
        assert reply_markup.inline_keyboard[0][0].text == "🎯 Мои цели"
        assert reply_markup.inline_keyboard[1][0].text == "➕ Создать цель"
        assert reply_markup.inline_keyboard[2][0].text == "📊 Открыть таблицу"


@pytest.mark.asyncio
async def test_help_handler(mock_update, mock_context):
    """Test the /help command handler."""
    await help_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_awaited_once_with(
        HELP_TEXT, disable_web_page_preview=True
    )


@pytest.mark.asyncio
async def test_cancel_handler(mock_update, mock_context):
    """Test the /cancel command handler."""
    await cancel_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_awaited_once_with(CANCEL_TEXT)


@pytest.mark.asyncio
async def test_unknown_handler(mock_update, mock_context):
    """Test the unknown command handler."""
    await unknown_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_awaited_once_with(UNKNOWN_TEXT)


@pytest.mark.asyncio
async def test_reset_handler_flow(mock_update, mock_context):
    """Test the /reset command handler flow."""
    # Mock is_subscribed to return True
    with patch("handlers.common.is_subscribed", return_value=True):
        await reset_handler(mock_update, mock_context)

        # Verify confirmation message was sent
        mock_update.message.reply_text.assert_awaited_once()
        call_args = mock_update.message.reply_text.call_args

        # Check message content
        message = call_args[0][0]
        assert "⚠️ ВНИМАНИЕ!" in message
        assert "Все ваши цели" in message
        assert "нельзя отменить" in message

        # Check inline keyboard
        reply_markup = call_args[1]["reply_markup"]
        assert isinstance(reply_markup, InlineKeyboardMarkup)
        assert len(reply_markup.inline_keyboard) == 1
        assert len(reply_markup.inline_keyboard[0]) == 2
        assert reply_markup.inline_keyboard[0][0].text == "⚠️ Да, удалить все"
        assert reply_markup.inline_keyboard[0][1].text == "❌ Отмена"


@pytest.mark.asyncio
async def test_reset_handler_not_subscribed(mock_update, mock_context):
    """Test the /reset command when user is not subscribed."""
    # Mock is_subscribed to return False
    with patch("handlers.common.is_subscribed", return_value=False):
        await reset_handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_awaited_once_with(
            "❌ Вы не подписаны на бота. Используйте /start для начала."
        )


@pytest.mark.asyncio
async def test_confirm_reset(mock_storage):
    """Test the confirm reset callback."""
    # Create mock callback query
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.from_user.id = 12345

    update = MagicMock()
    update.callback_query = query

    context = MagicMock()

    with patch("handlers.common.get_async_storage") as mock_get_storage:
        mock_get_storage.return_value = mock_storage

        await confirm_reset(update, context)

        # Verify answer was sent
        query.answer.assert_awaited_once()

        # Verify spreadsheet was deleted
        mock_storage.delete_spreadsheet.assert_awaited_once_with(12345)

        # Verify success message
        query.edit_message_text.assert_awaited_once()
        message = query.edit_message_text.call_args[0][0]
        assert RESET_SUCCESS_TEXT in message
        assert "/start" in message


@pytest.mark.asyncio
async def test_cancel_reset():
    """Test the cancel reset callback."""
    # Create mock callback query
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    update = MagicMock()
    update.callback_query = query

    context = MagicMock()

    await cancel_reset(update, context)

    # Verify answer was sent
    query.answer.assert_awaited_once()

    # Verify cancellation message
    query.edit_message_text.assert_awaited_once_with("❌ Сброс данных отменен.")
