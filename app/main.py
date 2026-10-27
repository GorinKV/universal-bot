"""Точка входа: aiogram 3, long polling."""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from app.bot.handlers import router
from app.config import settings
from app.services.health import log_startup_info

logger = logging.getLogger(__name__)


async def set_commands(bot: Bot) -> None:
    """Регистрирует команды в меню Telegram."""
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Начать работу"),
            BotCommand(command="help", description="Справка"),
            BotCommand(command="chatid", description="Мой chat_id"),
            BotCommand(command="health", description="Проверка компонентов"),
        ]
    )


async def main() -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    log_startup_info()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    await set_commands(bot)
    bot.delete_webhook(drop_pending_updates=True)
    logger.info("Бот запущен, начинаю long polling")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Остановлено")

