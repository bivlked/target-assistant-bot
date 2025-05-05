import asyncio
import os
import sys
import argparse
from typing import List

from telegram import Bot, BotCommand

from config import telegram


DEFAULT_COMMANDS: List[BotCommand] = [
    BotCommand("start", "🚀 Начать работу с ботом"),
    BotCommand("help", "ℹ️ Справка по доступным командам"),
    BotCommand("setgoal", "🎯 Установить новую цель"),
    BotCommand("today", "📅 Задача на сегодня"),
    BotCommand("today_async", "⚡ Асинхронная задача на сегодня (тест)"),
    BotCommand("check", "✍️ Отметить выполнение задачи"),
    BotCommand("status", "📊 Посмотреть прогресс в достижении цели"),
    BotCommand("motivation", "💡 Мотивирующее сообщение"),
    BotCommand("cancel", "⛔ Отменить текущую операцию"),
    BotCommand("reset", "🗑️ Сбросить все цели (удалить данные полностью)"),
]

# --- Описание бота (Bot API >= 6.1) ---
SHORT_DESCRIPTION = "✅ Личный ассистент: ставьте цели и достигайте их!"

FULL_DESCRIPTION = (
    "🎯 Target Assistant Bot помогает сформулировать цель, разбить её на ежедневные задачи и "
    "отслеживать прогресс в Google Sheets.\n\n"
    "Основные команды:\n"
    "• /setgoal — постановка цели с поддержкой AI\n"
    "• /today — задача на сегодня\n"
    "• /today_async — асинхронная задача (тест)\n"
    "• /check — отметить выполнение задачи\n"
    "• /status — прогресс в достижении цели\n"
    "• /motivation — мотивирующее сообщение\n"
    "• /cancel — отменить текущую операцию\n"
    "• /reset — сбросить все цели и данные\n\n"
    "Давайте достигать целей вместе!"
)


async def _update_commands(force: bool = False):
    """Создаёт или обновляет команды BotFather.

    Если force=False и набор уже совпадает – изменения не выполняются.
    """

    token = telegram.token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ Ошибка: TELEGRAM_BOT_TOKEN не задан в окружении или config.py")
        sys.exit(1)

    bot = Bot(token=token)

    # --- Обновляем команды ---
    current_cmds = await bot.get_my_commands()
    if force or set((c.command, c.description) for c in current_cmds) != set(
        (c.command, c.description) for c in DEFAULT_COMMANDS
    ):
        await bot.set_my_commands(DEFAULT_COMMANDS)
        print("✅ Команды обновлены.")
    else:
        print("ℹ️ Команды уже актуальны – пропущено.")

    # --- Обновляем короткое описание ---
    short_desc = await bot.get_my_short_description()
    if force or (short_desc.short_description or "") != SHORT_DESCRIPTION:
        await bot.set_my_short_description(short_description=SHORT_DESCRIPTION)
        print("✅ SHORT_DESCRIPTION обновлено.")

    # --- Обновляем полное описание ---
    full_desc = await bot.get_my_description()
    if force or (full_desc.description or "") != FULL_DESCRIPTION:
        await bot.set_my_description(description=FULL_DESCRIPTION)
        print("✅ FULL_DESCRIPTION обновлено.")


def main():
    parser = argparse.ArgumentParser(
        description="Настройка стандартных команд BotFather."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Принудительно перезаписать даже если команды уже совпадают.",
    )
    args = parser.parse_args()

    asyncio.run(_update_commands(force=args.force))


if __name__ == "__main__":
    main()
