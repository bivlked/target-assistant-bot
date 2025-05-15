"""Tests for handlers in handlers/common.py."""

import pytest
import pytest_asyncio  # Импортируем pytest_asyncio
from unittest.mock import (
    AsyncMock,
    MagicMock,
)  # Убираем patch, он не используется здесь
from datetime import datetime, timezone

from telegram import Update, User, Message, Chat, Bot
from telegram.ext import ContextTypes

from handlers.common import (
    start_handler,
    help_handler,
    cancel_handler,
    reset_handler,
    unknown_handler,
)
from core.goal_manager import GoalManager
from scheduler.tasks import Scheduler
from texts import WELCOME_TEXT, HELP_TEXT, CANCEL_TEXT, RESET_SUCCESS_TEXT, UNKNOWN_TEXT

# --- Mocks ---


@pytest.fixture
def mock_goal_manager():
    """Fixture for a mock GoalManager."""
    mock = MagicMock(spec=GoalManager)
    mock.setup_user = AsyncMock()  # setup_user is async
    mock.reset_user = AsyncMock()  # reset_user is async
    return mock


@pytest.fixture
def mock_scheduler():
    """Fixture for a mock Scheduler."""
    mock = MagicMock(spec=Scheduler)
    # add_user_jobs is synchronous but takes a bot object
    mock.add_user_jobs = MagicMock()
    return mock


class MockMessage:
    """A simple mock for telegram.Message for testing reply_text."""

    def __init__(self, user_id: int, chat_id: int, text: str = "/test"):
        self.from_user = User(id=user_id, first_name="TestUser", is_bot=False)
        self.chat = Chat(id=chat_id, type="private")
        self.text = text
        self.reply_text = AsyncMock()  # reply_text is an AsyncMock attribute
        self.message_id = 1  # Dummy message_id
        self.date = datetime.now(timezone.utc)  # Dummy date


@pytest_asyncio.fixture
async def mock_update_message(
    monkeypatch: pytest.MonkeyPatch,
):  # monkeypatch может быть уже не нужен здесь
    """Fixture for a mock Update object with a mocked message."""
    # user_id и chat_id для MockMessage
    user_id = 123
    chat_id = 123
    # Используем наш MockMessage
    mock_msg = MockMessage(user_id=user_id, chat_id=chat_id, text="/start_command")

    update = Update(update_id=1, message=mock_msg)
    # Для PTB v20+ Update ожидает, что effective_user и effective_chat будут доступны.
    # Если хендлеры используют update.effective_user, их нужно мокать.
    # Наши хендлеры в common.py используют update.effective_user, так что мокаем.
    # monkeypatch.setattr(update, "effective_user", mock_msg.from_user) - нельзя для Update
    # monkeypatch.setattr(update, "effective_chat", mock_msg.chat) - нельзя для Update
    # Вместо этого, мы должны убедиться, что наши хендлеры корректно извлекают
    # user и chat из update.message.from_user и update.message.chat, что они и делают.
    # Для Sentry мы используем update.effective_user, так что его нужно мокать, если он None.
    # Update() конструктор сам устанавливает effective_user/chat из message, если он есть.
    return update


@pytest.fixture
def mock_bot():
    """Fixture for a mock Bot object."""
    return AsyncMock(spec=Bot)


@pytest.fixture
def mock_context(mock_bot):
    """Fixture for a mock ContextTypes.DEFAULT_TYPE."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = mock_bot
    return context


# --- Tests for start_handler ---


@pytest.mark.asyncio
async def test_start_handler_flow(
    mock_goal_manager, mock_scheduler, mock_update_message, mock_context
):
    """Test the complete flow of the /start command handler."""
    user_id = mock_update_message.message.from_user.id

    # Create the handler using the factory
    handler_fn = start_handler(mock_goal_manager, mock_scheduler)

    await handler_fn(mock_update_message, mock_context)

    # Assertions
    mock_goal_manager.setup_user.assert_awaited_once_with(user_id)
    mock_scheduler.add_user_jobs.assert_called_once_with(mock_context.bot, user_id)
    mock_update_message.message.reply_text.assert_awaited_once_with(WELCOME_TEXT)


# --- Tests for help_handler ---
@pytest.mark.asyncio
async def test_help_handler(mock_update_message, mock_context):
    """Test the /help command handler."""
    await help_handler(mock_update_message, mock_context)
    mock_update_message.message.reply_text.assert_awaited_once_with(
        HELP_TEXT, parse_mode="Markdown", disable_web_page_preview=True
    )


# --- Tests for cancel_handler ---
@pytest.mark.asyncio
async def test_cancel_handler(mock_update_message, mock_context):
    """Test the /cancel command handler."""
    await cancel_handler(mock_update_message, mock_context)
    mock_update_message.message.reply_text.assert_awaited_once_with(CANCEL_TEXT)


# --- Tests for unknown_handler ---
@pytest.mark.asyncio
async def test_unknown_handler(mock_update_message, mock_context):
    """Test the unknown command handler."""
    # unknown_handler is a factory
    handler_fn = unknown_handler()
    await handler_fn(mock_update_message, mock_context)
    mock_update_message.message.reply_text.assert_awaited_once_with(UNKNOWN_TEXT)


# --- Tests for reset_handler ---
@pytest.mark.asyncio
async def test_reset_handler_flow(mock_goal_manager, mock_update_message, mock_context):
    """Test the complete flow of the /reset command handler."""
    user_id = mock_update_message.message.from_user.id

    # Create the handler using the factory
    handler_fn = reset_handler(mock_goal_manager)

    await handler_fn(mock_update_message, mock_context)

    # Assertions
    mock_goal_manager.reset_user.assert_awaited_once_with(user_id)
    mock_update_message.message.reply_text.assert_awaited_once_with(RESET_SUCCESS_TEXT)
