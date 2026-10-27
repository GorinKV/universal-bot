"""Работа с таблицей items (задачи и идеи)."""

import asyncmy

from app.services.db import get_pool


async def add(user_id: int, title: str, item_type: str = 'task') -> int:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO items (user_id, type, title) VALUES (%s, %s, %s)",
                (user_id, item_type, title)
            )
            return cur.lastrowid

async def get_list(user_id: int, status: str = 'todo') -> list[dict]:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(asyncmy.cursors.DictCursor) as cur:
            if status == 'done':
                await cur.execute(
                    "SELECT id, title, DATE_FORMAT(done_at, '%%d.%%m') as dt "
                    "FROM items WHERE user_id=%s AND status='done' "
                    "ORDER BY done_at DESC",
                    (user_id,)
                )
            else:
                await cur.execute(
                    "SELECT id, title, type, DATE_FORMAT(created_at, '%%d.%%m') as dt "
                    "FROM items WHERE user_id=%s AND status='todo' "
                    "ORDER BY id ASC",
                    (user_id,)
                )
            return await cur.fetchall()

async def get_by_period(user_id: int, period: str) -> list[dict]:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(asyncmy.cursors.DictCursor) as cur:
            if period == 'month':
                where = "YEAR(done_at)=YEAR(NOW()) AND MONTH(done_at)=MONTH(NOW())"
            elif period == 'year':
                where = "YEAR(done_at)=YEAR(NOW())"
            else:
                where = "DATE(done_at)=CURDATE()"

            await cur.execute(
                f"SELECT id, title, DATE_FORMAT(done_at, '%%d.%%m') as dt "
                f"FROM items WHERE user_id=%s AND status='done' AND {where} "
                f"ORDER BY done_at DESC",
                (user_id,)
            )
            return await cur.fetchall()

async def mark_done(user_id: int, item_id: int) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE items SET status='done', done_at=NOW() "
                "WHERE id=%s AND user_id=%s AND status='todo'",
                (item_id, user_id)
            )
            return cur.rowcount > 0

async def undo_by_position(user_id: int, pos: int) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id FROM items WHERE user_id=%s AND status='done' "
                "ORDER BY done_at DESC LIMIT 1 OFFSET %s",
                (user_id, pos - 1)
            )
            row = await cur.fetchone()
            if not row:
                return False
            item_id = row[0]

            await cur.execute(
                "UPDATE items SET status='todo', done_at=NULL WHERE id=%s",
                (item_id,)
            )
            return True

async def delete(user_id: int, item_id: int) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM items WHERE id=%s AND user_id=%s",
                (item_id, user_id)
            )
            return cur.rowcount > 0

async def clear_all(user_id: int) -> int:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM items WHERE user_id=%s", (user_id,))
            return cur.rowcount

async def get_ideas(user_id: int) -> list[dict]:
    """Все идеи пользователя (и активные, и выполненные)."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(asyncmy.cursors.DictCursor) as cur:
            await cur.execute(
                "SELECT id, title, status, DATE_FORMAT(created_at, '%%d.%%m') as dt "
                "FROM items WHERE user_id=%s AND type='idea' "
                "ORDER BY status ASC, id ASC",
                (user_id,)
            )
            return await cur.fetchall()

async def find_by_position(user_id: int, pos: int) -> dict | None:
    """Найти активную задачу по позиции (1-based)."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(asyncmy.cursors.DictCursor) as cur:
            await cur.execute(
                "SELECT id, title FROM items WHERE user_id=%s AND status='todo' "
                "ORDER BY id ASC LIMIT 1 OFFSET %s",
                (user_id, pos - 1)
            )
            return await cur.fetchone()

async def find_by_title(user_id: int, title: str) -> dict | None:
    """Найти активную задачу по части названия."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(asyncmy.cursors.DictCursor) as cur:
            await cur.execute(
                "SELECT id, title FROM items WHERE user_id=%s AND status='todo' "
                "AND title LIKE %s ORDER BY id ASC LIMIT 1",
                (user_id, f"%{title}%")
            )
            return await cur.fetchone()
