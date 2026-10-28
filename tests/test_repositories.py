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
async def test_add_item(mock_db):
    pool, conn, cur = mock_db
    cur.lastrowid = 42

    item_id = await items.add(user_id=1, title="Купить сыр", item_type="task")

    assert item_id == 42
    cur.execute.assert_called_once()
    args, _ = cur.execute.call_args
    assert "INSERT INTO items" in args[0]
    # Добавляем None в конец, так как due_at по умолчанию None
    assert args[1] == (1, "task", "Купить сыр", None)


@pytest.mark.asyncio
async def test_mark_done(mock_db):
    pool, conn, cur = mock_db
    cur.rowcount = 1

    result = await items.mark_done(user_id=1, item_id=10)

    assert result is True
    cur.execute.assert_called_once()
    args, _ = cur.execute.call_args
    assert "UPDATE items SET status='done'" in args[0]
    assert args[1] == (10, 1)


@pytest.mark.asyncio
async def test_get_ideas(mock_db):
    pool, conn, cur = mock_db
    cur.fetchall.return_value = [{"id": 2, "title": "Идея сыра"}]

    result = await items.get_ideas(user_id=1)

    assert len(result) == 1
    assert result[0]["title"] == "Идея сыра"
