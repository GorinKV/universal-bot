"""Статистика по задачам: что выполнено за неделю."""

from datetime import date

import asyncmy

from app.services.db import get_pool


async def week_stats(user_id: int) -> dict:
    """Статистика за последние 7 дней: создано/выполнено/открыто + рекорд-день."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(asyncmy.cursors.DictCursor) as cur:
            await cur.execute(
                "SELECT COUNT(*) AS total, SUM(status='done') AS done, SUM(status='todo') AS open "
                "FROM items WHERE user_id=%s AND created_at >= NOW() - INTERVAL 7 DAY",
                (user_id,),
            )
            week = await cur.fetchone() or {}
            await cur.execute(
                "SELECT DATE(done_at) AS day, COUNT(*) AS n "
                "FROM items WHERE user_id=%s AND status='done' "
                "AND done_at >= NOW() - INTERVAL 7 DAY GROUP BY day ORDER BY n DESC LIMIT 1",
                (user_id,),
            )
            peak = await cur.fetchone() or {}

    return {
        "total": int(week.get("total") or 0),
        "done": int(week.get("done") or 0),
        "open": int(week.get("open") or 0),
        "peak_day": peak.get("day").strftime("%d.%m") if isinstance(peak.get("day"), date) else peak.get("day"),
        "peak_n": int(peak.get("n") or 0),
    }


def format_stats(stats: dict) -> str:
    """Человекочитаемый блок статистики для отчётов и команды /stats."""
    lines = [
        "<b>📊 Статистика:</b>",
        "",
        f"✅ Выполнено за неделю: <b>{stats['done']}</b> из созданных недели (<i>{stats['total']}</i>)",
        f"🔲 Открыто сейчас: <b>{stats['open']}</b>",
    ]
    if stats["peak_n"] > 0:
        lines.append(f"🏆 Рекорд: <b>{stats['peak_n']} шт.</b> ({stats['peak_day']})")
    return "\n".join(lines)
