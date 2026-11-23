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
