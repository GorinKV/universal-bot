"""Клиент GigaChat: OAuth, чат, история, function calling (создание задач/идей)."""

import asyncio
import json
import logging

from gigachat import GigaChat
from gigachat.models import (
    Chat,
    Function,
    FunctionParameters,
    Messages,
    MessagesRole,
)

from app.config import settings
from app.repositories import items

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты дружелюбный помощник. Отвечай кратко, по делу, на русском языке.\n"
    "Если пользователь просит создать задачу, обязательно используй инструмент create_task.\n"
    "Если пользователь просит сохранить идею, используй create_idea.\n"
    "Не отвечай текстом, если нужно просто создать задачу или идею — вызывай инструмент."
)

MAX_USER_LEN = 2000
MAX_AI_LEN = 4000
MAX_HISTORY = 20

_client: GigaChat | None = None
_histories: dict[int, list[Messages]] = {}

# Описание функций для GigaChat
CREATE_TASK_FUNCTION = Function(
    name="create_task",
    description="Создать новую задачу в списке дел пользователя",
    parameters=FunctionParameters(
        type="object",
        properties={
            "title": {
                "type": "string",
                "description": "Текст задачи (например, 'Купить молоко', 'Сварить сыр')",
            }
        },
        required=["title"],
    ),
)

CREATE_IDEA_FUNCTION = Function(
    name="create_idea",
    description="Сохранить новую идею пользователя",
    parameters=FunctionParameters(
        type="object",
        properties={
            "title": {
                "type": "string",
                "description": "Текст идеи (например, 'Сыр с трюфелем', 'Блог о сыроварении')",
            }
        },
        required=["title"],
    ),
)

FUNCTIONS = [CREATE_TASK_FUNCTION, CREATE_IDEA_FUNCTION]


def _get_client() -> GigaChat:
    global _client
    if _client is None:
        _client = GigaChat(
            base_url="https://api.giga.chat/v1",
            credentials=settings.gigachat_credentials,
            scope=settings.gigachat_scope,
            model=settings.gigachat_model,
            verify_ssl_certs=False,
            timeout=60,
        )
    return _client


def is_configured() -> bool:
    return bool(settings.gigachat_credentials)


def reset_history(user_id: int) -> None:
    _histories.pop(user_id, None)


def _get_history(user_id: int) -> list[Messages]:
    if user_id not in _histories:
        _histories[user_id] = [
            Messages(role=MessagesRole.SYSTEM, content=SYSTEM_PROMPT)
        ]
    return _histories[user_id]


async def _execute_function(user_id: int, name: str, arguments: dict) -> dict:
    """Выполняет функцию, вызванную моделью, и возвращает результат."""
    try:
        if name == "create_task":
            title = arguments.get("title", "").strip()
            if not title:
                return {"status": "error", "message": "Пустой текст задачи"}
            item_id = await items.add(user_id, title, item_type="task")
            return {"status": "success", "id": item_id, "title": title}

        if name == "create_idea":
            title = arguments.get("title", "").strip()
            if not title:
                return {"status": "error", "message": "Пустой текст идеи"}
            item_id = await items.add(user_id, title, item_type="idea")
            return {"status": "success", "id": item_id, "title": title}

        return {"status": "error", "message": f"Неизвестная функция: {name}"}
    except Exception as e:
        logger.exception("Ошибка выполнения функции %s", name)
        return {"status": "error", "message": str(e)}


async def ask(user_id: int, text: str) -> str:
    if not is_configured():
        raise RuntimeError("GigaChat не настроен (проверьте .env)")

    text = text[:MAX_USER_LEN]
    history = _get_history(user_id)
    history.append(Messages(role=MessagesRole.USER, content=text))

    try:
        client = _get_client()

        # Первый запрос — с описанием функций
        response = await asyncio.to_thread(
            client.chat,
            Chat(
                messages=history,
                functions=FUNCTIONS,
                function_call="auto",
                temperature=0.7,
                max_tokens=1024,
            ),
        )

        choice = response.choices[0]
        message = choice.message

        # Если модель решила вызвать функцию
        if choice.finish_reason == "function_call" and message.function_call:
            name = message.function_call.name
            raw_args = message.function_call.arguments

            # ИСПРАВЛЕНИЕ: arguments может быть как строкой, так и словарём
            if isinstance(raw_args, str):
                try:
                    arguments = json.loads(raw_args)
                except json.JSONDecodeError:
                    arguments = {}
            else:
                arguments = raw_args or {}

            logger.info("GigaChat вызвал функцию %s с аргументами %s", name, arguments)

            # Выполняем функцию
            result = await _execute_function(user_id, name, arguments)

            # Добавляем ответ модели с вызовом функции и результат функции в историю
            history.append(message)
            history.append(
                Messages(
                    role=MessagesRole.FUNCTION,
                    content=json.dumps(result, ensure_ascii=False),
                    name=name,
                )
            )

            # Второй запрос — модель формирует текстовый ответ на основе результата
            response = await asyncio.to_thread(
                client.chat,
                Chat(
                    messages=history,
                    temperature=0.7,
                    max_tokens=1024,
                ),
            )
            answer = response.choices[0].message.content or ""
        else:
            answer = message.content or ""

        if not answer:
            answer = "Готово."

    except Exception as e:
        logger.exception("GigaChat: ошибка запроса")
        history.pop()
        raise RuntimeError(f"GigaChat: {e}") from e

    history.append(Messages(role=MessagesRole.ASSISTANT, content=answer))

    if len(history) > MAX_HISTORY + 1:
        _histories[user_id] = [history[0]] + history[-MAX_HISTORY:]

    return answer[:MAX_AI_LEN]


async def ping() -> tuple[bool, str]:
    if not is_configured():
        return False, "не настроен"
    try:
        client = _get_client()
        response = await asyncio.to_thread(
            client.chat,
            Chat(
                messages=[
                    Messages(role=MessagesRole.USER, content="ок"),
                ],
                max_tokens=10,
            ),
        )
        _ = response.choices[0].message.content
        return True, "ok"
    except Exception as e:
        return False, str(e)[:120]
