"""Tests for handlers/goals.py: Multi-goal management and goal creation/editing dialogues."""

# type: ignore[operator, index]

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, _Call
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
        call_args = cast(_Call, call_args)
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
        call_args = cast(_Call, call_args)
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
        call_args = cast(_Call, call_args)
        assert "Шаг 1/6: Введите короткое название цели" in call_args.args[0]
        assert call_args.kwargs.get("parse_mode") == ParseMode.MARKDOWN_V2


# Need to import datetime and timezone for mock_update_message
from datetime import datetime, timezone

# Goal handlers tests: comprehensive coverage for all missing TODO items


@pytest.mark.asyncio
async def test_goal_name_received_valid_input(
    mock_update_message: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test goal_name_received with valid input."""
    assert mock_update_message.message is not None
    mock_update_message.message.text = "Изучить Python"
    reply_text_mock = cast(AsyncMock, mock_update_message.message.reply_text)

    state = await goal_name_received(mock_update_message, mock_context)

    assert state == GOAL_DESCRIPTION
    assert mock_context.user_data["goal_name"] == "Изучить Python"
    assert reply_text_mock.await_count == 1
    call_args = reply_text_mock.await_args
    assert call_args is not None
    call_args = cast(_Call, call_args)
    assert "Шаг 2/6" in call_args.args[0]  # type: ignore[index]
    assert call_args.kwargs.get("parse_mode") == ParseMode.MARKDOWN_V2


@pytest.mark.asyncio
async def test_goal_name_received_invalid_input_too_long(
    mock_update_message: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test goal_name_received with valid input (no too long validation in actual code)."""
    assert mock_update_message.message is not None
    mock_update_message.message.text = "А" * 51  # This is actually valid
    reply_text_mock = cast(AsyncMock, mock_update_message.message.reply_text)

    state = await goal_name_received(mock_update_message, mock_context)

    assert state == GOAL_DESCRIPTION  # Proceeds to next state
    assert mock_context.user_data["goal_name"] == "А" * 51
    assert reply_text_mock.await_count == 1
    call_args = reply_text_mock.await_args
    assert call_args is not None
    call_args = cast(_Call, call_args)
    assert "Шаг 2/6" in call_args.args[0]  # type: ignore[index]


@pytest.mark.asyncio
async def test_goal_name_received_invalid_input_empty(
    mock_update_message: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test goal_name_received with empty input."""
    assert mock_update_message.message is not None
    mock_update_message.message.text = ""
    reply_text_mock = cast(AsyncMock, mock_update_message.message.reply_text)

    state = await goal_name_received(mock_update_message, mock_context)

    assert state == GOAL_NAME  # Returns to wait for valid input
    assert "goal_name" not in mock_context.user_data  # type: ignore[operator]
    # No reply_text call for empty input - it returns early
    assert reply_text_mock.await_count == 0


@pytest.mark.asyncio
async def test_goal_name_received_invalid_input_too_short(
    mock_update_message: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test goal_name_received with too short input (actual validation)."""
    assert mock_update_message.message is not None
    mock_update_message.message.text = "А"  # Too short (< 3 chars)
    reply_text_mock = cast(AsyncMock, mock_update_message.message.reply_text)

    state = await goal_name_received(mock_update_message, mock_context)

    assert state == GOAL_NAME
    assert "goal_name" not in mock_context.user_data  # type: ignore[operator]
    assert reply_text_mock.await_count == 1
    call_args = reply_text_mock.await_args
    assert call_args is not None
    call_args = cast(_Call, call_args)
    assert "минимум 3 символа" in call_args.args[0]  # type: ignore[index]


@pytest.mark.asyncio
async def test_goal_description_received_valid_input(
    mock_update_message: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test goal_description_received with valid input."""
    assert mock_update_message.message is not None
    mock_update_message.message.text = "Освоить основы программирования на Python"
    reply_text_mock = cast(AsyncMock, mock_update_message.message.reply_text)

    state = await goal_description_received(mock_update_message, mock_context)

    assert state == GOAL_DEADLINE
    assert (
        mock_context.user_data["goal_description"]
        == "Освоить основы программирования на Python"
    )
    assert reply_text_mock.await_count == 1
    call_args = reply_text_mock.await_args
    assert call_args is not None
    call_args = cast(_Call, call_args)
    assert "Шаг 3/6" in call_args.args[0]  # type: ignore[index]


@pytest.mark.asyncio
async def test_goal_description_received_invalid_input_too_long(
    mock_update_message: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test goal_description_received with valid long input (no max length validation)."""
    assert mock_update_message.message is not None
    mock_update_message.message.text = "А" * 501  # This is actually valid
    reply_text_mock = cast(AsyncMock, mock_update_message.message.reply_text)

    state = await goal_description_received(mock_update_message, mock_context)

    assert state == GOAL_DEADLINE  # Proceeds to next state
    assert mock_context.user_data["goal_description"] == "А" * 501
    assert reply_text_mock.await_count == 1
    call_args = reply_text_mock.await_args
    assert call_args is not None
    call_args = cast(_Call, call_args)
    assert "Шаг 3/6" in call_args.args[0]  # type: ignore[index]


@pytest.mark.asyncio
async def test_goal_deadline_received_valid_input(
    mock_update_message: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test goal_deadline_received with valid deadline (no parsing validation)."""
    assert mock_update_message.message is not None
    mock_update_message.message.text = "3 месяца"
    reply_text_mock = cast(AsyncMock, mock_update_message.message.reply_text)

    state = await goal_deadline_received(mock_update_message, mock_context)

    assert state == GOAL_DAILY_TIME
    assert mock_context.user_data["goal_deadline"] == "3 месяца"
    assert reply_text_mock.await_count == 1
    call_args = reply_text_mock.await_args
    assert call_args is not None
    call_args = cast(_Call, call_args)
    assert "Шаг 4/6" in call_args.args[0]  # type: ignore[index]


@pytest.mark.asyncio
async def test_goal_deadline_received_invalid_input(
    mock_update_message: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test goal_deadline_received with empty input."""
    assert mock_update_message.message is not None
    mock_update_message.message.text = ""
    reply_text_mock = cast(AsyncMock, mock_update_message.message.reply_text)

    state = await goal_deadline_received(mock_update_message, mock_context)

    assert state == GOAL_DEADLINE
    assert "goal_deadline" not in mock_context.user_data  # type: ignore[operator]
    # No reply_text call for empty input - it returns early
    assert reply_text_mock.await_count == 0


@pytest.mark.asyncio
async def test_goal_daily_time_received_valid_input(
    mock_update_message: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test goal_daily_time_received with valid time format."""
    assert mock_update_message.message is not None
    mock_update_message.message.text = "1 час"
    reply_text_mock = cast(AsyncMock, mock_update_message.message.reply_text)

    state = await goal_daily_time_received(mock_update_message, mock_context)

    assert state == GOAL_PRIORITY
    assert mock_context.user_data["goal_daily_time"] == "1 час"
    assert reply_text_mock.await_count == 1
    call_args = reply_text_mock.await_args
    assert call_args is not None
    call_args = cast(_Call, call_args)
    assert "Шаг 5/6" in call_args.args[0]  # type: ignore[index]


@pytest.mark.asyncio
async def test_goal_daily_time_received_invalid_input(
    mock_update_message: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test goal_daily_time_received with invalid time format."""
    assert mock_update_message.message is not None
    mock_update_message.message.text = ""  # Empty input
    reply_text_mock = cast(AsyncMock, mock_update_message.message.reply_text)

    state = await goal_daily_time_received(mock_update_message, mock_context)

    assert state == GOAL_DAILY_TIME
    assert "goal_daily_time" not in mock_context.user_data  # type: ignore[operator]
    # No reply_text call for empty input - it returns early
    assert reply_text_mock.await_count == 0


@pytest.mark.asyncio
async def test_goal_priority_received_high_priority(
    mock_update_callback_query: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test goal_priority_received with high priority selection."""
    assert mock_update_callback_query.callback_query is not None
    callback_query_mock = cast(MagicMock, mock_update_callback_query.callback_query)
    callback_query_mock.data = "priority_high"
    answer_mock = cast(AsyncMock, callback_query_mock.answer)
    edit_message_text_mock = cast(AsyncMock, callback_query_mock.edit_message_text)

    state = await goal_priority_received(mock_update_callback_query, mock_context)

    assert state == GOAL_TAGS
    # Priority is stored as enum object, not .value
    assert mock_context.user_data["goal_priority"] == GoalPriority.HIGH
    assert answer_mock.await_count == 1
    assert edit_message_text_mock.await_count == 1


@pytest.mark.asyncio
async def test_goal_priority_received_medium_priority(
    mock_update_callback_query: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test goal_priority_received with medium priority selection."""
    assert mock_update_callback_query.callback_query is not None
    callback_query_mock = cast(MagicMock, mock_update_callback_query.callback_query)
    callback_query_mock.data = "priority_medium"
    answer_mock = cast(AsyncMock, callback_query_mock.answer)
    edit_message_text_mock = cast(AsyncMock, callback_query_mock.edit_message_text)

    state = await goal_priority_received(mock_update_callback_query, mock_context)

    assert state == GOAL_TAGS
    # Priority is stored as enum object, not .value
    assert mock_context.user_data["goal_priority"] == GoalPriority.MEDIUM


@pytest.mark.asyncio
async def test_goal_tags_received_with_tags(
    mock_update_message: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test goal_tags_received with tags provided."""
    assert mock_update_message.message is not None
    mock_update_message.message.text = "учеба, программирование, python"
    reply_text_mock = cast(AsyncMock, mock_update_message.message.reply_text)

    # Set up context with previous goal data (using enum objects, not .value)
    mock_context.user_data = {
        "goal_name": "Изучить Python",
        "goal_description": "Освоить основы",
        "goal_deadline": "3 месяца",
        "goal_daily_time": "1 час",
        "goal_priority": GoalPriority.HIGH,  # enum object, not .value
    }

    state = await goal_tags_received(mock_update_message, mock_context)

    assert state == GOAL_CONFIRM
    assert "goal_tags" in mock_context.user_data
    expected_tags = ["учеба", "программирование", "python"]
    assert mock_context.user_data["goal_tags"] == expected_tags
    assert reply_text_mock.await_count == 1


@pytest.mark.asyncio
async def test_goal_tags_received_without_tags(
    mock_update_message: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test goal_tags_received when user skips tags."""
    assert mock_update_message.message is not None
    mock_update_message.message.text = "-"  # Skip marker
    reply_text_mock = cast(AsyncMock, mock_update_message.message.reply_text)

    # Set up context with previous goal data (using enum objects, not .value)
    mock_context.user_data = {
        "goal_name": "Изучить Python",
        "goal_description": "Освоить основы",
        "goal_deadline": "3 месяца",
        "goal_daily_time": "1 час",
        "goal_priority": GoalPriority.HIGH,  # enum object, not .value
    }

    state = await goal_tags_received(mock_update_message, mock_context)

    assert state == GOAL_CONFIRM
    assert mock_context.user_data["goal_tags"] == []
    assert reply_text_mock.await_count == 1


@pytest.mark.asyncio
async def test_goal_confirmed_confirm_successful_creation(
    mock_update_callback_query: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test goal_confirmed when user confirms and goal creation succeeds."""
    assert mock_update_callback_query.callback_query is not None
    callback_query_mock = cast(MagicMock, mock_update_callback_query.callback_query)
    callback_query_mock.data = "confirm_goal"
    answer_mock = cast(AsyncMock, callback_query_mock.answer)
    edit_message_text_mock = cast(AsyncMock, callback_query_mock.edit_message_text)

    # Set up complete goal data in context (using enum objects)
    mock_context.user_data = {
        "goal_name": "Изучить Python",
        "goal_description": "Освоить основы программирования",
        "goal_deadline": "3 месяца",
        "goal_daily_time": "1 час",
        "goal_priority": GoalPriority.HIGH,  # enum object, not .value
        "goal_tags": ["учеба", "python"],
    }

    with (
        patch("handlers.goals.get_async_storage") as mock_get_storage,
        patch("handlers.goals.get_async_llm") as mock_get_llm,
        patch("handlers.goals.format_date") as mock_format_date,
    ):
        mock_storage = AsyncMock()
        mock_storage.get_next_goal_id.return_value = 1
        mock_storage.save_goal_info.return_value = "https://sheets.url"
        mock_get_storage.return_value = mock_storage

        mock_llm = AsyncMock()
        mock_llm.generate_plan.return_value = [{"day_number": 1, "task": "Test task"}]
        mock_get_llm.return_value = mock_llm

        mock_format_date.return_value = "01.01.2025"

        state = await goal_confirmed(mock_update_callback_query, mock_context)

        assert state == ConversationHandler.END
        assert answer_mock.await_count == 1
        # Handler calls edit_message_text twice (loading message + success message)
        assert edit_message_text_mock.await_count == 2

        # Verify storage calls
        mock_storage.save_goal_info.assert_called_once()
        mock_storage.save_plan.assert_called_once()
        mock_llm.generate_plan.assert_called_once()


@pytest.mark.asyncio
async def test_goal_confirmed_cancel(
    mock_update_callback_query: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test goal_confirmed when user cancels goal creation."""
    assert mock_update_callback_query.callback_query is not None
    callback_query_mock = cast(MagicMock, mock_update_callback_query.callback_query)
    callback_query_mock.data = "cancel_goal"
    answer_mock = cast(AsyncMock, callback_query_mock.answer)
    edit_message_text_mock = cast(AsyncMock, callback_query_mock.edit_message_text)

    state = await goal_confirmed(mock_update_callback_query, mock_context)

    assert state == ConversationHandler.END
    assert answer_mock.await_count == 1
    assert edit_message_text_mock.await_count == 1
    call_args = edit_message_text_mock.await_args
    assert call_args is not None
    call_args = cast(_Call, call_args)
    assert "Создание цели отменено" in call_args.args[0]  # type: ignore[index]


@pytest.mark.asyncio
async def test_my_goals_command_no_goals(
    mock_update_message: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test my_goals_command when user has no goals."""
    assert mock_update_message.message is not None
    reply_text_mock = cast(AsyncMock, mock_update_message.message.reply_text)

    # Create proper statistics mock structure
    stats_mock = {
        "total_goals": 0,
        "active_count": 0,
        "completed_count": 0,
        "archived_count": 0,
        "total_progress": 0,
        "active_goals": [],
        "can_add_more": True,
    }

    with (
        patch("handlers.goals.is_subscribed", AsyncMock(return_value=True)),
        patch("handlers.goals.get_async_storage") as mock_get_storage,
    ):
        mock_storage = AsyncMock()
        mock_storage.get_overall_statistics.return_value = stats_mock
        mock_get_storage.return_value = mock_storage

        await my_goals_command(mock_update_message, mock_context)

        assert reply_text_mock.await_count == 1
        call_args = reply_text_mock.await_args
        assert call_args is not None
        call_args = cast(_Call, call_args)
        assert "У вас пока нет целей" in call_args.args[0]  # type: ignore[index]


@pytest.mark.asyncio
async def test_my_goals_command_with_goals(
    mock_update_message: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test my_goals_command when user has goals."""
    assert mock_update_message.message is not None
    reply_text_mock = cast(AsyncMock, mock_update_message.message.reply_text)

    test_goal = Goal(
        goal_id=1,
        name="Test Goal",
        description="Test Description",
        deadline="1 месяц",
        daily_time="30 минут",
        start_date="01.01.2025",
        status=GoalStatus.ACTIVE,
        priority=GoalPriority.HIGH,
        tags=["test"],
        progress_percent=50,
    )

    # Create proper statistics mock structure
    stats_mock = {
        "total_goals": 1,
        "active_count": 1,
        "completed_count": 0,
        "archived_count": 0,
        "total_progress": 50,
        "active_goals": [test_goal],
        "can_add_more": True,
    }

    with (
        patch("handlers.goals.is_subscribed", AsyncMock(return_value=True)),
        patch("handlers.goals.get_async_storage") as mock_get_storage,
    ):
        mock_storage = AsyncMock()
        mock_storage.get_overall_statistics.return_value = stats_mock
        mock_get_storage.return_value = mock_storage

        await my_goals_command(mock_update_message, mock_context)

        assert reply_text_mock.await_count == 1
        call_args = reply_text_mock.await_args
        assert call_args is not None
        call_args = cast(_Call, call_args)
        # Should show goals with inline keyboard
        assert "reply_markup" in call_args.kwargs


@pytest.mark.asyncio
async def test_manage_goals_menu(
    mock_update_callback_query: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test manage_goals_menu callback."""
    assert mock_update_callback_query.callback_query is not None
    callback_query_mock = cast(MagicMock, mock_update_callback_query.callback_query)
    callback_query_mock.data = "manage_goals"
    answer_mock = cast(AsyncMock, callback_query_mock.answer)
    edit_message_text_mock = cast(AsyncMock, callback_query_mock.edit_message_text)

    test_goal = Goal(
        goal_id=1,
        name="Test Goal",
        description="Test Description",
        deadline="1 месяц",
        daily_time="30 минут",
        start_date="01.01.2025",
        status=GoalStatus.ACTIVE,
        priority=GoalPriority.HIGH,
        tags=["test"],
        progress_percent=50,
    )

    with patch("handlers.goals.get_async_storage") as mock_get_storage:
        mock_storage = AsyncMock()
        mock_storage.get_active_goals.return_value = [test_goal]
        mock_get_storage.return_value = mock_storage

        await manage_goals_menu(mock_update_callback_query, mock_context)

        assert answer_mock.await_count == 1
        assert edit_message_text_mock.await_count == 1
        call_args = edit_message_text_mock.await_args
        assert call_args is not None
        call_args = cast(_Call, call_args)
        assert "reply_markup" in call_args.kwargs


@pytest.mark.asyncio
async def test_show_goal_details(
    mock_update_callback_query: Update, mock_context: ContextTypes.DEFAULT_TYPE
):
    """Test show_goal_details callback."""
    assert mock_update_callback_query.callback_query is not None
    callback_query_mock = cast(MagicMock, mock_update_callback_query.callback_query)
    callback_query_mock.data = "goal_1"  # Correct format: goal_<id>
    answer_mock = cast(AsyncMock, callback_query_mock.answer)
    edit_message_text_mock = cast(AsyncMock, callback_query_mock.edit_message_text)

    test_goal = Goal(
        goal_id=1,
        name="Test Goal",
        description="Test Description",
        deadline="1 месяц",
        daily_time="30 минут",
        start_date="01.01.2025",
        status=GoalStatus.ACTIVE,
        priority=GoalPriority.HIGH,
        tags=["test"],
        progress_percent=50,
    )

    # Mock goal statistics object
    from core.models import GoalStatistics

    test_stats = GoalStatistics(
        total_tasks=10,
        completed_tasks=5,
        progress_percent=50,
        days_elapsed=5,
        days_remaining=25,
        completion_rate=0.5,
    )

    with patch("handlers.goals.get_async_storage") as mock_get_storage:
        mock_storage = AsyncMock()
        mock_storage.get_goal_by_id.return_value = test_goal
        mock_storage.get_goal_statistics.return_value = test_stats
        mock_get_storage.return_value = mock_storage

        await show_goal_details(mock_update_callback_query, mock_context)

        assert answer_mock.await_count == 1
        assert edit_message_text_mock.await_count == 1
        call_args = edit_message_text_mock.await_args
        assert call_args is not None
        call_args = cast(_Call, call_args)
        assert "Test Goal" in call_args.args[0]  # type: ignore[index]
