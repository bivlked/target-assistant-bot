from __future__ import annotations  # Should be the very first line

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file at the very beginning

import asyncio

from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.ext import ContextTypes

from config import telegram, logging_cfg, prometheus_cfg
from core.goal_manager import GoalManager

# from llm.client import LLMClient # Not used directly, GoalManager uses AsyncLLMClient
from llm.async_client import AsyncLLMClient
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
from prometheus_client import start_http_server  # For metrics
from core.metrics import APP_INFO  # For app version metric
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


async def main_async():
    """Main async entry point for the Telegram bot application."""
    # Initialize Sentry (if configured)
    setup_sentry()

    # Token check
    if not telegram.token:
        logger.error("TELEGRAM_BOT_TOKEN is not set")  # Translated log
        return

    # Initialize dependencies
    sheets_client = AsyncSheetsManager()
    llm_client = AsyncLLMClient()
    goal_manager = GoalManager(storage=sheets_client, llm=llm_client)

    # Create Telegram Application
    application = Application.builder().token(telegram.token).build()

    # Create scheduler with current event loop
    loop = asyncio.get_running_loop()
    scheduler = Scheduler(goal_manager, event_loop=loop)

    # Register handlers
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("cancel", cancel_handler))
    application.add_handler(CommandHandler("reset", reset_handler(goal_manager)))

    # /start depends on goal_manager and scheduler
    application.add_handler(
        CommandHandler("start", start_handler(goal_manager, scheduler))
    )

    # /setgoal conversation
    application.add_handler(build_setgoal_conv(goal_manager))

    # /today, /status, /motivation, /check
    today_handler, status_handler, motivation_handler, check_conv = build_task_handlers(
        goal_manager
    )
    application.add_handler(CommandHandler("today", today_handler))
    application.add_handler(CommandHandler("status", status_handler))
    application.add_handler(CommandHandler("motivation", motivation_handler))
    application.add_handler(check_conv)

    # Unknown commands - filter all except known ones
    known_cmds = (
        r"^(\/)(start|help|setgoal|today|motivation|status|check|cancel|reset)(?:@\w+)?"
    )
    unknown_cmd_filter = filters.Command() & ~filters.Regex(known_cmds)
    application.add_handler(MessageHandler(unknown_cmd_filter, unknown_handler()))

    # Set error handler
    application.add_error_handler(error_handler)

    # Initialize application
    await application.initialize()

    # Start Prometheus metrics server
    start_http_server(prometheus_cfg.port)
    logger.info(f"Prometheus metrics available on port {prometheus_cfg.port} /metrics")

    # Start scheduler AFTER application is initialized
    scheduler.start()

    # Get version from pyproject.toml
    try:
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            import toml as tomllib  # type: ignore  # fallback for older Python
        with open("pyproject.toml", "rb" if hasattr(tomllib, "load") else "r") as f:
            pyproject = tomllib.load(f)
            version = pyproject.get("project", {}).get("version", "unknown")
    except Exception:
        version = "1.0.0"  # Fallback version

    logger.info(f"Bot started v{version}")
    APP_INFO.labels(version=version).set(1)  # Set version metric

    # Start the bot
    await application.start()
    await application.updater.start_polling()

    # Keep the application running
    await asyncio.Event().wait()


def main():
    """Main entry point that creates and runs the event loop."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")


if __name__ == "__main__":
    main()
