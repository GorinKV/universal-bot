"""Клиент GigaChat: OAuth, чат, история, function calling с фолбэком."""

import asyncio
import json
import logging
from datetime import datetime

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

def get_system_prompt() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return (
        f"Сегодняшняя дата: {today}.\n"
        "Ты универсальный помощник с доступом к инструментам.\n"
        "ВНИМАНИЕ! Если пользователь просит выполнить действие с задачами, ОБЯЗАТЕЛЬНО вызывай соответствующий инструмент.\n"
        "Правила:\n"
        "- Просит создать задачу -> create_task. Если указано время ('завтра', 'до пятницы'), ОБЯЗАТЕЛЬНО вычисли дату в формате YYYY-MM-DD и передай в due_date.\n"
        "- Просит сохранить идею -> create_idea.\n"
        "- Просит показать задачи/список дел -> get_tasks.\n"
        "- Просит показать идеи -> get_ideas.\n"
        "- 'выполнил', 'сделал' -> mark_task_done.\n"
        "- 'удали' -> delete_task.\n"
        "- 'верни' -> undo_task.\n"
        "Не задавай лишних вопросов, просто вызывай инструмент."
    )

MAX_USER_LEN = 2000
MAX_AI_LEN = 4000
MAX_HISTORY = 20

_client: GigaChat | None = None
_histories: dict[int, list[Messages]] = {}


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
            Messages(role=MessagesRole.SYSTEM, content=get_system_prompt())
        ]
    return _histories[user_id]


# --- Инструменты (описание функций) ---

CREATE_TASK_FUNCTION = Function(
    name="create_task",
    description="Создать новую задачу",
    parameters=FunctionParameters(
        type="object",
        properties={
            "title": {"type": "string", "description": "Текст задачи"},
            "due_date": {"type": "string", "description": "Срок выполнения в формате YYYY-MM-DD (опционально)"},
        },
        required=["title"],
    ),
)

CREATE_IDEA_FUNCTION = Function(
    name="create_idea",
    description="Сохранить идею",
    parameters=FunctionParameters(
        type="object",
        properties={"title": {"type": "string", "description": "Текст идеи"}},
        required=["title"],
    ),
)

GET_TASKS_FUNCTION = Function(
    name="get_tasks",
    description="Показать список задач",
    parameters=FunctionParameters(
        type="object",
        properties={
            "filter": {
                "type": "string",
                "enum": ["active", "completed", "all"],
                "description": "active (активные), completed (выполненные), all (все)",
            }
        },
    ),
)

GET_IDEAS_FUNCTION = Function(
    name="get_ideas",
    description="Показать список идей",
    parameters=FunctionParameters(type="object", properties={}),
)

MARK_DONE_FUNCTION = Function(
    name="mark_task_done",
    description="Отметить задачу выполненной",
    parameters=FunctionParameters(
        type="object",
        properties={
            "position": {"type": "integer", "description": "Позиция в списке"},
            "title": {"type": "string", "description": "Название задачи"},
        },
    ),
)

DELETE_FUNCTION = Function(
    name="delete_task",
    description="Удалить задачу",
    parameters=FunctionParameters(
        type="object",
        properties={
            "position": {"type": "integer", "description": "Позиция в списке"},
            "title": {"type": "string", "description": "Название задачи"},
        },
    ),
)

UNDO_FUNCTION = Function(
    name="undo_task",
    description="Вернуть задачу из выполненных",
    parameters=FunctionParameters(
        type="object",
        properties={"position": {"type": "integer", "description": "Позиция в выполненных"}},
        required=["position"],
    ),
)

CLEAR_FUNCTION = Function(
    name="clear_tasks",
    description="Удалить все задачи",
    parameters=FunctionParameters(type="object", properties={}),
)

FUNCTIONS = [
    CREATE_TASK_FUNCTION,
    CREATE_IDEA_FUNCTION,
    GET_TASKS_FUNCTION,
    GET_IDEAS_FUNCTION,
    MARK_DONE_FUNCTION,
    DELETE_FUNCTION,
    UNDO_FUNCTION,
    CLEAR_FUNCTION,
]


async def _execute_function(user_id: int, name: str, arguments: dict) -> dict:
    try:
        if name == "create_task":
            title = arguments.get("title", "").strip()
            due_date = arguments.get("due_date")
            if not title:
                return {"status": "error", "message": "Пустой текст"}
            item_id = await items.add(user_id, title, item_type="task", due_at=due_date)
            return {"status": "success", "id": item_id, "title": title, "due": due_date}

        if name == "create_idea":
            title = arguments.get("title", "").strip()
            if not title:
                return {"status": "error", "message": "Пустой текст"}
            item_id = await items.add(user_id, title, item_type="idea")
            return {"status": "success", "id": item_id, "title": title}

        if name == "get_tasks":
            filter_type = arguments.get("filter", "active")
            if filter_type == "completed":
                data = await items.get_list(user_id, 'done')
                lines = [f"~[{i['id']}] {i['title']}~ ({i['dt']})" for i in data]
            elif filter_type == "all":
                todo = await items.get_list(user_id, 'todo')
                done = await items.get_list(user_id, 'done')
                lines = [f"[{i['id']}] {i['title']}" for i in todo] + [
                    f"~[{i['id']}] {i['title']}~ ({i['dt']})" for i in done
                ]
            else:
                data = await items.get_list(user_id, 'todo')
                lines = [
                    f"[{i['id']}] {i['title']}" + (f" (до {i['due']})" if i.get('due') else "")
                    for i in data
                ]
            if not lines:
                return {"status": "success", "result": "Список пуст."}
            return {"status": "success", "result": "\n".join(lines)}

        if name == "get_ideas":
            ideas = await items.get_ideas(user_id)
            if not ideas:
                return {"status": "success", "result": "Идей нет."}
            lines = [f"[{i['id']}] {i['title']}" for i in ideas]
            return {"status": "success", "result": "\n".join(lines)}

        if name in ("mark_task_done", "delete_task"):
            position = arguments.get("position")
            title = arguments.get("title")
            item = None
            if position:
                item = await items.find_by_position(user_id, int(position))
            elif title:
                item = await items.find_by_title(user_id, str(title))
            if not item:
                return {"status": "error", "message": "Задача не найдена"}

            if name == "mark_task_done":
                await items.mark_done(user_id, item["id"])
                return {"status": "success", "title": item["title"]}
            else:
                await items.delete(user_id, item["id"])
                return {"status": "success", "title": item["title"]}

        if name == "undo_task":
            position = arguments.get("position")
            if not position:
                return {"status": "error", "message": "Не указана позиция"}
            ok = await items.undo_by_position(user_id, int(position))
            if not ok:
                return {"status": "error", "message": "Задача не найдена"}
            return {"status": "success"}

        if name == "clear_tasks":
            count = await items.clear_all(user_id)
            return {"status": "success", "count": count}

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

        response = await asyncio.to_thread(
            client.chat,
            Chat(
                messages=history,
                functions=FUNCTIONS,
                function_call="auto",
                temperature=0.3,
                max_tokens=1024,
            ),
        )

        choice = response.choices[0]
        message = choice.message

        if choice.finish_reason == "function_call" and message.function_call:
            name = message.function_call.name
            raw_args = message.function_call.arguments

            if isinstance(raw_args, str):
                try:
                    arguments = json.loads(raw_args)
                except json.JSONDecodeError:
                    arguments = {}
            else:
                arguments = raw_args or {}

            logger.info("GigaChat вызвал функцию %s с аргументами %s", name, arguments)
            result = await _execute_function(user_id, name, arguments)

            history.append(message)
            history.append(
                Messages(
                    role=MessagesRole.FUNCTION,
                    content=json.dumps(result, ensure_ascii=False),
                    name=name,
                )
            )

            response = await asyncio.to_thread(
                client.chat,
                Chat(messages=history, temperature=0.3, max_tokens=1024),
            )
            answer = response.choices[0].message.content or ""
        else:
            answer = message.content or ""

        if not answer:
            answer = "Готово."

    except Exception as e:
        error_str = str(e)

        # Фолбэк: если ошибка 422 (некорректная история вызовов функций)
        if "422" in error_str and ("function" in error_str or "assistant" in error_str):
            logger.warning("История функций повреждена (422). Сбрасываю историю и повторяю запрос.")
            reset_history(user_id)
            # Повторная попытка с чистого листа, без функций
            try:
                client = _get_client()
                new_history = [
                    Messages(role=MessagesRole.SYSTEM, content=get_system_prompt()),
                    Messages(role=MessagesRole.USER, content=text),
                ]
                response = await asyncio.to_thread(
                    client.chat,
                    Chat(messages=new_history, temperature=0.3, max_tokens=1024),
                )
                answer = response.choices[0].message.content or "Готово."
                # Сохраняем новую историю
                _histories[user_id] = new_history + [
                    Messages(role=MessagesRole.ASSISTANT, content=answer)
                ]
                return answer[:MAX_AI_LEN]
            except Exception as retry_error:
                logger.exception("Повторная попытка также не удалась")
                raise RuntimeError(f"GigaChat (после сброса истории): {retry_error}") from retry_error

        logger.exception("GigaChat: ошибка запроса")
        history.pop()  # откатить сообщение пользователя
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
                messages=[Messages(role=MessagesRole.USER, content="ок")],
                max_tokens=10,
            ),
        )
        _ = response.choices[0].message.content
        return True, "ok"
    except Exception as e:
        return False, str(e)[:120]
