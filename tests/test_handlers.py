from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bot.handlers import cmd_add_item, cmd_start


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
