# -*- coding: utf-8 -*-
"""Neon PostgreSQL — 사용자(가족)별 데이터 격리 마이그레이션."""
from __future__ import annotations

import logging

import asyncpg

logger = logging.getLogger(__name__)


async def migrate_per_user_isolation(conn: asyncpg.Connection) -> None:
    """기존 DB를 parent_account_id 기준 격리 스키마로 승격."""
    default_parent = await conn.fetchval(
        "SELECT id FROM parent_accounts ORDER BY id LIMIT 1"
    )
    if default_parent is None:
        return

    # cleaning_logs: parent_account_id 채우기
    await conn.execute(
        """
        ALTER TABLE cleaning_logs
        ADD COLUMN IF NOT EXISTS parent_account_id INT REFERENCES parent_accounts(id)
        """
    )
    await conn.execute(
        """
        UPDATE cleaning_logs
        SET parent_account_id = $1
        WHERE parent_account_id IS NULL
        """,
        default_parent,
    )

    # log_messages: parent_account_id 추가
    await conn.execute(
        """
        ALTER TABLE log_messages
        ADD COLUMN IF NOT EXISTS parent_account_id INT
        """
    )
    await conn.execute(
        """
        UPDATE log_messages lm
        SET parent_account_id = cl.parent_account_id
        FROM cleaning_logs cl
        WHERE lm.log_date = cl.log_date
          AND lm.parent_account_id IS NULL
        """,
    )
    await conn.execute(
        """
        UPDATE log_messages
        SET parent_account_id = $1
        WHERE parent_account_id IS NULL
        """,
        default_parent,
    )

    # cleaning_logs PK → (parent_account_id, log_date)
    await conn.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'log_messages_log_date_fkey'
          ) THEN
            ALTER TABLE log_messages DROP CONSTRAINT log_messages_log_date_fkey;
          END IF;
        END $$
        """
    )
    await conn.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conrelid = 'cleaning_logs'::regclass
              AND contype = 'p'
              AND array_length(conkey, 1) = 1
          ) THEN
            ALTER TABLE cleaning_logs DROP CONSTRAINT cleaning_logs_pkey;
          END IF;
        END $$
        """
    )
    await conn.execute(
        """
        ALTER TABLE cleaning_logs
        ALTER COLUMN parent_account_id SET NOT NULL
        """
    )
    await conn.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'cleaning_logs_pkey'
              AND conrelid = 'cleaning_logs'::regclass
          ) THEN
            ALTER TABLE cleaning_logs
            ADD PRIMARY KEY (parent_account_id, log_date);
          END IF;
        END $$
        """
    )

    # log_messages FK → composite
    await conn.execute(
        """
        ALTER TABLE log_messages
        ALTER COLUMN parent_account_id SET NOT NULL
        """
    )
    await conn.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'log_messages_log_fkey'
          ) THEN
            ALTER TABLE log_messages
            ADD CONSTRAINT log_messages_log_fkey
            FOREIGN KEY (parent_account_id, log_date)
            REFERENCES cleaning_logs(parent_account_id, log_date)
            ON DELETE CASCADE;
          END IF;
        END $$
        """
    )

    # praise_presets: phrase 전역 UNIQUE → 가족별 UNIQUE
    await conn.execute(
        """
        ALTER TABLE praise_presets
        ADD COLUMN IF NOT EXISTS parent_account_id INT REFERENCES parent_accounts(id)
        """
    )
    await conn.execute(
        """
        UPDATE praise_presets
        SET parent_account_id = $1
        WHERE parent_account_id IS NULL
        """,
        default_parent,
    )
    await conn.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conrelid = 'praise_presets'::regclass
              AND contype = 'u'
              AND conname LIKE '%phrase%'
          ) THEN
            ALTER TABLE praise_presets DROP CONSTRAINT IF EXISTS praise_presets_phrase_key;
          END IF;
        END $$
        """
    )
    await conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS praise_presets_parent_phrase_uidx
        ON praise_presets (parent_account_id, phrase)
        """
    )

    # shop_rewards / daily_quests NULL parent 정리
    for table in ("shop_rewards", "daily_quests"):
        await conn.execute(
            f"""
            ALTER TABLE {table}
            ADD COLUMN IF NOT EXISTS parent_account_id INT REFERENCES parent_accounts(id)
            """
        )
        await conn.execute(
            f"""
            UPDATE {table}
            SET parent_account_id = $1
            WHERE parent_account_id IS NULL
            """,
            default_parent,
        )

    logger.info("[chungsora] per-user schema migration applied")
