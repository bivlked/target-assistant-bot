"""Tests for handlers/goals.py: Multi-goal management and goal creation/editing dialogues."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import cast

from telegram import Update, User, Message, Chat, CallbackQuery
from telegram.ext import ConversationHandler, ContextTypes
from telegram.constants import ParseMode

from handlers.goals import (
    add_goal_conversation,
    add_goal_command_start,
    add_goal_start,
    goal_name_received,
    goal_description_received,
    goal_deadline_received,
    goal_daily_time_received,
    goal_priority_received,
    goal_tags_received,
    goal_confirmed,
    my_goals_command,
    manage_goals_menu,
    show_goal_details,
    # States (importing for clarity, though integers are fine)
    GOAL_NAME,
    GOAL_DESCRIPTION,
    GOAL_DEADLINE,
    GOAL_DAILY_TIME,
    GOAL_PRIORITY,
    GOAL_TAGS,
    GOAL_CONFIRM,
)
from core.models import Goal, GoalPriority, GoalStatus, TaskStatus
from utils.helpers import escape_markdown_v2


@pytest.fixture
def mock_user() -> User:
    """Returns a mock Telegram User."""
    return User(id=123, first_name="Test", is_bot=False, username="testuser")


@pytest.fixture
def mock_chat() -> Chat:
    """Returns a mock Telegram Chat."""
    return Chat(id=123, type="private")


@pytest.fixture
def mock_update_message(mock_user: User, mock_chat: Chat) -> Update:
    """Returns a mock Update object with a message."""
    message = MagicMock(spec=Message)
    message.message_id = 1
    message.date = datetime.now(timezone.utc)
    message.chat = mock_chat
    message.from_user = mock_user
    message.text = ""
    message.reply_text = AsyncMock()
    return Update(update_id=1, message=message)


@pytest.fixture
def mock_update_callback_query(mock_user: User, mock_chat: Chat) -> Update:
    """Returns a mock Update object with a callback query."""
    message = MagicMock(spec=Message)
    message.message_id = 1
    message.date = datetime.now(timezone.utc)
    message.chat = mock_chat
    message.from_user = mock_user

    callback_query = MagicMock(spec=CallbackQuery)
    callback_query.id = "test_callback_id"
    callback_query.from_user = mock_user
    callback_query.chat_instance = "test_chat_instance"
    callback_query.data = ""
    callback_query.message = message
    callback_query.answer = AsyncMock()
    callback_query.edit_message_text = AsyncMock()
    return Update(update_id=1, callback_query=callback_query)


@pytest.fixture
def mock_context(mock_user_data: dict | None = None) -> ContextTypes.DEFAULT_TYPE:
    """Returns a mock PTB context."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock()
    context.user_data = mock_user_data if mock_user_data is not None else {}
    context.chat_data = {}
    context.application = MagicMock()
    return context


@pytest.mark.asyncio
async def test_add_goal_command_start_new_user_no_goals_limit_ok(
    mock_update_message: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test /add_goal command entry point when user has no goals (limit is fine)."""
    assert mock_update_message.message is not None  # Mypy check
    reply_text_mock = cast(AsyncMock, mock_update_message.message.reply_text)
    with (
        patch("handlers.goals.is_subscribed", AsyncMock(return_value=True)),
        patch("handlers.goals.get_async_storage") as mock_get_storage,
    ):

        mock_storage_instance = AsyncMock()
        mock_storage_instance.get_active_goals_count.return_value = 0  # No active goals
        mock_get_storage.return_value = mock_storage_instance

        state = await add_goal_command_start(mock_update_message, mock_context)

        assert state == GOAL_NAME
        assert reply_text_mock.await_count == 1
        call_args = reply_text_mock.await_args
        assert call_args is not None
        assert "Шаг 1/6: Введите короткое название цели" in call_args.args[0]
        assert call_args.kwargs.get("parse_mode") == ParseMode.MARKDOWN_V2


@pytest.mark.asyncio
async def test_add_goal_command_start_goal_limit_reached(
    mock_update_message: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test /add_goal command entry point when user has reached goal limit."""
    assert mock_update_message.message is not None  # Mypy check
    reply_text_mock = cast(AsyncMock, mock_update_message.message.reply_text)
    with (
        patch("handlers.goals.is_subscribed", AsyncMock(return_value=True)),
        patch("handlers.goals.get_async_storage") as mock_get_storage,
    ):

        mock_storage_instance = AsyncMock()
        mock_storage_instance.get_active_goals_count.return_value = (
            10  # Goal limit reached
        )
        mock_get_storage.return_value = mock_storage_instance

        state = await add_goal_command_start(mock_update_message, mock_context)

        assert state == ConversationHandler.END
        assert reply_text_mock.await_count == 1
        call_args = reply_text_mock.await_args
        assert call_args is not None
        assert "Достигнут лимит активных целей" in call_args.args[0]
        assert call_args.kwargs.get("parse_mode") == ParseMode.MARKDOWN_V2


@pytest.mark.asyncio
async def test_add_goal_callback_start_limit_ok(
    mock_update_callback_query: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test add_goal callback query entry point when limit is fine."""
    assert mock_update_callback_query.callback_query is not None  # Mypy check
    callback_query_mock_instance = cast(
        MagicMock, mock_update_callback_query.callback_query
    )
    callback_query_mock_instance.data = "add_goal"

    answer_mock = cast(AsyncMock, callback_query_mock_instance.answer)
    edit_message_text_mock = cast(
        AsyncMock, callback_query_mock_instance.edit_message_text
    )

    with patch("handlers.goals.get_async_storage") as mock_get_storage:
        mock_storage_instance = AsyncMock()
        mock_storage_instance.get_active_goals_count.return_value = 0
        mock_get_storage.return_value = mock_storage_instance

        state = await add_goal_start(mock_update_callback_query, mock_context)

        assert state == GOAL_NAME
        assert answer_mock.await_count == 1
        assert edit_message_text_mock.await_count == 1
        call_args = edit_message_text_mock.await_args
        assert call_args is not None
        assert "Шаг 1/6: Введите короткое название цели" in call_args.args[0]
        assert call_args.kwargs.get("parse_mode") == ParseMode.MARKDOWN_V2


# Need to import datetime and timezone for mock_update_message
from datetime import datetime, timezone

# TODO: Add more tests for other states:
# - goal_name_received (valid and invalid)
# - goal_description_received (valid and invalid)
# - goal_deadline_received
# - goal_daily_time_received
# - goal_priority_received
# - goal_tags_received (with and without tags)
# - goal_confirmed (confirm and cancel)
# - Successful goal creation with mocked LLM and storage calls
# - my_goals_command (no goals, with goals)
# - manage_goals_menu
# - show_goal_details
# - Other callback handlers for editing/deleting goals

# Add any other necessary imports and test cases as needed
