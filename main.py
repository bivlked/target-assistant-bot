from __future__ import annotations  # Should be the very first line

import sys
import os

print(f"Initial sys.path: {sys.path}")
print(f"Initial CWD: {os.getcwd()}")

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file at the very beginning

import logging
import asyncio
from threading import Thread

from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.ext import ContextTypes

from config import (
    telegram,
    google,
    openai_cfg as llm_config,
    scheduler_cfg as global_scheduler_config,
    ratelimiter_cfg,
    cache_config,
    logging_cfg,
)
from core.goal_manager import GoalManager
from core.interfaces import AsyncStorageInterface, AsyncLLMInterface

# Явные импорты функций добавления хендлеров из правильных имен файлов
from handlers.common import add_common_handlers
from handlers.goal_setting import build_setgoal_conv
from handlers.task_management import build_task_handlers
from llm.llm_client import AsyncLLMClient
from scheduler.config import configure_jobs as configure_scheduler_jobs
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # Добавлено для явности
from sheets.sheets_manager import AsyncSheetsManager
from utils.logging_config import setup_logging
from core.exceptions import BotError
from utils.sentry_integration import setup_sentry
from prometheus_client import start_http_server  # For metrics

# from core.metrics import APP_INFO  # For app version metric - УДАЛЕНО
from texts import DEFAULT_ERROR_TEXT  # Import new text

# ---------------------------------------------------------------------------
# PTB >=20.9 includes a fix for the __polling_cleanup_cb slot, no extra patch needed.
# ---------------------------------------------------------------------------

# ---------------------------------
# Logging setup
# ---------------------------------
logger = setup_logging(logging_cfg.level)


async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler for the Telegram bot application.

    Logs the error and attempts to send a user-friendly message to the chat
    where the error occurred.

    Args:
        update: The Telegram Update that caused the error.
        context: The PTB context, containing the error in `context.error`.
    """
    error = context.error
    logger.error("Error processing update=%s", update, exc_info=error)  # Translated log

    # Friendly message to the user
    if isinstance(error, BotError):
        user_msg = error.user_friendly
    else:
        user_msg = DEFAULT_ERROR_TEXT  # Use constant

    if update and update.effective_chat:
        try:
            await context.bot.send_message(update.effective_chat.id, user_msg)
        except Exception:  # noqa: BLE001
            pass


async def main_async() -> None:
    """Асинхронная основная функция для запуска бота."""
    if telegram.sentry_dsn:
        setup_sentry()
        logger.info(
            "Sentry SDK инициализирован (или попытка инициализации была сделана)."
        )
    else:
        logger.warning(
            "Sentry DSN не найден в конфигурации. Sentry SDK не инициализирован."
        )

    setup_logging(logging_cfg.level)

    logger.info(f"Запуск Target Assistant Bot v{telegram.app_version}")
    logger.debug(f"Конфигурация Google Sheets: {google}")
    logger.debug(f"Конфигурация LLM: {llm_config}")
    logger.debug(f"Конфигурация Scheduler: {global_scheduler_config}")
    logger.debug(f"Конфигурация Rate Limiter: {ratelimiter_cfg}")

    if not telegram.token:
        logger.critical("Токен Telegram не найден. Завершение работы.")
        return

    sheets_manager: AsyncStorageInterface = AsyncSheetsManager(
        config_google=google, config_cache=cache_config
    )
    logger.info("AsyncSheetsManager инициализирован.")

    llm_client: AsyncLLMInterface = AsyncLLMClient(config_llm=llm_config)
    logger.info("AsyncLLMClient инициализирован.")

    goal_manager = GoalManager(storage=sheets_manager, llm=llm_client)
    logger.info("GoalManager инициализирован.")

    application = Application.builder().token(telegram.token).build()
    logger.info("Telegram Application создан.")

    application.goal_manager = goal_manager  # type: ignore[attr-defined]
    logger.debug("GoalManager добавлен в контекст приложения.")

    # Используем явные импортированные функции/фабрики
    # Для common_handlers теперь нужна ссылка на scheduler, которая создается позже.
    # Поэтому add_common_handlers будет вызван после инициализации scheduler.
    
    # goal_setting_handlers и task_management_handlers
    application.add_handler(build_setgoal_conv(goal_manager))
    
    today_h, status_h, motivation_h, check_c = build_task_handlers(goal_manager)
    application.add_handler(CommandHandler("today", today_h))
    application.add_handler(CommandHandler("status", status_h))
    application.add_handler(CommandHandler("motivation", motivation_h))
    application.add_handler(check_c)
    logger.info("Обработчики goal_setting и task_management зарегистрированы.")

    current_loop = asyncio.get_running_loop()
    logger.info(f"Используется event loop: {current_loop} для APScheduler.")

    scheduler = AsyncIOScheduler(event_loop=current_loop, timezone=global_scheduler_config.timezone)
    logger.info("APScheduler AsyncIOScheduler инициализирован.")

    # Теперь, когда scheduler создан, можно зарегистрировать common_handlers, если они его используют
    # Однако, start_handler из common.py требует и goal_manager, и scheduler
    # и регистрируется внутри add_common_handlers.
    # Значит, add_common_handlers нужно вызывать здесь.
    add_common_handlers(application, goal_manager, scheduler) # Передаем scheduler
    logger.info("Общие обработчики команд зарегистрированы.")

    # Регистрируем error_handler, который все еще в main.py
    application.add_error_handler(error_handler)

    try:
        metrics_port = telegram.prometheus_port
        if metrics_port:
            prometheus_server_thread = Thread(
                target=start_http_server, args=(metrics_port,)
            )
            prometheus_server_thread.daemon = (
                True  # Поток завершится при выходе из основного
            )
            prometheus_server_thread.start()
            logger.info(f"Prometheus HTTP-сервер запущен на порту {metrics_port}.")
        else:
            logger.info("Порт для Prometheus не указан, сервер не запущен.")

        async with (
            application
        ):  # Это вызовет application.initialize() и application.shutdown()
            logger.info(
                "PTB Application входит в асинхронный контекст (вызовется initialize)."
            )

            await application.start()
            logger.info("Polling PTB Application запущен.")

            if application.bot:
                configure_scheduler_jobs(scheduler, goal_manager, application.bot)
                logger.info("Задачи планировщика сконфигурированы.")
                scheduler.start()

            await application.updater.start_polling()  # Начинаем опрос обновлений
            logger.info("Updater PTB Application начал опрос обновлений.")

            if application.updater and application.updater.running:
                while application.updater.running:  # Проверяем флаг напрямую
                    await asyncio.sleep(1)
                logger.info("PTB Updater был остановлен.")
            else:
                logger.warning(
                    "PTB Updater не запущен или уже остановлен после старта. Приложение может завершиться."
                )

    except KeyboardInterrupt:
        logger.info("Получен сигнал KeyboardInterrupt. Завершение работы...")
    except Exception as e:
        logger.critical(f"Критическая ошибка в main_async: {e}", exc_info=True)
    finally:
        logger.info("Начало процесса остановки компонентов...")
        if scheduler.running:
            scheduler.shutdown()
            logger.info("Планировщик APScheduler остановлен.")
        logger.info("Target Assistant Bot завершил работу.")


def main():
    """Синхронная точка входа, запускающая асинхронную логику."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
