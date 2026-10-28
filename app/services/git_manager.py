"""Управление git-репозиториями (статус, диффы, коммиты)."""

import asyncio
import logging
import os
import subprocess

from app.config import settings
from app.services import gigachat

logger = logging.getLogger(__name__)


def _run_git(path: str, args: list[str]) -> tuple[str, str, int]:
    """Синхронный запуск git-команды (возвращает stdout, stderr, код)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=path,
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "timeout", -1
    except Exception as e:
        return "", str(e), -1


async def is_git_repo(path: str) -> bool:
    """Проверяет, является ли путь git-репозиторием."""
    if not os.path.isdir(path):
        return False
    _, _, code = await asyncio.to_thread(_run_git, path, ["rev-parse", "--is-inside-work-tree"])
    return code == 0


async def get_status(path: str) -> str:
    """Возвращает краткий статус изменений."""
    stdout, _, code = await asyncio.to_thread(_run_git, path, ["status", "--short"])
    if code != 0:
        return "❌ Ошибка чтения статуса"
    return stdout.strip() or "✅ Изменений нет"


async def generate_commit_message(path: str) -> str:
    """Просит GigaChat придумать сообщение по git diff."""
    # Получаем дифф (только для отслеживаемых файлов)
    stdout, _, _ = await asyncio.to_thread(_run_git, path, ["diff", "--stat"])
    diff_text, _, _ = await asyncio.to_thread(_run_git, path, ["diff"])

    if not diff_text.strip():
        return "chore: автосохранение"

    # Ограничиваем размер, чтобы не тратить токены (GigaChat съест 4000 символов)
    prompt = (
        "Напиши одно короткое сообщение для git commit на русском языке (без кавычек). "
        "Оно должно описывать суть изменений, которые показаны в диффе ниже. "
        "Начни с типа (feat, fix, refactor, docs, chore), например: 'feat: добавлен парсинг дат'.\n\n"
        f"{diff_text[:4000]}"
    )

    try:
        # Используем тот же контекст ИИ (или отдельный запрос)
        msg = await gigachat.ask(settings.admin_id, prompt)
        # Чистим от лишних кавычек/префиксов, которые любит ИИ
        msg = msg.strip().strip('"').strip("'").split('\n')[0]
        return msg[:100]  # Ограничиваем длину
    except Exception as e:
        logger.error("Ошибка генерации сообщения: %s", e)
        return "chore: автосохранение изменений"


async def commit(path: str, message: str) -> bool:
    """Делает git add . и git commit -m."""
    # 1. Добавляем
    _, err, code = await asyncio.to_thread(_run_git, path, ["add", "."])
    if code != 0:
        logger.error("Git add error в %s: %s", path, err)
        return False

    # 2. Коммитим
    stdout, err, code = await asyncio.to_thread(_run_git, path, ["commit", "-m", message])
    if code != 0:
        logger.warning("Git commit error в %s: %s", path, err)
        return False

    logger.info("Коммит в %s: %s", path, message)
    return True
