# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from typing import List

import asyncpg

logger = logging.getLogger(__name__)


async def init_cleaning_tables(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS cleaning_memories (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id         TEXT NOT NULL,
                room_id         VARCHAR(100) NOT NULL,
                room_name       VARCHAR(200) NOT NULL,
                cleanliness     INT NOT NULL,
                monsters_cleared TEXT[] NOT NULL DEFAULT '{}',
                duration_sec    INT NOT NULL DEFAULT 0,
                exp_gained      INT NOT NULL DEFAULT 0,
                gold_gained     INT NOT NULL DEFAULT 0,
                created_at      TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    logger.info("[cleaning] tables initialized")


class CleaningRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def save_memory(
        self,
        user_id: str,
        room_id: str,
        room_name: str,
        cleanliness: int,
        monsters_cleared: List[str],
        duration_sec: int,
        exp_gained: int,
        gold_gained: int,
    ) -> dict:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO cleaning_memories
                    (user_id, room_id, room_name, cleanliness,
                     monsters_cleared, duration_sec, exp_gained, gold_gained)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, created_at
                """,
                user_id,
                room_id,
                room_name,
                cleanliness,
                monsters_cleared,
                duration_sec,
                exp_gained,
                gold_gained,
            )
            return {"id": str(row["id"]), "created_at": row["created_at"]}
