from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories import items


@pytest.fixture
def mock_db(monkeypatch):
    pool = MagicMock()
    conn = MagicMock()
    cur = AsyncMock()

    acquire_mock = MagicMock()
    acquire_mock.__aenter__ = AsyncMock(return_value=conn)
    acquire_mock.__aexit__ = AsyncMock(return_value=None)
    pool.acquire.return_value = acquire_mock

    cursor_mock = MagicMock()
    cursor_mock.__aenter__ = AsyncMock(return_value=cur)
    cursor_mock.__aexit__ = AsyncMock(return_value=None)
    conn.cursor.return_value = cursor_mock

    monkeypatch.setattr("app.repositories.items.get_pool", lambda: pool)
    return pool, conn, cur


@pytest.mark.asyncio
async def test_add_with_remind_at(mock_db):
    pool, conn, cur = mock_db
    cur.lastrowid = 55

    item_id = await items.add(1, "Встретиться", "task", due_at="2026-01-01 09:00", remind_at="2026-01-01 08:30")

    assert item_id == 55
    sql, args = cur.execute.call_args[0]
    assert "remind_at" in sql
    assert args == (1, "task", "Встретиться", "2026-01-01 09:00", "2026-01-01 08:30")


@pytest.mark.asyncio
async def test_set_remind(mock_db):
    pool, conn, cur = mock_db
    cur.rowcount = 1

    assert await items.set_remind(7, 10, "2026-01-01 08:30:00") is True
    sql, args = cur.execute.call_args[0]
    assert "UPDATE items SET remind_at=%s" in sql
    assert args == ("2026-01-01 08:30:00", 10, 7)

    assert await items.set_remind(7, 10, None) is True
    _, args = cur.execute.call_args[0]
    assert args == (None, 10, 7)


@pytest.mark.asyncio
async def test_set_remind_scoped_to_owner(mock_db):
    pool, conn, cur = mock_db
    cur.rowcount = 0

    assert await items.set_remind(2, 10, "2026-01-01 08:30") is False
    _, args = cur.execute.call_args[0]
    assert "AND user_id=%s" in cur.execute.call_args[0][0]


@pytest.mark.asyncio
async def test_get_todo_by_id_returns_remind_at(mock_db):
    pool, conn, cur = mock_db
    cur.fetchone.return_value = {"id": 10, "title": "Купить молоко", "remind_at": "2026-01-01 08:30:00"}

    row = await items.get_todo_by_id(3, 10)

    assert row["remind_at"] == "2026-01-01 08:30:00"
    sql, args = cur.execute.call_args[0]
    assert "SELECT id, title, remind_at FROM items" in sql
    assert args == (10, 3)


@pytest.mark.asyncio
async def test_get_pending_reminders(mock_db):
    pool, conn, cur = mock_db
    cur.fetchall.return_value = [
        {"id": 1, "user_id": 5, "remind_at": "2026-01-01 08:30", "title": "А"},
        {"id": 2, "user_id": 5, "remind_at": "2026-01-01 09:00", "title": "Б"},
    ]

    rows = await items.get_pending_reminders()

    assert len(rows) == 2
    sql = cur.execute.call_args[0][0]
    assert "status='todo' AND remind_at IS NOT NULL AND remind_at > NOW()" in sql


# --- ПОВТОРЯЮЩИЕСЯ ЗАДАЧИ ---

def test_next_occurrence_daily():
    from datetime import datetime, timedelta
    base = datetime(2026, 3, 1, 9, 30)
    assert items.next_occurrence(base, 'daily') == base + timedelta(days=1)
    assert items.next_occurrence(base, 'daily', 3) == base + timedelta(days=3)


def test_next_occurrence_weekly():
    from datetime import datetime, timedelta
    base = datetime(2026, 3, 1, 9, 30)  # воскресенье
    assert items.next_occurrence(base, 'weekly') == base + timedelta(days=7)
    assert items.next_occurrence(base, 'weekly', 2) == base + timedelta(days=14)


def test_next_occurrence_monthly_clamps_to_days():
    from datetime import datetime
    base = datetime(2026, 1, 31, 10, 0)
    nxt = items.next_occurrence(base, 'monthly')
    assert (nxt.month, nxt.day) == (2, 28)  # февраль 2026: 28 дней

    nxt = items.next_occurrence(datetime(2026, 3, 31, 10, 0), 'monthly')
    assert (nxt.month, nxt.day) == (4, 30)  # апрель: 30 дней


def test_next_occurrence_monthly_steps():
    from datetime import datetime
    base = datetime(2026, 1, 15, 0, 0)
    assert items.next_occurrence(base, 'monthly', 3) == datetime(2026, 4, 15, 0, 0)


def test_next_occurrence_unsupported():
    from datetime import datetime
    assert items.next_occurrence(datetime.now(), 'yearly') is None


@pytest.mark.asyncio
async def test_set_repeat(mock_db):
    pool, conn, cur = mock_db
    cur.rowcount = 1

    assert await items.set_repeat(5, 10, 'monthly', 3) is True
    sql, args = cur.execute.call_args[0]
    assert "SET repeat=%s, repeat_every=%s" in sql
    assert args == ('monthly', 3, 10, 5)

    assert await items.set_repeat(5, 10, 'none') is True
    _, args = cur.execute.call_args[0]
    assert args == ('none', 1, 10, 5)


@pytest.mark.asyncio
async def test_mark_done_non_repeating(mock_db):
    pool, conn, cur = mock_db
    cur.rowcount = 1
    cur.fetchone.return_value = {"id": 10, "title": "x", "repeat": "none", "repeat_every": 1}

    assert await items.mark_done(5, 10) is True
    sql, _ = cur.execute.call_args[0]
    assert "SET status='done', done_at=NOW()" in sql


@pytest.mark.asyncio
async def test_mark_done_repeating_reschedules(mock_db):
    from datetime import datetime, timedelta
    pool, conn, cur = mock_db
    cur.rowcount = 1
    future = datetime.now() + timedelta(days=3)
    cur.fetchone.return_value = {"id": 10, "title": "x", "due_at": future.strftime('%Y-%m-%d %H:%M:%S'), "repeat": "daily", "repeat_every": 1}

    assert await items.mark_done(5, 10) is True
    sql, args = cur.execute.call_args[0]
    assert "SET status='todo', done_at=NULL" in sql
    assert "WHERE id=%s AND user_id=%s AND status='todo'" in sql
    assert args[1] == 10 and args[2] == 5
    new_due = datetime.strptime(args[0], '%Y-%m-%d %H:%M:%S')
    assert new_due.date() == future.date() + timedelta(days=1)


@pytest.mark.asyncio
async def test_mark_done_repeating_overdue_uses_now_base(mock_db):
    from datetime import datetime, timedelta
    pool, conn, cur = mock_db
    cur.rowcount = 1
    past = datetime.now() - timedelta(days=5)
    cur.fetchone.return_value = {"id": 10, "title": "x", "due_at": past.strftime('%Y-%m-%d %H:%M:%S'), "repeat": "weekly", "repeat_every": 1}

    assert await items.mark_done(5, 10) is True
    args = cur.execute.call_args[0][1]
    new_due = datetime.strptime(args[0], '%Y-%m-%d %H:%M:%S')
    assert new_due > datetime.now() + timedelta(days=0)
