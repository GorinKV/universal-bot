from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bot.handlers import _done_keyboard, cb_clear, cb_done, cmd_add_item, cmd_clear, cmd_start


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
