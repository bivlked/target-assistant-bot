"""Enhanced tests for handlers/common.py to achieve better coverage.

Focus on edge cases and error scenarios not covered by basic tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Message, CallbackQuery, Chat
from telegram.ext import ContextTypes

from handlers.common import (
    start_handler,
    help_handler,
    cancel_handler,
    reset_handler,
    confirm_reset,
    cancel_reset,
    unknown_handler,
)
from scheduler.tasks import Scheduler


@pytest.fixture
def mock_scheduler():
    """Create a mock scheduler for testing."""
    scheduler = MagicMock(spec=Scheduler)
    scheduler.add_user_jobs = MagicMock()
    return scheduler


@pytest.fixture
def mock_context():
    """Create a mock context for testing."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = MagicMock()
    return context


def create_update_with_none_user():
    """Create an update with None effective_user for testing edge cases."""
    update = MagicMock(spec=Update)
    update.effective_user = None
    update.message = MagicMock(spec=Message)
    return update


def create_update_with_none_message():
    """Create an update with None message for testing edge cases."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 123
    update.message = None
    return update


def create_valid_update():
    """Create a valid update for testing."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 123
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    return update


@pytest.mark.asyncio
async def test_start_handler_no_effective_user(mock_scheduler, mock_context):
    """Test start handler when update has no effective_user (covers line 80)."""
    handler = start_handler(mock_scheduler)
    update = create_update_with_none_user()

    # Should return early without processing
    result = await handler.callback(update, mock_context)

    # Should return None and not call any scheduler methods
    assert result is None
    mock_scheduler.add_user_jobs.assert_not_called()


@pytest.mark.asyncio
async def test_start_handler_no_message(mock_scheduler, mock_context):
    """Test start handler when update has no message (covers line 80)."""
    handler = start_handler(mock_scheduler)
    update = create_update_with_none_message()

    # Should return early without processing
    result = await handler.callback(update, mock_context)

    # Should return None and not call any scheduler methods
    assert result is None
    mock_scheduler.add_user_jobs.assert_not_called()


@pytest.mark.asyncio
async def test_help_handler_no_effective_user(mock_context):
    """Test help handler when update has no effective_user (covers line 118)."""
    update = create_update_with_none_user()

    # Should return early without processing
    result = await help_handler(update, mock_context)

    # Should return None and not call reply_text
    assert result is None
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_help_handler_no_message(mock_context):
    """Test help handler when update has no message (covers line 118)."""
    update = create_update_with_none_message()

    # Should return early without processing
    result = await help_handler(update, mock_context)

    # Should return None
    assert result is None


@pytest.mark.asyncio
async def test_cancel_handler_no_effective_user(mock_context):
    """Test cancel handler when update has no effective_user (covers line 133)."""
    update = create_update_with_none_user()

    # Should return early without processing
    result = await cancel_handler(update, mock_context)

    # Should return None and not call reply_text
    assert result is None
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_handler_no_message(mock_context):
    """Test cancel handler when update has no message (covers line 133)."""
    update = create_update_with_none_message()

    # Should return early without processing
    result = await cancel_handler(update, mock_context)

    # Should return None
    assert result is None


@pytest.mark.asyncio
async def test_reset_handler_no_effective_user(mock_context):
    """Test reset handler when update has no effective_user (covers line 146)."""
    update = create_update_with_none_user()

    # Should return early without processing
    result = await reset_handler(update, mock_context)

    # Should return None and not call reply_text
    assert result is None
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_reset_handler_no_message(mock_context):
    """Test reset handler when update has no message (covers line 146)."""
    update = create_update_with_none_message()

    # Should return early without processing
    result = await reset_handler(update, mock_context)

    # Should return None
    assert result is None


@pytest.mark.asyncio
async def test_reset_handler_unsubscribed_user(mock_context):
    """Test reset handler when user is not subscribed (covers line 177)."""
    update = create_valid_update()

    # Mock is_subscribed to return False
    with patch("handlers.common.is_subscribed", return_value=False):
        await reset_handler(update, mock_context)

    # Should send unsubscribed message
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    # First positional argument contains the text
    assert "Вы не подписаны на бота" in call_args.args[0]


@pytest.mark.asyncio
async def test_confirm_reset_exception_handling(mock_context):
    """Test confirm_reset exception handling (covers line 191-193)."""
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.from_user = MagicMock(spec=User)
    query.from_user.id = 123
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    update.callback_query = query

    # Mock storage to raise exception
    with patch("handlers.common.get_async_storage") as mock_storage_func:
        mock_storage = AsyncMock()
        mock_storage.delete_spreadsheet = AsyncMock(
            side_effect=Exception("Storage error")
        )
        mock_storage_func.return_value = mock_storage

        await confirm_reset(update, mock_context)

    # Should handle exception and send error message
    query.edit_message_text.assert_called_once()
    call_args = query.edit_message_text.call_args
    # First positional argument contains the text
    assert "Произошла ошибка при сбросе данных" in call_args.args[0]


@pytest.mark.asyncio
async def test_cancel_reset_no_query(mock_context):
    """Test cancel_reset when update has no callback_query (covers line 205)."""
    update = MagicMock(spec=Update)
    update.callback_query = None

    # Should return early without processing
    result = await cancel_reset(update, mock_context)

    # Should return None
    assert result is None


@pytest.mark.asyncio
async def test_unknown_handler_no_effective_user(mock_context):
    """Test unknown handler when update has no effective_user (covers line 217)."""
    update = create_update_with_none_user()

    # Should return early without processing
    result = await unknown_handler(update, mock_context)

    # Should return None and not call reply_text
    assert result is None
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_handler_no_message(mock_context):
    """Test unknown handler when update has no message (covers line 217)."""
    update = create_update_with_none_message()

    # Should return early without processing
    result = await unknown_handler(update, mock_context)

    # Should return None
    assert result is None


@pytest.mark.asyncio
async def test_confirm_reset_no_user():
    """Test confirm_reset when callback_query has no from_user."""
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.from_user = None
    update.callback_query = query

    # Should return early without processing
    result = await confirm_reset(update, None)

    # Should return None
    assert result is None


@pytest.mark.asyncio
async def test_confirm_reset_no_query():
    """Test confirm_reset when update has no callback_query."""
    update = MagicMock(spec=Update)
    update.callback_query = None

    # Should return early without processing
    result = await confirm_reset(update, None)

    # Should return None
    assert result is None
