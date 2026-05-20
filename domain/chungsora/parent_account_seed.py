# -*- coding: utf-8 -*-
"""Neon parent_accounts — DB에 이미 있는 계정에만 기본 데이터(praise/shop) 적용."""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

import asyncpg

logger = logging.getLogger(__name__)


async def apply_defaults_for_db_parents(
    conn: asyncpg.Connection,
    seed_parent_defaults: Callable[[asyncpg.Connection, int], Awaitable[None]],
) -> None:
    """비밀번호는 건드리지 않음. parent_accounts 행마다 praise/shop 기본값만 채움."""
    rows = await conn.fetch("SELECT id, login_id FROM parent_accounts ORDER BY id")
    for row in rows:
        await seed_parent_defaults(conn, int(row["id"]))
        logger.info("[chungsora] defaults checked for login_id=%s", row["login_id"])
