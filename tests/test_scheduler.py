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
