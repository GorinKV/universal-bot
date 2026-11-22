"""Регистрация пользователей на каждом входящем апдейте."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from app.repositories import users

logger = logging.getLogger(__name__)


class UserMiddleware(BaseMiddleware):
    """Обновляет профиль пользователя и время последней активности.

    Ошибка записи в БД не должна ломать обработку команды, поэтому исключение
    только логируется.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if isinstance(user, User) and not user.is_bot:
            try:
                await users.touch(user.id, user.username, user.first_name)
            except Exception as e:
                logger.warning("Не удалось сохранить пользователя %s: %s", user.id, e)
        return await handler(event, data)
