# -*- coding: utf-8 -*-
import logging

import asyncpg

from core.config import settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = settings.database_url
        if not dsn:
            raise RuntimeError(
                "Database URL is not configured. Set NEON_DB_URL (+ NEON_DB_USERNAME/PASSWORD)."
            )
        ssl = "require" if "neon.tech" in dsn else None
        _pool = await asyncpg.create_pool(
            dsn=dsn,
            ssl=ssl,
            min_size=1,
            max_size=10,
            command_timeout=60,
            max_inactive_connection_lifetime=300,
        )
        logger.info("[Database] pool created")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
