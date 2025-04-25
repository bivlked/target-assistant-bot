import os
import asyncio

from telegram import Bot, BotCommand

from config import telegram


async def _update_commands():
    """Асинхронное обновление команд через Telegram Bot API."""
    token = telegram.token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Ошибка: TELEGRAM_BOT_TOKEN не задан в окружении или config.py")
        return

    bot = Bot(token=token)

    commands = [
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

    await bot.set_my_commands(commands)
    print("✅ Команды успешно обновлены в BotFather!")


def main():
    asyncio.run(_update_commands())


if __name__ == "__main__":
    main() 