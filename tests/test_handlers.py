from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bot.handlers import (
    _done_keyboard,
    cb_clear,
    cb_done,
    cmd_add_item,
    cmd_clear,
    cmd_remind,
    cmd_reports,
    cmd_start,
)


@pytest.mark.asyncio
async def test_cmd_start():
    # Мокаем объект Message от aiogram
    message = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.first_name = "Константин"

    await cmd_start(message)

    # Проверяем, что бот вызвал answer и в тексте есть имя
    message.answer.assert_called_once()
    args, _ = message.answer.call_args
    assert "Привет, Константин" in args[0]


@pytest.mark.asyncio
@patch("app.bot.handlers.items.add")
async def test_cmd_add_item(mock_add):
    mock_add.return_value = 10

    message = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.id = 1

    command = MagicMock()
    command.command = "task"
    command.args = "Купить молоко"

    await cmd_add_item(message, command)

    mock_add.assert_called_once_with(1, "Купить молоко", "task")
    message.answer.assert_called_once()
    assert "Добавлено (ID: <code>10</code>)" in message.answer.call_args[0][0]


@pytest.mark.asyncio
@patch("app.bot.handlers.items.clear_all")
async def test_cmd_clear_requires_confirmation(mock_clear):
    message = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.id = 1

    await cmd_clear(message)

    # Ничего не удалено до подтверждения
    mock_clear.assert_not_called()
    message.answer.assert_called_once()


@pytest.mark.asyncio
@patch("app.bot.handlers.items.clear_all")
async def test_callback_confirm_clear(mock_clear):
    mock_clear.return_value = 3
    callback = AsyncMock()
    callback.data = "clear:yes"
    callback.message = AsyncMock()
    callback.from_user = MagicMock()
    callback.from_user.id = 1

    await cb_clear(callback)

    mock_clear.assert_called_once_with(1)
    callback.message.edit_text.assert_called_once()
    assert "Удалено" in callback.message.edit_text.call_args[0][0]


def test_done_keyboard_built_from_ids():
    kb = _done_keyboard("[3] Купить корма\n[17] Позвонить маме", set())
    assert kb is not None
    data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert data == ["done:3", "done:17"]


def test_done_keyboard_skips_done_ids():
    kb = _done_keyboard("[3] активная\n~[7] выполненная~", {7})
    assert kb is not None
    data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert data == ["done:3"]


def test_done_keyboard_empty_without_ids():
    assert _done_keyboard("📭 Пусто.", set()) is None


@pytest.mark.asyncio
@patch("app.bot.handlers.items.mark_done")
async def test_callback_done_success(mock_mark):
    mock_mark.return_value = True
    callback = AsyncMock()
    callback.data = "done:7"
    callback.message = AsyncMock()
    callback.from_user = MagicMock()
    callback.from_user.id = 1

    await cb_done(callback)

    mock_mark.assert_called_once_with(1, 7)
    callback.answer.assert_called_once()
    assert callback.answer.call_args[0][0] == "✅ Выполнено!"
    callback.message.edit_reply_markup.assert_called_once()


@pytest.mark.asyncio
@patch("app.bot.handlers.items.mark_done")
async def test_callback_done_not_found(mock_mark):
    mock_mark.return_value = False
    callback = AsyncMock()
    callback.data = "done:99"
    callback.message = AsyncMock()
    callback.from_user = MagicMock()
    callback.from_user.id = 1

    await cb_done(callback)

    mock_mark.assert_called_once_with(1, 99)
    kwargs = callback.answer.call_args[1]
    assert kwargs["show_alert"] is True
    callback.message.edit_reply_markup.assert_not_called()


@pytest.mark.asyncio
@patch("app.bot.handlers.items.mark_done")
async def test_callback_done_bad_data(mock_mark):
    callback = AsyncMock()
    callback.data = "done:abc"

    await cb_done(callback)

    mock_mark.assert_not_called()
    callback.answer.assert_called_once()


@pytest.mark.asyncio
@patch("app.bot.handlers.users.set_reports")
async def test_cmd_reports_enable(mock_set):
    message = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.id = 7
    command = MagicMock()
    command.args = "on"

    await cmd_reports(message, command)

    mock_set.assert_awaited_once_with(7, True)
    assert "включены" in message.answer.call_args[0][0]


@pytest.mark.asyncio
@patch("app.bot.handlers.users.set_reports")
async def test_cmd_reports_disable(mock_set):
    message = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.id = 7
    command = MagicMock()
    command.args = "off"

    await cmd_reports(message, command)

    mock_set.assert_awaited_once_with(7, False)
    assert "выключены" in message.answer.call_args[0][0]


@pytest.mark.asyncio
@patch("app.bot.handlers.users.reports_enabled")
async def test_cmd_reports_status(mock_enabled):
    mock_enabled.return_value = True
    message = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.id = 7
    command = MagicMock()
    command.args = None

    await cmd_reports(message, command)

    assert "включены" in message.answer.call_args[0][0]


# --- /remind ---

@pytest.mark.asyncio
@patch("app.bot.handlers.items.get_todo_by_id")
@patch("app.bot.handlers.items.set_remind")
@patch("app.bot.handlers.sched_mod.schedule_item_reminder")
async def test_cmd_remind_minutes_before_due(mock_sched, mock_set_remind, mock_row):
    from datetime import datetime

    due = (datetime.now() + timedelta(hours=2)).replace(microsecond=0)
    mock_row.return_value = {"id": 10, "title": "Созвон", "due_at": due}
    mock_set_remind.return_value = True
    message = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.id = 5
    command = MagicMock()
    command.args = "10 60"

    await cmd_remind(message, command)

    mock_set_remind.assert_awaited_once()
    args = mock_set_remind.call_args[0]
    assert args[0] == 5 and args[1] == 10
    assert datetime.strptime(args[2], "%Y-%m-%d %H:%M:%S") == due - timedelta(minutes=60)
    mock_sched.assert_awaited_once_with(5, 10)
    assert "Созвон" in message.answer.call_args[0][0]


@pytest.mark.asyncio
@patch("app.bot.handlers.items.get_todo_by_id")
@patch("app.bot.handlers.items.set_remind")
async def test_cmd_remind_no_due_uses_now_plus(mock_set_remind, mock_row):
    from datetime import datetime

    mock_row.return_value = {"id": 10, "title": "Хвост", "due_at": None}
    mock_set_remind.return_value = True
    message = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.id = 5
    command = MagicMock()
    command.args = "10 30"

    await cmd_remind(message, command)

    remind_dt = datetime.strptime(mock_set_remind.call_args[0][2], "%Y-%m-%d %H:%M:%S")
    assert (datetime.now() + timedelta(minutes=20)).replace(second=0, microsecond=0) <= remind_dt


@pytest.mark.asyncio
@patch("app.bot.handlers.items.get_todo_by_id")
@patch("app.bot.handlers.items.set_remind")
@patch("app.bot.handlers.sched_mod.cancel_reminder")
async def test_cmd_remind_off(mock_cancel, mock_set_remind, mock_row):
    mock_row.return_value = {"id": 10, "title": "x", "due_at": None}
    mock_set_remind.return_value = True
    message = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.id = 5
    command = MagicMock()
    command.args = "10 off"

    await cmd_remind(message, command)

    mock_set_remind.assert_awaited_once_with(5, 10, None)
    mock_cancel.assert_called_once_with(5, 10)
    assert "Напоминание сброшено" in message.answer.call_args[0][0]


@pytest.mark.asyncio
@patch("app.bot.handlers.items.get_todo_by_id")
async def test_cmd_remind_invalid_format(mock_row):
    mock_row.return_value = {"id": 10, "title": "x", "due_at": None}
    message = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.id = 5
    command = MagicMock()
    command.args = "10 безумие"

    await cmd_remind(message, command)

    assert "Неверный формат" in message.answer.call_args[0][0]


@pytest.mark.asyncio
@patch("app.bot.handlers.items.get_todo_by_id")
async def test_cmd_remind_unknown_id(mock_row):
    mock_row.return_value = None
    message = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.id = 5
    command = MagicMock()
    command.args = "999 10"

    await cmd_remind(message, command)

    assert "Нет активной задачи" in message.answer.call_args[0][0]


@pytest.mark.asyncio
@patch("app.bot.handlers.items.get_list")
async def test_cmd_remind_lists_tasks_without_args(mock_get_list):
    mock_get_list.return_value = [
        {"id": 1, "title": "А", "due": "01.01", "remind": "01.01 08:00"},
        {"id": 2, "title": "Б", "due": None, "remind": "02.01 07:00"},
    ]
    message = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.id = 5
    command = MagicMock()
    command.args = None

    await cmd_remind(message, command)

    text = message.answer.call_args[0][0]
    assert "[1] А" in text and "напомнить: 01.01 08:00" in text
    assert "[2] Б" in text and "напомнить: 02.01 07:00" in text
