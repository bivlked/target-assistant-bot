from __future__ import annotations

import logging

from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.ext import ContextTypes

from config import telegram, logging_cfg
from core.goal_manager import GoalManager
from llm.client import LLMClient
from sheets.client import SheetsManager
from sheets.async_client import AsyncSheetsManager
from scheduler.tasks import Scheduler
from handlers.common import (
    start_handler,
    help_handler,
    cancel_handler,
    reset_handler,
    unknown_handler,
)
from handlers.goal_setting import build_setgoal_conv
from handlers.task_management import build_task_handlers
from utils.logging import setup_logging
from core.exceptions import BotError
from utils.sentry_integration import setup_sentry

# ---------------------------------------------------------------------------
# PTB >=20.9 содержит фикс слота __polling_cleanup_cb, дополнительный патч не нужен.
# ---------------------------------------------------------------------------

# ---------------------------------
# Настройка логирования
# ---------------------------------
logger = setup_logging(logging_cfg.level)


async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок Telegram."""
    error = context.error
    logger.error("Ошибка при обработке update=%s", update, exc_info=error)

    # Дружелюбное сообщение пользователю
    if isinstance(error, BotError):
        user_msg = error.user_friendly
    else:
        user_msg = "Произошла непредвиденная ошибка. Попробуйте позже."

    if update and update.effective_chat:
        try:
            await context.bot.send_message(update.effective_chat.id, user_msg)
        except Exception:  # noqa: BLE001
            pass


def main():
    # Инициализация Sentry (если настроено)
    setup_sentry()
    # Проверка токена
    if not telegram.token:
        logger.error("TELEGRAM_BOT_TOKEN не задан")
        return

    # Инициализация зависимостей
    sheets_manager = SheetsManager()
    sheets_async = AsyncSheetsManager()
    llm_client = LLMClient()
    goal_manager = GoalManager(
        sheets_sync=sheets_manager, sheets_async=sheets_async, llm_sync=llm_client
    )
    scheduler = Scheduler(goal_manager)

    # Запуск планировщика
    scheduler.start()

    # Создание приложения Telegram
    application = Application.builder().token(telegram.token).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("cancel", cancel_handler))
    application.add_handler(CommandHandler("reset", reset_handler(goal_manager)))

    # /start зависит от goal_manager и scheduler
    application.add_handler(
        CommandHandler("start", start_handler(goal_manager, scheduler))
    )

    # /setgoal диалог
    application.add_handler(build_setgoal_conv(goal_manager))

    # /today, /status, /motivation, /check
    today_handler, status_handler, motivation_handler, check_conv = build_task_handlers(
        goal_manager
    )
    application.add_handler(CommandHandler("today", today_handler))
    application.add_handler(CommandHandler("status", status_handler))
    application.add_handler(CommandHandler("motivation", motivation_handler))
    application.add_handler(check_conv)

    # неизвестные команды – фильтруем все, кроме перечисленных
    known_cmds = (
        r"^(\/)(start|help|setgoal|today|motivation|status|check|cancel|reset)(?:@\w+)?"
    )
    unknown_cmd_filter = filters.Command() & ~filters.Regex(known_cmds)
    application.add_handler(MessageHandler(unknown_cmd_filter, unknown_handler()))

    # Запуск бота
    application.add_error_handler(error_handler)
    logger.info("Бот запущен")
    application.run_polling()


if __name__ == "__main__":
    main()
