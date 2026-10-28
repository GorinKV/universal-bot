"""Полный сброс и установка меню бота для всех scope."""

import asyncio

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from app.config import settings


async def main():
    bot = Bot(token=settings.bot_token)

    print("🧹 Очищаем старые команды...")
    # Удаляем глобальные
    await bot.delete_my_commands(scope=BotCommandScopeDefault())
    # Удаляем для чата админа (они часто перекрывают глобальные)
    try:
        await bot.delete_my_commands(scope=BotCommandScopeChat(chat_id=settings.admin_id))
    except Exception:
        pass

    print("📝 Устанавливаем новые команды...")
    commands = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="tasks", description="Активные задачи"),
        BotCommand(command="ideas", description="Список идей"),
        BotCommand(command="git", description="Git-автокоммиты"),
        BotCommand(command="help", description="Справка"),
        BotCommand(command="health", description="Проверка"),
    ]

    # Ставим глобальные
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

    # Ставим для чата админа (чтобы приоритет был 100%)
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=settings.admin_id))
    except Exception as e:
        print(f"⚠️ Не удалось установить для чата: {e}")

    print("✅ Меню обновлено на сервере!")
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
