from __future__ import annotations

import logging

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import telegram, logging_cfg
from core.goal_manager import GoalManager
from llm.client import LLMClient
from sheets.client import SheetsManager
from scheduler.tasks import Scheduler
from handlers.common import start_handler, help_handler, cancel_handler, reset_handler, unknown_handler
from handlers.goal_setting import build_setgoal_conv
from handlers.task_management import build_task_handlers

# ---------------------------------------------------------------------------
# Временный патч для python-telegram-bot 20.8 на Python 3.13
# Ошибка AttributeError: '_Updater__polling_cleanup_cb' — отсутствует слот
# Исправлено в PTB 20.9+, но пока ставим динамический патч, добавляющий слот.
# ---------------------------------------------------------------------------
from telegram.ext import _updater as _tg_up

if hasattr(_tg_up, "Updater"):
    updater_cls = _tg_up.Updater
    missing_slot = "_Updater__polling_cleanup_cb"
    if hasattr(updater_cls, "__slots__") and missing_slot not in updater_cls.__slots__:
        # расширяем кортеж слотов
        updater_cls.__slots__ = (*updater_cls.__slots__, missing_slot)

# ---------------------------------
# Настройка логирования
# ---------------------------------
logging.basicConfig(level=logging_cfg.level, format=logging_cfg.format)

logger = logging.getLogger(__name__)


def main():
    # Проверка токена
    if not telegram.token:
        logger.error("TELEGRAM_BOT_TOKEN не задан")
        return

    # Инициализация зависимостей
    sheets_manager = SheetsManager()
    llm_client = LLMClient()
    goal_manager = GoalManager(sheets_manager, llm_client)
    scheduler = Scheduler(goal_manager)

    # Запуск планировщика
    scheduler.start()

    # Создание приложения Telegram
    application = Application.builder().token(telegram.token).concurrent_updates(True).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("cancel", cancel_handler))
    application.add_handler(CommandHandler("reset", reset_handler(goal_manager)))

    # /start зависит от goal_manager и scheduler
    application.add_handler(CommandHandler("start", start_handler(goal_manager, scheduler)))

    # /setgoal диалог
    application.add_handler(build_setgoal_conv(goal_manager))

    # /today, /status, /motivation, /check
    today_handler, status_handler, motivation_handler, check_conv = build_task_handlers(goal_manager)
    application.add_handler(CommandHandler("today", today_handler))
    application.add_handler(CommandHandler("status", status_handler))
    application.add_handler(CommandHandler("motivation", motivation_handler))
    application.add_handler(check_conv)

    # неизвестные команды – фильтруем все, кроме перечисленных
    known_cmds = r"^(\/)(start|help|setgoal|today|motivation|status|check|cancel|reset)(?:@\w+)?"
    unknown_cmd_filter = filters.COMMAND & ~filters.Regex(known_cmds)
    application.add_handler(MessageHandler(unknown_cmd_filter, unknown_handler()))

    # Запуск бота
    logger.info("Бот запущен")
    application.run_polling()


if __name__ == "__main__":
    main() 