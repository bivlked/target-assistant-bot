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


@pytest_asyncio.fixture
async def mock_bot_instance():
    """Fixture for a mock Bot object instance."""
    bot_mock = AsyncMock(spec=Bot)
    # bot_mock.send_message = AsyncMock() # Уже AsyncMock из-за spec=Bot, если Bot.send_message async
    # Если Bot.send_message не async в spec, то нужно мокать его как AsyncMock:
    # setattr(bot_mock, 'send_message', AsyncMock())
    return bot_mock


class MockMessage:  # Наш мок-класс
    def __init__(self, user_id: int, chat_id: int, text: str = "/test"):
        self.from_user = User(id=user_id, first_name="TestUser", is_bot=False)
        self.chat = Chat(id=chat_id, type="private")
        self.text = text
        self.reply_text = AsyncMock()
        self.message_id = 1
        self.date = datetime.now(timezone.utc)
        # Добавим атрибут bot, чтобы он был похож на настоящий Message, если кто-то его проверит
        # Хотя reply_text у нас уже мокнут и не будет использовать self.bot
        self.bot = None


@pytest_asyncio.fixture
async def mock_update_message(
    monkeypatch: pytest.MonkeyPatch,
):  # monkeypatch снова нужен
    """Fixture for a mock Update object with a Message mock that has a mocked reply_text."""
    user = User(id=123, first_name="TestUser", is_bot=False)
    chat = Chat(id=123, type="private")

    # Создаем MagicMock, который имитирует Message
    # Атрибуты from_user и chat будут установлены как MagicMock, если к ним будет обращение,
    # но мы их установим явно для наших тестов.
    # Важно: настоящий Message создается с bot, но мы его не используем, так как reply_text мокаем.
    message_mock = MagicMock(spec=Message)
    message_mock.from_user = user
    message_mock.chat = chat
    message_mock.text = "/test_command"
    message_mock.message_id = 1
    message_mock.date = datetime.now(timezone.utc)

    # Мокаем метод reply_text у этого экземпляра message_mock
    # setattr(message_mock, "reply_text", AsyncMock()) # Так тоже можно
    message_mock.reply_text = AsyncMock()

    update = Update(update_id=1, message=message_mock)
    return update


@pytest.fixture
def mock_context(mock_bot_instance: AsyncMock):
    """Fixture for a mock ContextTypes.DEFAULT_TYPE."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = mock_bot_instance
    return context


# --- Tests for start_handler ---


@pytest.mark.asyncio
async def test_start_handler_flow(
    mock_goal_manager, mock_scheduler, mock_update_message, mock_context
):
    """Test the complete flow of the /start command handler."""
    user_id = mock_update_message.message.from_user.id
    handler_fn = start_handler(mock_goal_manager, mock_scheduler)
    await handler_fn(mock_update_message, mock_context)

    mock_goal_manager.setup_user.assert_awaited_once_with(user_id)
    mock_scheduler.add_user_jobs.assert_called_once_with(
        mock_context.bot, user_id
    )  # context.bot используется здесь
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
    handler_fn = unknown_handler()
    await handler_fn(mock_update_message, mock_context)
    mock_update_message.message.reply_text.assert_awaited_once_with(UNKNOWN_TEXT)


# --- Tests for reset_handler ---
@pytest.mark.asyncio
async def test_reset_handler_flow(mock_goal_manager, mock_update_message, mock_context):
    """Test the complete flow of the /reset command handler."""
    user_id = mock_update_message.message.from_user.id
    handler_fn = reset_handler(mock_goal_manager)
    await handler_fn(mock_update_message, mock_context)

    mock_goal_manager.reset_user.assert_awaited_once_with(user_id)
    mock_update_message.message.reply_text.assert_awaited_once_with(RESET_SUCCESS_TEXT)
