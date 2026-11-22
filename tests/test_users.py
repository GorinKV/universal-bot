from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories import users


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

    monkeypatch.setattr("app.repositories.users.get_pool", lambda: pool)
    return pool, conn, cur


@pytest.mark.asyncio
async def test_touch_registers_user(mock_db):
    pool, conn, cur = mock_db

    await users.touch(42, "kirill", "Кирилл")

    cur.execute.assert_called_once()
    sql, args = cur.execute.call_args[0]
    assert "INSERT INTO users" in sql
    assert "ON DUPLICATE KEY UPDATE" in sql
    assert args == (42, "kirill", "Кирилл")


@pytest.mark.asyncio
async def test_set_reports_upserts_flag(mock_db):
    pool, conn, cur = mock_db

    await users.set_reports(42, False)

    sql, args = cur.execute.call_args[0]
    assert "INSERT INTO users" in sql
    assert "reports_enabled=VALUES(reports_enabled)" in sql
    assert args == (42, False)


@pytest.mark.asyncio
async def test_get_report_recipients(mock_db):
    pool, conn, cur = mock_db
    cur.fetchall.return_value = [(1,), (2,), (3,)]

    result = await users.get_report_recipients()

    assert result == [1, 2, 3]
    sql = cur.execute.call_args[0][0]
    assert "reports_enabled=1" in sql
    assert "EXISTS (SELECT 1 FROM items" in sql


@pytest.mark.asyncio
async def test_reports_enabled_defaults_to_true(mock_db):
    pool, conn, cur = mock_db
    cur.fetchone.return_value = None

    assert await users.reports_enabled(42) is True


@pytest.mark.asyncio
async def test_reports_enabled_respects_flag(mock_db):
    pool, conn, cur = mock_db
    cur.fetchone.return_value = (0,)

    assert await users.reports_enabled(42) is False
