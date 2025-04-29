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
    BotCommand("check", "✍️ Отметить выполнение"),
    BotCommand("status", "📊 Посмотреть прогресс"),
    BotCommand("motivation", "💡 Мотивационное сообщение"),
    BotCommand("cancel", "⛔ Отменить ввод"),
    BotCommand("reset", "🗑️ Сбросить все данные"),
]


async def _update_commands(force: bool = False):
    """Создаёт или обновляет команды BotFather.

    Если force=False и набор уже совпадает – изменения не выполняются.
    """

    token = telegram.token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ Ошибка: TELEGRAM_BOT_TOKEN не задан в окружении или config.py")
        sys.exit(1)

    bot = Bot(token=token)

    current = await bot.get_my_commands()
    if not force and set((c.command, c.description) for c in current) == set(
        (c.command, c.description) for c in DEFAULT_COMMANDS
    ):
        print("ℹ️ Команды уже актуальны – обновление не требуется.")
        return

    await bot.set_my_commands(DEFAULT_COMMANDS)
    print("✅ Команды успешно обновлены в BotFather!")


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
