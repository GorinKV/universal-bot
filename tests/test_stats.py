from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import stats


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

    monkeypatch.setattr("app.services.stats.get_pool", lambda: pool)
    return pool, conn, cur


@pytest.mark.asyncio
async def test_week_stats_aggregates(mock_db):
    pool, conn, cur = mock_db
    from datetime import date
    cur.fetchone.side_effect = [
        {"total": 5, "done": 3, "open": 2},
        {"day": date(2026, 11, 20), "n": 3},
    ]

    result = await stats.week_stats(7)

    assert result == {"total": 5, "done": 3, "open": 2, "peak_day": "20.11", "peak_n": 3}
    assert "INTERVAL 7 DAY" in cur.execute.call_args[0][0]
    assert cur.execute.call_count == 2


@pytest.mark.asyncio
async def test_week_stats_empty_peak(mock_db):
    pool, conn, cur = mock_db
    cur.fetchone.side_effect = [
        {"total": 0, "done": None, "open": None},
        {},
    ]

    result = await stats.week_stats(7)

    assert result == {"total": 0, "done": 0, "open": 0, "peak_day": None, "peak_n": 0}


def test_format_stats():
    text = stats.format_stats({"done": 3, "total": 5, "open": 2, "peak_day": "20.11", "peak_n": 3})

    assert "✅ Выполнено за неделю: <b>3</b>" in text
    assert "Открыто сейчас: <b>2</b>" in text
    assert "🏆 Рекорд: <b>3 шт.</b> (20.11)" in text


def test_format_stats_no_peak():
    text = stats.format_stats({"done": 0, "total": 0, "open": 0, "peak_day": None, "peak_n": 0})

    assert "Рекорд" not in text
