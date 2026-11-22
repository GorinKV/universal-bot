"""Планировщик задач (APScheduler)."""

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.repositories import users
from app.services import reports
from app.services.backup import create_and_send_backup

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)


async def _build_report(user_id: int, report_type: str) -> str | None:
    if report_type == "morning":
        return await reports.morning_digest(user_id)
    if report_type == "midday":
        return await reports.midday_report(user_id)
    if report_type == "evening":
        return await reports.evening_report(user_id)
    return None


async def send_daily_report(bot: Bot, report_type: str) -> None:
    """Отправляет отчёт каждому пользователю с включёнными отчётами."""
    recipients = await users.get_report_recipients()
    if not recipients:
        logger.warning("Нет получателей отчёта %s", report_type)
        return

    sent = 0
    for user_id in recipients:
        try:
            text = await _build_report(user_id, report_type)
            if not text:
                continue
            await bot.send_message(user_id, text)
            sent += 1
        except TelegramForbiddenError:
            # Пользователь заблокировал бота — больше не шлём ему отчёты
            await users.set_reports(user_id, False)
            logger.warning("Пользователь %s заблокировал бота, отчёты выключены", user_id)
        except TelegramRetryAfter as e:
            logger.warning("Flood control для %s: пауза %s с", user_id, e.retry_after)
        except Exception as e:
            # Сбой на одном получателе не должен останавливать рассылку остальным
            logger.error("Ошибка отчёта %s для %s: %s", report_type, user_id, e)

    logger.info("Отчёт %s отправлен %s/%s пользователям", report_type, sent, len(recipients))


def start_scheduler(bot: Bot) -> None:
    """Регистрирует задачи по времени."""
    # 04:00 Бэкап всего
    scheduler.add_job(
        create_and_send_backup, CronTrigger(hour=4, minute=0),
        args=[bot], id="daily_backup"
    )
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


def stop_scheduler() -> None:
    scheduler.shutdown()
    logger.info("Планировщик остановлен")
