"""Планировщик задач (APScheduler)."""

import html
import logging
from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from app.config import settings
from app.repositories import items, users
from app.services import reports
from app.services.backup import create_and_send_backup

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
_bot: Bot | None = None


def _reminder_job_id(user_id: int, item_id: int) -> str:
    return f"reminder:{user_id}:{item_id}"


async def send_reminder(user_id: int, item_id: int) -> None:
    """Отправляет уведомление о напоминании (задача должна быть активной)."""
    if not _bot:
        return
    row = await items.find_by_id(user_id, item_id)
    if not row:
        return
    try:
        await _bot.send_message(
            user_id, f"⏰ Напоминание: <b>{html.escape(row['title'])}</b>"
        )
        logger.info("Напоминание отправлено пользователю %s (задача %s)", user_id, item_id)
    except TelegramForbiddenError:
        logger.warning("Пользователь %s заблокировал бота", user_id)
    except Exception as e:
        logger.error("Ошибка напоминания %s/%s: %s", user_id, item_id, e)


def _add_reminder_job(user_id: int, item_id: int, remind_at) -> None:
    # remind_at — наивная серверная стена (как в DB и datetime.now()):
    # локальный wall-clock процесса и стена базы одной временной зоны.
    # DateTrigger берёт локальную зону процесса, а settings.scheduler_timezone
    # на этом сервере отличается — поэтому сделаем naive run_date.
    if isinstance(remind_at, str):
        remind_at = datetime.strptime(remind_at[:16], "%Y-%m-%d %H:%M")
    elif isinstance(remind_at, datetime) and remind_at.tzinfo is not None:
        remind_at = remind_at.replace(tzinfo=None)
    job_id = _reminder_job_id(user_id, item_id)
    if scheduler.get_job(job_id):
        return
    scheduler.add_job(
        send_reminder, DateTrigger(run_date=remind_at),
        args=[user_id, item_id], id=job_id
    )


async def schedule_item_reminder(user_id: int, item_id: int) -> None:
    """Создаёт/обновляет таймер напоминания для задачи, если remind_at задан."""
    row = await items.get_todo_by_id(user_id, item_id)
    if row and row.get("remind_at"):
        _add_reminder_job(user_id, item_id, row["remind_at"])


def cancel_reminder(user_id: int, item_id: int) -> None:
    """Отменяет таймер напоминания для задачи (задача выполнена/удалена)."""
    job_id = _reminder_job_id(user_id, item_id)
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


async def reload_reminders() -> None:
    """Пересоздаёт таймеры для всех напоминаний, уже хранящихся в БД."""
    for row in await items.get_pending_reminders():
        _add_reminder_job(row["user_id"], row["id"], row["remind_at"])
    logger.info("Созданы таймеры для напоминаний: %s",
                len([j for j in scheduler.get_jobs() if j.id.startswith("reminder:")]))


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


async def start_scheduler(bot: Bot) -> None:
    """Регистрирует задачи по времени (включая напоминания)."""
    global _bot
    _bot = bot
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
    await reload_reminders()
    logger.info("Планировщик запущен (Europe/Moscow)")


def stop_scheduler() -> None:
    scheduler.shutdown()
    logger.info("Планировщик остановлен")
