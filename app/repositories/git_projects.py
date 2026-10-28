"""Работа с таблицей git_projects."""

import asyncmy

from app.services.db import get_pool


async def add_project(user_id: int, path: str) -> int:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO git_projects (user_id, path) VALUES (%s, %s)",
                (user_id, path)
            )
            return cur.lastrowid


async def get_projects(user_id: int) -> list[dict]:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(asyncmy.cursors.DictCursor) as cur:
            await cur.execute(
                "SELECT id, path, enabled FROM git_projects WHERE user_id=%s ORDER BY id ASC",
                (user_id,)
            )
            return await cur.fetchall()


async def remove_project(user_id: int, project_id: int) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM git_projects WHERE id=%s AND user_id=%s",
                (project_id, user_id)
            )
            return cur.rowcount > 0
