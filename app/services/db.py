"""Подключение к MariaDB и инициализация схемы."""

import logging
import asyncmy
from app.config import settings

logger = logging.getLogger(__name__)
_pool: asyncmy.Pool | None = None

async def init_db() -> None:
    global _pool
    try:
        _pool = await asyncmy.create_pool(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            db=settings.db_name,
            minsize=1,
            maxsize=5,
            autocommit=True,
        )
        async with _pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS items (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        type ENUM('task', 'idea') DEFAULT 'task',
                        title TEXT NOT NULL,
                        status ENUM('todo', 'done') DEFAULT 'todo',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        done_at DATETIME NULL,
                        INDEX idx_user_status (user_id, status)
                    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
                """)
        logger.info("MariaDB подключена, таблица items готова")
    except Exception as e:
        logger.error("Ошибка подключения к MariaDB: %s", e)
        raise

async def close_db() -> None:
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        logger.info("MariaDB отключена")

def get_pool() -> asyncmy.Pool:
    if _pool is None:
        raise RuntimeError("БД не инициализирована")
    return _pool

async def ping() -> tuple[bool, str]:
    if _pool is None:
        return False, "не подключена"
    try:
        async with _pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                await cur.fetchone()
        return True, "ok"
    except Exception as e:
        return False, str(e)[:80]
