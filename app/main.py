"""Точка входа: aiogram 3, long polling, планировщик."""

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
from app.services.db import init_db, close_db
from app.services.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)

async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="tasks", description="Задачи"),
        BotCommand(command="ideas", description="Идеи"),
        BotCommand(command="help", description="Справка"),
        BotCommand(command="health", description="Проверка"),
    ])

async def main() -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    log_startup_info()

    await init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    
    # Запускаем планировщик
    start_scheduler(bot)

    dp = Dispatcher()
    dp.include_router(router)

    await set_commands(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Бот запущен, начинаю long polling")

    try:
        await dp.start_polling(bot)
    finally:
        stop_scheduler()
        await close_db()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Остановлено")
