from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.exceptions import TelegramForbiddenError

from app.services import scheduler as sched


@pytest.fixture
def bot():
    return AsyncMock()


@pytest.mark.asyncio
async def test_report_goes_to_every_user(monkeypatch, bot):
    monkeypatch.setattr(sched.users, "get_report_recipients", AsyncMock(return_value=[1, 2]))
    monkeypatch.setattr(
        sched.reports, "morning_digest", AsyncMock(side_effect=lambda uid: f"отчёт {uid}")
    )

    await sched.send_daily_report(bot, "morning")

    assert bot.send_message.await_count == 2
    bot.send_message.assert_any_await(1, "отчёт 1")
    bot.send_message.assert_any_await(2, "отчёт 2")


@pytest.mark.asyncio
async def test_failure_for_one_user_does_not_stop_others(monkeypatch, bot):
    monkeypatch.setattr(sched.users, "get_report_recipients", AsyncMock(return_value=[1, 2]))
    monkeypatch.setattr(sched.reports, "evening_report", AsyncMock(return_value="итог"))
    bot.send_message.side_effect = [RuntimeError("сеть"), None]

    await sched.send_daily_report(bot, "evening")

    assert bot.send_message.await_count == 2
    bot.send_message.assert_any_await(2, "итог")


@pytest.mark.asyncio
async def test_blocked_user_turns_reports_off(monkeypatch, bot):
    monkeypatch.setattr(sched.users, "get_report_recipients", AsyncMock(return_value=[1, 2]))
    monkeypatch.setattr(sched.reports, "midday_report", AsyncMock(return_value="отчёт"))
    set_reports = AsyncMock()
    monkeypatch.setattr(sched.users, "set_reports", set_reports)
    bot.send_message.side_effect = [
        TelegramForbiddenError(method=MagicMock(), message="bot was blocked"),
        None,
    ]

    await sched.send_daily_report(bot, "midday")

    set_reports.assert_awaited_once_with(1, False)
    bot.send_message.assert_any_await(2, "отчёт")


@pytest.mark.asyncio
async def test_no_recipients_no_sending(monkeypatch, bot):
    monkeypatch.setattr(sched.users, "get_report_recipients", AsyncMock(return_value=[]))

    await sched.send_daily_report(bot, "morning")

    bot.send_message.assert_not_awaited()


# --- НАПОМИНАНИЯ ---

def _fake_job_store():
    """MagicMock, имитирующий работу AsyncIOScheduler для reminder-функций."""
    jobs = {}

    def add_job(func, trigger, args=None, id=None):
        jobs[id] = {"func": func, "args": args}

    def get_job(job_id):
        return jobs.get(job_id)

    def remove_job(job_id):
        del jobs[job_id]

    def get_jobs():
        return [type("J", (), {"id": k})() for k in jobs]

    store = MagicMock()
    store.add_job.side_effect = add_job
    store.get_job.side_effect = get_job
    store.remove_job.side_effect = remove_job
    store.get_jobs.side_effect = get_jobs
    store.jobs = jobs  # реальный dict, чтобы тесты видели то, что записал scheduler
    return store


@pytest.mark.asyncio
async def test_schedule_item_reminder_adds_job(monkeypatch):
    store = _fake_job_store()
    monkeypatch.setattr(sched, "scheduler", store)
    monkeypatch.setattr(
        sched.items, "get_todo_by_id",
        AsyncMock(return_value={"id": 10, "title": "Пить кофе", "remind_at": "2026-01-01 08:30"}),
    )

    await sched.schedule_item_reminder(5, 10)

    assert "reminder:5:10" in store.jobs
    job = store.jobs["reminder:5:10"]
    assert job["args"] == [5, 10]


@pytest.mark.asyncio
async def test_schedule_item_reminder_skips_when_no_remind_at(monkeypatch):
    store = _fake_job_store()
    monkeypatch.setattr(sched, "scheduler", store)
    monkeypatch.setattr(
        sched.items, "get_todo_by_id",
        AsyncMock(return_value={"id": 10, "title": "x", "remind_at": None}),
    )

    await sched.schedule_item_reminder(5, 10)

    assert not store.jobs


@pytest.mark.asyncio
async def test_cancel_reminder_removes_job(monkeypatch):
    store = _fake_job_store()
    store.jobs["reminder:5:10"] = {"func": None}
    monkeypatch.setattr(sched, "scheduler", store)

    sched.cancel_reminder(5, 10)

    assert "reminder:5:10" not in store.jobs


@pytest.mark.asyncio
async def test_reload_reminders(monkeypatch):
    store = _fake_job_store()
    monkeypatch.setattr(sched, "scheduler", store)
    monkeypatch.setattr(
        sched.items, "get_pending_reminders",
        AsyncMock(return_value=[
            {"id": 1, "user_id": 5, "remind_at": "2026-01-01 08:30", "title": "А"},
            {"id": 2, "user_id": 6, "remind_at": "2026-01-01 09:00", "title": "Б"},
        ]),
    )

    await sched.reload_reminders()

    assert set(store.jobs) == {"reminder:5:1", "reminder:6:2"}


@pytest.mark.asyncio
async def test_send_reminder_sends_when_task_active(monkeypatch, bot):
    monkeypatch.setattr(sched, "_bot", bot)
    monkeypatch.setattr(
        sched.items, "find_by_id",
        AsyncMock(return_value={"id": 10, "title": "Встретиться"}),
    )

    await sched.send_reminder(5, 10)

    bot.send_message.assert_awaited_once()
    args = bot.send_message.call_args[0]
    assert args[0] == 5
    assert "Встретиться" in args[1]


@pytest.mark.asyncio
async def test_send_reminder_skips_done_task(monkeypatch, bot):
    monkeypatch.setattr(sched, "_bot", bot)
    monkeypatch.setattr(sched.items, "find_by_id", AsyncMock(return_value=None))

    await sched.send_reminder(5, 10)

    bot.send_message.assert_not_awaited()
