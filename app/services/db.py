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
                # Пользователи бота и настройки отчётов
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username VARCHAR(64) NULL,
                        first_name VARCHAR(128) NULL,
                        reports_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
                """)
                # Таблица задач и идей
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS items (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        type ENUM('task', 'idea') DEFAULT 'task',
                        title TEXT NOT NULL,
                        status ENUM('todo', 'done') DEFAULT 'todo',
                        due_at DATETIME NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        done_at DATETIME NULL,
                        remind_at DATETIME NULL,
                        `repeat` ENUM('none', 'daily', 'weekly', 'monthly') NOT NULL DEFAULT 'none',
                        `repeat_every` INT NULL,
                        INDEX idx_user_status (user_id, status)
                    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
                """)
                # Миграция: remind_at для таблиц, созданных до неё (CREATE TABLE снизу не помогает)
                await cur.execute(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_NAME='items' AND COLUMN_NAME='remind_at'"
                )
                if await cur.fetchone() is None:
                    await cur.execute("ALTER TABLE items ADD COLUMN remind_at DATETIME NULL")
                    logger.info("Миграция: добавлен items.remind_at")
                # Повтор задач: 'none' | 'daily' | 'weekly' | 'monthly', repeat_every = N единиц
                await cur.execute(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_NAME='items' AND COLUMN_NAME='repeat'"
                )
                if await cur.fetchone() is None:
                    await cur.execute(
                        "ALTER TABLE items ADD COLUMN `repeat` "
                        "ENUM('none', 'daily', 'weekly', 'monthly') NOT NULL DEFAULT 'none'")
                await cur.execute(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_NAME='items' AND COLUMN_NAME='repeat_every'"
                )
                if await cur.fetchone() is None:
                    await cur.execute("ALTER TABLE items ADD COLUMN `repeat_every` INT NULL")
                # Таблица git-проектов
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS git_projects (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        path VARCHAR(255) NOT NULL,
                        enabled BOOLEAN DEFAULT TRUE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_user (user_id)
                    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
                """)
        logger.info("MariaDB подключена, таблицы users, items и git_projects готовы")
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
