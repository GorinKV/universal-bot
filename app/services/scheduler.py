"""Планировщик задач (APScheduler)."""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.services import reports

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

async def send_daily_report(bot, report_type: str):
    """Отправляет отчет админу (пока одному пользователю)."""
    try:
        if report_type == "morning":
            text = await reports.morning_digest(settings.admin_id)
        elif report_type == "midday":
            text = await reports.midday_report(settings.admin_id)
        elif report_type == "evening":
            text = await reports.evening_report(settings.admin_id)
        else:
            return

        await bot.send_message(settings.admin_id, text)
        logger.info("Отправлен %s отчет", report_type)
    except Exception as e:
        logger.error("Ошибка отправки отчета %s: %s", report_type, e)

def start_scheduler(bot):
    """Регистрирует задачи по времени."""
    # 07:00 Утренний дайджест
    scheduler.add_job(
        send_daily_report, CronTrigger(hour=7, minute=0),
        args=[bot, "morning"], id="morning_digest"
    )
    # 17:00 Промежуточный отчет
    scheduler.add_job(
        send_daily_report, CronTrigger(hour=17, minute=0),
        args=[bot, "midday"], id="midday_report"
    )
    # 20:40 Вечерний отчет
    scheduler.add_job(
        send_daily_report, CronTrigger(hour=20, minute=40),
        args=[bot, "evening"], id="evening_report"
    )

    scheduler.start()
    logger.info("Планировщик запущен (Europe/Moscow)")

def stop_scheduler():
    scheduler.shutdown()
    logger.info("Планировщик остановлен")
