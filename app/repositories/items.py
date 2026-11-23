"""Работа с таблицей items (задачи и идеи)."""

import calendar
from datetime import date, datetime, time, timedelta
from typing import cast

import asyncmy

from app.services.db import get_pool


def next_occurrence(base: datetime | date | None, repeat: str, every: int = 1) -> datetime | None:
    """Следующее вхождение повторяющейся задачи. None — неподдерживаемый repeat."""
    if base is None:
        base = datetime.now()
    elif isinstance(base, date) and not isinstance(base, datetime):
        base = datetime.combine(base, time())
    every = max(1, int(every))
    if repeat == 'daily':
        return base + timedelta(days=every)
    if repeat == 'weekly':
        return base + timedelta(days=7 * every)
    if repeat == 'monthly':
        return _add_months(base, every)
    return None


def _add_months(d: datetime, months: int) -> datetime:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return d.replace(year=y, month=m, day=day)


def _to_dt(value) -> datetime | None:
    """Безопасный парсер DB-даты в наивный datetime."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time())
    if not value:
        return None
    s = str(value).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


async def add(user_id: int, title: str, item_type: str = 'task', due_at: str | None = None,
              remind_at: str | None = None) -> int:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO items (user_id, type, title, due_at, remind_at) VALUES (%s, %s, %s, %s, %s)",
                (user_id, item_type, title, due_at, remind_at)
            )
            return cast(int, cur.lastrowid)


async def get_list(user_id: int, status: str = 'todo') -> list[dict]:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(asyncmy.cursors.DictCursor) as cur:
            if status == 'done':
                await cur.execute(
                    "SELECT id, title, DATE_FORMAT(done_at, '%%d.%%m') as dt FROM items WHERE user_id=%s AND status='done' ORDER BY done_at DESC",
                    (user_id,)
                )
            else:
                await cur.execute(
                    "SELECT id, title, type, DATE_FORMAT(due_at, '%%d.%%m') as due, DATE_FORMAT(created_at, '%%d.%%m') as dt, "
                    "DATE_FORMAT(remind_at, '%%d.%%m %%H:%%M') as remind, `repeat`, `repeat_every` "
                    "FROM items WHERE user_id=%s AND status='todo' ORDER BY id ASC",
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
                f"SELECT id, title, DATE_FORMAT(done_at, '%%d.%%m') as dt FROM items WHERE user_id=%s AND status='done' AND {where} ORDER BY done_at DESC",
                (user_id,)
            )
            return await cur.fetchall()


async def mark_done(user_id: int, item_id: int) -> bool:
    """Выполняет задачу. Если задача повторяющаяся — возвращает её в активные со следующим вхождением."""
    row = await find_by_id(user_id, item_id)
    if row is None:
        return False

    repeat = row.get('repeat') or 'none'
    every = row.get('repeat_every') or 1
    new_due = None
    if repeat in ('daily', 'weekly', 'monthly'):
        base = _to_dt(row.get('due_at')) or datetime.now()
        cand = next_occurrence(base, repeat, every)
        if cand is None or cand <= datetime.now():
            cand = next_occurrence(datetime.now(), repeat, every)
        if cand is not None:
            new_due = cand.strftime('%Y-%m-%d %H:%M:%S')

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if new_due:
                await cur.execute(
                    "UPDATE items SET status='todo', done_at=NULL, due_at=%s "
                    "WHERE id=%s AND user_id=%s AND status='todo'",
                    (new_due, item_id, user_id)
                )
            else:
                await cur.execute(
                    "UPDATE items SET status='done', done_at=NOW() WHERE id=%s AND user_id=%s AND status='todo'",
                    (item_id, user_id)
                )
            return cast(int, cur.rowcount) > 0


async def set_repeat(user_id: int, item_id: int, repeat: str = 'none', every: int | None = None) -> bool:
    """Устанавливает/сбрасывает повтор для активной задачи."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE items SET `repeat`=%s, `repeat_every`=%s "
                "WHERE id=%s AND user_id=%s AND status='todo'",
                (repeat, every if every is not None else 1, item_id, user_id)
            )
            return cast(int, cur.rowcount) > 0


async def undo_by_position(user_id: int, pos: int) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id FROM items WHERE user_id=%s AND status='done' ORDER BY done_at DESC LIMIT 1 OFFSET %s",
                (user_id, pos - 1)
            )
            row = await cur.fetchone()
            if not row:
                return False
            await cur.execute("UPDATE items SET status='todo', done_at=NULL WHERE id=%s", (row[0],))
            return True


async def delete(user_id: int, item_id: int) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM items WHERE id=%s AND user_id=%s", (item_id, user_id))
            return cast(int, cur.rowcount) > 0


async def clear_all(user_id: int) -> int:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM items WHERE user_id=%s", (user_id,))
            return cast(int, cur.rowcount)


async def get_ideas(user_id: int) -> list[dict]:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(asyncmy.cursors.DictCursor) as cur:
            await cur.execute(
                "SELECT id, title, status, DATE_FORMAT(created_at, '%%d.%%m') as dt FROM items WHERE user_id=%s AND type='idea' ORDER BY status ASC, id ASC",
                (user_id,)
            )
            return await cur.fetchall()


async def find_by_id(user_id: int, item_id: int) -> dict | None:
    """Найти активную задачу по её ID (число в скобках)."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(asyncmy.cursors.DictCursor) as cur:
            await cur.execute(
                "SELECT id, title, due_at, `repeat`, `repeat_every` FROM items "
                "WHERE user_id=%s AND status='todo' AND id=%s",
                (user_id, item_id)
            )
            return await cur.fetchone()


async def find_by_position(user_id: int, pos: int) -> dict | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(asyncmy.cursors.DictCursor) as cur:
            await cur.execute(
                "SELECT id, title FROM items WHERE user_id=%s AND status='todo' ORDER BY id ASC LIMIT 1 OFFSET %s",
                (user_id, pos - 1)
            )
            return await cur.fetchone()


async def find_by_title(user_id: int, title: str) -> dict | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(asyncmy.cursors.DictCursor) as cur:
            await cur.execute(
                "SELECT id, title FROM items WHERE user_id=%s AND status='todo' AND title LIKE %s ORDER BY id ASC LIMIT 1",
                (user_id, f"%{title}%")
            )
            return await cur.fetchone()


async def set_remind(user_id: int, item_id: int, remind_at: str | None) -> bool:
    """Устанавливает/сбрасывает время напоминания для активной задачи."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE items SET remind_at=%s WHERE id=%s AND user_id=%s AND status='todo'",
                (remind_at, item_id, user_id)
            )
            return cast(int, cur.rowcount) > 0


async def get_pending_reminders() -> list[dict]:
    """Все напоминания в будущем — для пересоздания таймеров при рестарте."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(asyncmy.cursors.DictCursor) as cur:
            await cur.execute(
                "SELECT id, user_id, remind_at, title FROM items "
                "WHERE status='todo' AND remind_at IS NOT NULL AND remind_at > NOW()"
            )
            return await cur.fetchall()


async def get_todo_by_id(user_id: int, item_id: int) -> dict | None:
    """Сырая строка с remind_at (для планировщика) — без фильтра status."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(asyncmy.cursors.DictCursor) as cur:
            await cur.execute(
                "SELECT id, title, remind_at FROM items WHERE id=%s AND user_id=%s AND status='todo'",
                (item_id, user_id)
            )
            return await cur.fetchone()
