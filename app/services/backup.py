"""Модуль резервного копирования БД и кода."""

import asyncio
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime

from aiogram import Bot
from aiogram.types import FSInputFile

from app.config import settings

logger = logging.getLogger(__name__)


def _dump_database(db_path: str):
    """Синхронный дамп базы (запускается в отдельном потоке)."""
    env = os.environ.copy()
    env["MYSQL_PWD"] = settings.db_password

    cmd = [
        "mariadb-dump",
        "-h", settings.db_host,
        "-u", settings.db_user,
        settings.db_name,
    ]
    # Запускаем и пишем вывод сразу в файл
    with open(db_path, "wb") as f:
        subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env, check=True)


def _archive_code(tar_path: str, base_dir: str):
    """Синхронная упаковка кода (запускается в отдельном потоке)."""
    def exclude_filter(tarinfo):
        # Исключаем мусор и секреты
        if any(x in tarinfo.name for x in ['.venv', '.git', '__pycache__', '.env', '.pytest_cache']):
            return None
        return tarinfo

    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(base_dir, arcname="universal-bot", filter=exclude_filter)


async def create_and_send_backup(bot: Bot):
    """Создает бэкап и отправляет админу в Telegram."""
    logger.info("Начинаю создание бэкапа...")
    tmpdir = tempfile.mkdtemp(prefix="bot_backup_")
    date_str = datetime.now().strftime("%Y-%m-%d")

    try:
        db_path = os.path.join(tmpdir, f"db_{date_str}.sql")
        tar_path = os.path.join(tmpdir, f"code_{date_str}.tar.gz")

        # 1. Дамп БД (в отдельном потоке, чтобы не блокировать бота)
        await asyncio.to_thread(_dump_database, db_path)

        # 2. Архив кода (в отдельном потоке)
        # Берем текущую директорию (корень проекта)
        base_dir = os.getcwd()
        await asyncio.to_thread(_archive_code, tar_path, base_dir)

        # 3. Отправка в Telegram
        await bot.send_document(
            settings.admin_id,
            FSInputFile(db_path, filename=f"db_{date_str}.sql"),
            caption=f"📦 <b>Бэкап БД</b> ({date_str})"
        )
        await bot.send_document(
            settings.admin_id,
            FSInputFile(tar_path, filename=f"code_{date_str}.tar.gz"),
            caption=f"📦 <b>Бэкап кода</b> ({date_str})\n<i>(.env исключен)</i>"
        )
        logger.info("Бэкап успешно отправлен")

    except Exception as e:
        logger.exception("Ошибка при создании бэкапа")
        try:
            await bot.send_message(settings.admin_id, f"⚠️ <b>Ошибка бэкапа:</b>\n<code>{e}</code>")
        except Exception:
            pass
    finally:
        # Очистка временных файлов
        shutil.rmtree(tmpdir, ignore_errors=True)
