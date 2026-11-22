"""Пользователи бота: регистрация, настройки отчётов."""

from app.services.db import get_pool


async def touch(user_id: int, username: str | None = None, first_name: str | None = None) -> None:
    """Регистрирует пользователя или обновляет его профиль и время активности."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO users (user_id, username, first_name, last_seen_at) "
                "VALUES (%s, %s, %s, NOW()) "
                "ON DUPLICATE KEY UPDATE username=VALUES(username), "
                "first_name=VALUES(first_name), last_seen_at=NOW()",
                (user_id, username, first_name),
            )


async def set_reports(user_id: int, enabled: bool) -> None:
    """Включает или выключает ежедневные отчёты для пользователя."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO users (user_id, reports_enabled, last_seen_at) "
                "VALUES (%s, %s, NOW()) "
                "ON DUPLICATE KEY UPDATE reports_enabled=VALUES(reports_enabled)",
                (user_id, enabled),
            )


async def reports_enabled(user_id: int) -> bool:
    """Включены ли отчёты. Для ещё не зарегистрированных — да (по умолчанию)."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT reports_enabled FROM users WHERE user_id=%s",
                (user_id,),
            )
            row = await cur.fetchone()
            return True if row is None else bool(row[0])


async def get_report_recipients() -> list[int]:
    """ID пользователей, которым нужно отправлять отчёты.

    Берём только тех, у кого включены отчёты и есть хотя бы одна запись:
    иначе новый пользователь получал бы три пустых сообщения в день.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT u.user_id FROM users u "
                "WHERE u.reports_enabled=1 "
                "AND EXISTS (SELECT 1 FROM items i WHERE i.user_id=u.user_id) "
                "ORDER BY u.user_id"
            )
            rows = await cur.fetchall()
            return [int(r[0]) for r in rows]
