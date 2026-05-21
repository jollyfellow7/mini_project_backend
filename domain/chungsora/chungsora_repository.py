# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import logging
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)

BASELINE_SLOT_COUNT = 3
COACH_CHARACTER_IDS = frozenset({"jiu", "seoyeon", "hajun"})


def _normalize_coach_id(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in COACH_CHARACTER_IDS:
        return s
    return "jiu"


def _streak_mult(streak_days: int) -> float:
    if streak_days >= 14:
        return 2.0
    if streak_days >= 7:
        return 1.5
    if streak_days >= 3:
        return 1.25
    return 1.0


def _effective_coach_id(profile: dict) -> str:
    child = _normalize_coach_id(profile.get("child_coach_character_id"))
    if child:
        return child
    return _normalize_coach_id(profile.get("coach_character_id")) or "jiu"


def _normalize_upload_path(url: str | None) -> str | None:
    """DB에 저장된 EC2 절대 URL → /uploads/... 상대 경로 (프론트 BFF 프록시용)."""
    if not url:
        return None
    u = url.strip()
    if not u:
        return None
    if u.startswith(("http://", "https://")):
        from urllib.parse import urlparse

        path = urlparse(u).path
        if path.startswith("/uploads/"):
            return path
    return u


def _pad_baseline_urls(urls: list[Any] | None) -> list[str | None]:
    padded: list[str | None] = [None, None, None]
    if not urls:
        return padded
    for i, item in enumerate(urls):
        if i >= BASELINE_SLOT_COUNT:
            break
        if item is None or item == "":
            continue
        padded[i] = _normalize_upload_path(str(item))
    return padded


def _password_hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


async def init_chungsora_tables(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS parent_accounts (
                id            SERIAL PRIMARY KEY,
                login_id      VARCHAR(64) NOT NULL UNIQUE,
                password_hash VARCHAR(128) NOT NULL,
                display_name  VARCHAR(120) NOT NULL DEFAULT '',
                created_at    TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS cleaning_logs (
                parent_account_id INT NOT NULL REFERENCES parent_accounts(id) ON DELETE CASCADE,
                log_date      DATE NOT NULL,
                score         INT NOT NULL DEFAULT 0,
                streak_days   INT NOT NULL DEFAULT 0,
                before_url    TEXT,
                after_url     TEXT
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS log_messages (
                id         TEXT PRIMARY KEY,
                parent_account_id INT,
                log_date   DATE NOT NULL,
                role       VARCHAR(10) NOT NULL,
                text       TEXT NOT NULL,
                badge      TEXT,
                at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS praise_presets (
                id         SERIAL PRIMARY KEY,
                phrase     VARCHAR(40) NOT NULL,
                parent_account_id INT REFERENCES parent_accounts(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pair_codes (
                code               VARCHAR(8) PRIMARY KEY,
                expires_at         TIMESTAMPTZ NOT NULL,
                used               BOOLEAN NOT NULL DEFAULT FALSE,
                parent_account_id  INT REFERENCES parent_accounts(id),
                created_at         TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            ALTER TABLE pair_codes
            ADD COLUMN IF NOT EXISTS parent_account_id INT REFERENCES parent_accounts(id)
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS lock_policy (
                id           INT PRIMARY KEY DEFAULT 1,
                lock_time    VARCHAR(8) NOT NULL DEFAULT '17:00',
                lock_days    VARCHAR(40) NOT NULL DEFAULT '월·수·금',
                pass_score   INT NOT NULL DEFAULT 70,
                allow_phone  BOOLEAN NOT NULL DEFAULT TRUE,
                allowlist    JSONB NOT NULL DEFAULT '["dialer","com.chungsora.child"]'::jsonb,
                CHECK (id = 1)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS shop_rewards (
                id         SERIAL PRIMARY KEY,
                label      VARCHAR(120) NOT NULL,
                won        INT NOT NULL,
                sort_order INT NOT NULL DEFAULT 0
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_quests (
                id          SERIAL PRIMARY KEY,
                parent_account_id INT REFERENCES parent_accounts(id),
                title       VARCHAR(120) NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                active      BOOLEAN NOT NULL DEFAULT TRUE,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            ALTER TABLE daily_quests
            ADD COLUMN IF NOT EXISTS parent_account_id INT REFERENCES parent_accounts(id)
        """)
        await conn.execute("""
            ALTER TABLE parent_accounts
            ADD COLUMN IF NOT EXISTS onboard_done BOOLEAN NOT NULL DEFAULT FALSE
        """)
        await conn.execute("""
            ALTER TABLE parent_accounts
            ADD COLUMN IF NOT EXISTS child_display_name VARCHAR(120) NOT NULL DEFAULT '자녀'
        """)
        await conn.execute("""
            ALTER TABLE parent_accounts
            ADD COLUMN IF NOT EXISTS points_balance INT NOT NULL DEFAULT 0
        """)
        await conn.execute("""
            ALTER TABLE parent_accounts
            ADD COLUMN IF NOT EXISTS base_clean_won INT NOT NULL DEFAULT 1000
        """)
        await conn.execute("""
            ALTER TABLE parent_accounts
            ADD COLUMN IF NOT EXISTS lock_time VARCHAR(8) NOT NULL DEFAULT '17:00'
        """)
        await conn.execute("""
            ALTER TABLE parent_accounts
            ADD COLUMN IF NOT EXISTS lock_days VARCHAR(40) NOT NULL DEFAULT '월·수·금'
        """)
        await conn.execute("""
            ALTER TABLE parent_accounts
            ADD COLUMN IF NOT EXISTS pass_score INT NOT NULL DEFAULT 70
        """)
        await conn.execute("""
            ALTER TABLE parent_accounts
            ADD COLUMN IF NOT EXISTS allow_phone BOOLEAN NOT NULL DEFAULT TRUE
        """)
        await conn.execute("""
            ALTER TABLE parent_accounts
            ADD COLUMN IF NOT EXISTS allowlist JSONB NOT NULL DEFAULT '["dialer","com.chungsora.child"]'::jsonb
        """)
        await conn.execute("""
            ALTER TABLE parent_accounts
            ADD COLUMN IF NOT EXISTS baseline_url TEXT
        """)
        await conn.execute("""
            ALTER TABLE parent_accounts
            ADD COLUMN IF NOT EXISTS baseline_urls JSONB NOT NULL DEFAULT '[]'::jsonb
        """)
        await conn.execute("""
            ALTER TABLE parent_accounts
            ADD COLUMN IF NOT EXISTS baseline_verified BOOLEAN NOT NULL DEFAULT FALSE
        """)
        await conn.execute("""
            ALTER TABLE parent_accounts
            ADD COLUMN IF NOT EXISTS notification_prefs JSONB NOT NULL DEFAULT '{"cleaning_done":true,"proposal":true,"streak":true}'::jsonb
        """)
        await conn.execute("""
            ALTER TABLE parent_accounts
            ADD COLUMN IF NOT EXISTS coach_character_id VARCHAR(20) NOT NULL DEFAULT 'jiu'
        """)
        await conn.execute("""
            ALTER TABLE parent_accounts
            ADD COLUMN IF NOT EXISTS child_coach_character_id VARCHAR(20)
        """)
        await conn.execute("""
            ALTER TABLE shop_rewards
            ADD COLUMN IF NOT EXISTS parent_account_id INT REFERENCES parent_accounts(id)
        """)
        await conn.execute("""
            ALTER TABLE praise_presets
            ADD COLUMN IF NOT EXISTS parent_account_id INT REFERENCES parent_accounts(id)
        """)
        await conn.execute("""
            ALTER TABLE cleaning_logs
            ADD COLUMN IF NOT EXISTS parent_account_id INT REFERENCES parent_accounts(id)
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS child_devices (
                id                  TEXT PRIMARY KEY,
                parent_account_id   INT NOT NULL REFERENCES parent_accounts(id),
                display_name        VARCHAR(120) NOT NULL DEFAULT '',
                paired_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS propose_threads (
                id                  TEXT PRIMARY KEY,
                parent_account_id   INT NOT NULL REFERENCES parent_accounts(id),
                label               VARCHAR(120) NOT NULL,
                points              INT NOT NULL,
                status              VARCHAR(20) NOT NULL DEFAULT 'pending',
                updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS propose_messages (
                id          TEXT PRIMARY KEY,
                thread_id   TEXT NOT NULL REFERENCES propose_threads(id) ON DELETE CASCADE,
                role        VARCHAR(10) NOT NULL,
                kind        VARCHAR(20) NOT NULL,
                label       VARCHAR(120) NOT NULL DEFAULT '',
                points      INT NOT NULL DEFAULT 0,
                reason      TEXT,
                at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS points_ledger (
                id                  SERIAL PRIMARY KEY,
                parent_account_id   INT NOT NULL REFERENCES parent_accounts(id),
                amount              INT NOT NULL,
                label               VARCHAR(120) NOT NULL DEFAULT '',
                kind                VARCHAR(20) NOT NULL DEFAULT 'earn',
                at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        from domain.chungsora.schema_migrations import migrate_per_user_isolation

        await migrate_per_user_isolation(conn)
        await _seed_defaults(conn)
    logger.info("[chungsora] tables initialized")


async def _seed_defaults(conn: asyncpg.Connection) -> None:
    from domain.chungsora.parent_account_seed import apply_defaults_for_db_parents

    await apply_defaults_for_db_parents(conn, _seed_parent_defaults)


async def _seed_parent_defaults(conn: asyncpg.Connection, parent_id: int) -> None:
    n = await conn.fetchval(
        "SELECT COUNT(*) FROM praise_presets WHERE parent_account_id = $1", parent_id
    )
    if n == 0:
        for phrase in ("우리 지민 최고", "100점"):
            await conn.execute(
                """
                INSERT INTO praise_presets (phrase, parent_account_id)
                VALUES ($1, $2)
                ON CONFLICT (parent_account_id, phrase) DO NOTHING
                """,
                phrase,
                parent_id,
            )

    n = await conn.fetchval(
        "SELECT COUNT(*) FROM shop_rewards WHERE parent_account_id = $1", parent_id
    )
    if n == 0:
        for i, (label, won) in enumerate(
            [("간식 1개", 1000), ("게임 30분", 1500), ("외출 1시간", 2500)]
        ):
            await conn.execute(
                """
                INSERT INTO shop_rewards (label, won, sort_order, parent_account_id)
                VALUES ($1, $2, $3, $4)
                """,
                label,
                won,
                i,
                parent_id,
            )


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class ChungsoraRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def verify_parent_login(self, login_id: str, password: str) -> dict[str, Any] | None:
        login_id = login_id.strip()
        if not login_id or not password:
            return None
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, login_id, display_name, password_hash
                FROM parent_accounts
                WHERE LOWER(login_id) = LOWER($1)
                """,
                login_id,
            )
        if not row or row["password_hash"] != _password_hash(password):
            return None
        return {
            "id": row["id"],
            "login_id": row["login_id"],
            "display_name": row["display_name"],
        }

    async def create_parent_account(
        self, login_id: str, password: str, display_name: str = ""
    ) -> dict[str, Any]:
        login_id = login_id.strip()
        name = (display_name or login_id).strip()
        async with self._pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM parent_accounts WHERE LOWER(login_id) = LOWER($1)",
                login_id,
            )
            if exists:
                raise ValueError("duplicate_login_id")
            row = await conn.fetchrow(
                """
                INSERT INTO parent_accounts (login_id, password_hash, display_name)
                VALUES ($1, $2, $3)
                RETURNING id, login_id, display_name
                """,
                login_id,
                _password_hash(password),
                name,
            )
            await _seed_parent_defaults(conn, row["id"])
        return {
            "id": row["id"],
            "login_id": row["login_id"],
            "display_name": row["display_name"],
        }

    async def get_parent_by_id(self, parent_id: int) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, login_id, display_name, onboard_done, child_display_name,
                       points_balance, base_clean_won, lock_time, lock_days, pass_score,
                       allow_phone, allowlist, baseline_url, baseline_urls, baseline_verified,
                       notification_prefs, coach_character_id, child_coach_character_id
                FROM parent_accounts WHERE id = $1
                """,
                parent_id,
            )
        if not row:
            return None
        allowlist = row["allowlist"]
        if isinstance(allowlist, str):
            allowlist = json.loads(allowlist)
        prefs = row["notification_prefs"]
        if isinstance(prefs, str):
            prefs = json.loads(prefs)
        baseline_urls = row["baseline_urls"]
        if isinstance(baseline_urls, str):
            baseline_urls = json.loads(baseline_urls)
        if not baseline_urls and row["baseline_url"]:
            baseline_urls = [row["baseline_url"]]
        return {
            "id": row["id"],
            "login_id": row["login_id"],
            "display_name": row["display_name"],
            "onboard_done": row["onboard_done"],
            "child_display_name": row["child_display_name"],
            "points_balance": row["points_balance"],
            "base_clean_won": row["base_clean_won"],
            "lock_time": row["lock_time"],
            "lock_days": row["lock_days"],
            "pass_score": row["pass_score"],
            "allow_phone": row["allow_phone"],
            "allowlist": allowlist,
            "baseline_url": row["baseline_url"],
            "baseline_urls": baseline_urls or [],
            "baseline_verified": bool(row["baseline_verified"]),
            "notification_prefs": prefs,
            "coach_character_id": _normalize_coach_id(row["coach_character_id"]),
            "child_coach_character_id": _normalize_coach_id(row["child_coach_character_id"]),
        }

    async def update_parent_profile(self, parent_id: int, body: dict) -> dict:
        allowed = {
            "onboard_done",
            "child_display_name",
            "base_clean_won",
            "lock_time",
            "lock_days",
            "pass_score",
            "allow_phone",
            "allowlist",
            "baseline_url",
            "baseline_urls",
            "baseline_verified",
            "notification_prefs",
            "coach_character_id",
            "child_coach_character_id",
        }
        fields = {k: v for k, v in body.items() if k in allowed and v is not None}
        if "coach_character_id" in fields:
            fields["coach_character_id"] = _normalize_coach_id(fields["coach_character_id"])
        if "child_coach_character_id" in fields:
            fields["child_coach_character_id"] = _normalize_coach_id(
                fields["child_coach_character_id"]
            )
        if not fields:
            profile = await self.get_parent_by_id(parent_id)
            return profile or {}
        sets = []
        values: list[Any] = []
        idx = 1
        for key, val in fields.items():
            if key in ("allowlist", "notification_prefs", "baseline_urls"):
                sets.append(f"{key} = ${idx}::jsonb")
                values.append(json.dumps(val))
            else:
                sets.append(f"{key} = ${idx}")
                values.append(val)
            idx += 1
        values.append(parent_id)
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"UPDATE parent_accounts SET {', '.join(sets)} WHERE id = ${idx}",
                *values,
            )
        profile = await self.get_parent_by_id(parent_id)
        return profile or {}

    async def get_family_summary(self, parent_id: int) -> dict:
        profile = await self.get_parent_by_id(parent_id)
        if not profile:
            return {}
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log = await self.get_log(parent_id, today)
        streak = log.get("streak_days") or 0
        mult = _streak_mult(streak)
        return {
            "child_display_name": profile["child_display_name"],
            "points_balance": profile["points_balance"],
            "base_clean_won": profile["base_clean_won"],
            "streak_days": streak,
            "streak_mult": mult,
            "coach_character_id": profile.get("coach_character_id") or "jiu",
            "child_coach_character_id": profile.get("child_coach_character_id"),
            "effective_coach_character_id": _effective_coach_id(profile),
            "lock_time": profile["lock_time"],
            "lock_days": profile["lock_days"],
            "pass_score": profile["pass_score"],
            "onboard_done": profile["onboard_done"],
            "today_score": log.get("score") or 0,
            "baseline_url": _normalize_upload_path(profile.get("baseline_url")),
            "baseline_urls": _pad_baseline_urls(profile.get("baseline_urls") or []),
            "baseline_verified": bool(profile.get("baseline_verified")),
        }

    async def set_baseline_slot(self, parent_id: int, slot: int, url: str) -> list[str]:
        profile = await self.get_parent_by_id(parent_id)
        if not profile:
            return []
        urls: list[str | None] = list(profile.get("baseline_urls") or [])
        while len(urls) <= slot:
            urls.append(None)
        urls[slot] = url
        await self.update_parent_profile(
            parent_id,
            {
                "baseline_urls": urls,
                "baseline_url": urls[0] if urls else url,
                "baseline_verified": False,
            },
        )
        return [u for u in urls if u]

    async def ensure_log(self, parent_id: int, date_str: str) -> None:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO cleaning_logs (parent_account_id, log_date) VALUES ($1, $2)
                ON CONFLICT (parent_account_id, log_date) DO NOTHING
                """,
                parent_id,
                d,
            )

    async def get_log(self, parent_id: int, date_str: str) -> dict[str, Any]:
        await self.ensure_log(parent_id, date_str)
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT score, streak_days, before_url, after_url
                FROM cleaning_logs
                WHERE parent_account_id = $1 AND log_date = $2
                """,
                parent_id,
                d,
            )
            msgs = await conn.fetch(
                """
                SELECT id, role, text, badge, at
                FROM log_messages
                WHERE parent_account_id = $1 AND log_date = $2
                ORDER BY at
                """,
                parent_id,
                d,
            )
        messages = []
        for m in msgs:
            item: dict[str, Any] = {
                "id": m["id"],
                "role": m["role"],
                "text": m["text"],
                "at": m["at"].replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
            }
            if m["badge"]:
                item["badge"] = m["badge"]
            messages.append(item)
        return {
            "date": date_str,
            "score": row["score"] if row else 0,
            "streak_days": row["streak_days"] if row else 0,
            "before_url": row["before_url"] if row else None,
            "after_url": row["after_url"] if row else None,
            "messages": messages,
        }

    async def patch_log(
        self, parent_id: int, date_str: str, score: int | None, streak_days: int | None
    ) -> dict:
        await self.ensure_log(parent_id, date_str)
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        async with self._pool.acquire() as conn:
            if score is not None:
                await conn.execute(
                    """
                    UPDATE cleaning_logs SET score = $3
                    WHERE parent_account_id = $1 AND log_date = $2
                    """,
                    parent_id,
                    d,
                    score,
                )
            if streak_days is not None:
                await conn.execute(
                    """
                    UPDATE cleaning_logs SET streak_days = $3
                    WHERE parent_account_id = $1 AND log_date = $2
                    """,
                    parent_id,
                    d,
                    streak_days,
                )
        return await self.get_log(parent_id, date_str)

    async def set_log_photo(self, parent_id: int, date_str: str, phase: str, url: str) -> None:
        await self.ensure_log(parent_id, date_str)
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        col = "before_url" if phase == "before" else "after_url"
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""
                UPDATE cleaning_logs SET {col} = $3
                WHERE parent_account_id = $1 AND log_date = $2
                """,
                parent_id,
                d,
                url,
            )

    async def add_message(
        self, parent_id: int, date_str: str, role: str, text: str, badge: str | None
    ) -> dict:
        await self.ensure_log(parent_id, date_str)
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        msg_id = f"m-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO log_messages (id, parent_account_id, log_date, role, text, badge)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                msg_id,
                parent_id,
                d,
                role,
                text.strip(),
                badge.strip() if badge else None,
            )
        msg: dict[str, Any] = {
            "id": msg_id,
            "role": role,
            "text": text.strip(),
            "at": _now_iso(),
        }
        if badge:
            msg["badge"] = badge.strip()
        return msg

    async def calendar(self, parent_id: int, year_month: str) -> dict:
        profile = await self.get_parent_by_id(parent_id)
        balance = profile["points_balance"] if profile else 0
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT log_date::text AS d, score
                FROM cleaning_logs
                WHERE to_char(log_date, 'YYYY-MM') = $1
                  AND parent_account_id = $2
                  AND (score > 0 OR before_url IS NOT NULL OR after_url IS NOT NULL)
                ORDER BY log_date
                """,
                year_month,
                parent_id,
            )
        dates = [r["d"] for r in rows]
        total = sum(r["score"] for r in rows)
        points = balance if balance else (total or 0)
        return {"year_month": year_month, "dates": dates, "points": points}

    async def list_presets(self, parent_id: int) -> list[str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT phrase FROM praise_presets
                WHERE parent_account_id = $1
                ORDER BY created_at DESC LIMIT 8
                """,
                parent_id,
            )
        return [r["phrase"] for r in rows]

    async def add_preset(self, parent_id: int, phrase: str) -> list[str]:
        phrase = phrase.strip()
        if not phrase:
            return await self.list_presets(parent_id)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO praise_presets (phrase, parent_account_id)
                VALUES ($1, $2)
                ON CONFLICT (parent_account_id, phrase) DO NOTHING
                """,
                phrase,
                parent_id,
            )
        return await self.list_presets(parent_id)

    async def delete_preset(self, parent_id: int, phrase: str) -> list[str]:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM praise_presets
                WHERE phrase = $1 AND parent_account_id = $2
                """,
                phrase.strip(),
                parent_id,
            )
        return await self.list_presets(parent_id)

    def _gen_code(self) -> str:
        chars = string.digits + string.ascii_uppercase
        chars = chars.replace("O", "").replace("0", "").replace("I", "").replace("1", "")
        return "".join(random.choice(chars) for _ in range(6))

    async def has_child_device(self, parent_id: int) -> bool:
        async with self._pool.acquire() as conn:
            n = await conn.fetchval(
                "SELECT COUNT(*)::int FROM child_devices WHERE parent_account_id = $1",
                parent_id,
            )
        return bool(n and n > 0)

    async def sync_onboard_done_if_paired(self, parent_id: int) -> dict | None:
        """자녀 기기가 있으나 onboard_done=false 인 기존 계정 보정 (B-1)."""
        profile = await self.get_parent_by_id(parent_id)
        if not profile or profile.get("onboard_done"):
            return profile
        if not await self.has_child_device(parent_id):
            return profile
        return await self.update_parent_profile(parent_id, {"onboard_done": True})

    async def get_pair_code_status(self, parent_id: int, code: str) -> dict:
        code = code.strip().upper()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT used FROM pair_codes
                WHERE code = $1 AND parent_account_id = $2
                """,
                code,
                parent_id,
            )
            device_count = await conn.fetchval(
                "SELECT COUNT(*)::int FROM child_devices WHERE parent_account_id = $1",
                parent_id,
            )
        return {
            "code": code,
            "code_used": bool(row and row["used"]),
            "child_paired": bool(device_count and device_count > 0),
        }

    async def issue_pair_code(self, parent_account_id: int, ttl_minutes: int = 10) -> dict:
        code = self._gen_code()
        expires = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO pair_codes (code, expires_at, parent_account_id)
                VALUES ($1, $2, $3)
                """,
                code,
                expires,
                parent_account_id,
            )
        return {
            "code": code,
            "expires_at": expires.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "ttl_seconds": ttl_minutes * 60,
            "link_path": f"/child/pair?code={code}",
            "parent_account_id": parent_account_id,
        }

    async def verify_pair_code(self, code: str) -> dict:
        code = code.strip().upper()
        now = datetime.now(timezone.utc)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT code, expires_at, used, parent_account_id
                FROM pair_codes WHERE code = $1
                """,
                code,
            )
            if not row:
                return {"ok": False, "reason": "invalid"}
            if row["used"]:
                return {"ok": False, "reason": "used"}
            exp = row["expires_at"]
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < now:
                return {"ok": False, "reason": "expired"}
            await conn.execute("UPDATE pair_codes SET used = TRUE WHERE code = $1", code)
            device_id = f"dev-{code.lower()}"
            await conn.execute(
                """
                INSERT INTO child_devices (id, parent_account_id)
                VALUES ($1, $2)
                ON CONFLICT (id) DO UPDATE SET parent_account_id = EXCLUDED.parent_account_id
                """,
                device_id,
                row["parent_account_id"],
            )
        from core.jwt_utils import create_child_token

        parent_id = int(row["parent_account_id"])
        await self.sync_onboard_done_if_paired(parent_id)
        token = create_child_token(device_id, parent_id)
        return {
            "ok": True,
            "code": code,
            "parent_account_id": parent_id,
            "device_id": device_id,
            "device_token": token,
        }

    async def refresh_child_device_token(self, device_id: str) -> dict:
        """등록된 기기는 JWT 만료만 갱신 — 연결(DB)은 유지."""
        device_id = device_id.strip()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT parent_account_id FROM child_devices WHERE id = $1
                """,
                device_id,
            )
        if not row:
            return {"ok": False, "reason": "not_registered"}
        parent_id = int(row["parent_account_id"])
        await self.sync_onboard_done_if_paired(parent_id)
        from core.jwt_utils import create_child_token

        token = create_child_token(device_id, parent_id)
        return {
            "ok": True,
            "device_id": device_id,
            "parent_account_id": parent_id,
            "device_token": token,
        }

    async def get_lock_policy(self, parent_id: int) -> dict:
        profile = await self.get_parent_by_id(parent_id)
        if not profile:
            raise ValueError("parent_not_found")
        return {
            "lock_time": profile["lock_time"],
            "lock_days": profile["lock_days"],
            "pass_score": profile["pass_score"],
            "allow_phone": profile["allow_phone"],
            "allowlist": profile["allowlist"],
        }

    async def put_lock_policy(self, parent_id: int, body: dict) -> dict:
        await self.update_parent_profile(parent_id, body)
        return await self.get_lock_policy(parent_id)

    async def list_shop_rewards(self, parent_id: int) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, label, won FROM shop_rewards
                WHERE parent_account_id = $1
                ORDER BY sort_order, id
                """,
                parent_id,
            )
        return [{"id": str(r["id"]), "label": r["label"], "won": r["won"]} for r in rows]

    async def create_shop_reward(self, parent_id: int, label: str, won: int) -> list[dict]:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO shop_rewards (label, won, sort_order, parent_account_id)
                VALUES ($1, $2, (SELECT COALESCE(MAX(sort_order),0)+1 FROM shop_rewards WHERE parent_account_id = $3), $3)
                """,
                label,
                won,
                parent_id,
            )
        return await self.list_shop_rewards(parent_id)

    async def update_shop_reward(
        self, parent_id: int, reward_id: int, label: str | None, won: int | None
    ) -> list[dict]:
        async with self._pool.acquire() as conn:
            if label is not None:
                await conn.execute(
                    """
                    UPDATE shop_rewards SET label = $3
                    WHERE id = $1 AND parent_account_id = $2
                    """,
                    reward_id,
                    parent_id,
                    label,
                )
            if won is not None:
                await conn.execute(
                    """
                    UPDATE shop_rewards SET won = $3
                    WHERE id = $1 AND parent_account_id = $2
                    """,
                    reward_id,
                    parent_id,
                    won,
                )
        return await self.list_shop_rewards(parent_id)

    async def delete_shop_reward(self, parent_id: int, reward_id: int) -> list[dict]:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM shop_rewards
                WHERE id = $1 AND parent_account_id = $2
                """,
                reward_id,
                parent_id,
            )
        return await self.list_shop_rewards(parent_id)

    async def list_daily_quests(self, parent_id: int) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, title, description, active FROM daily_quests
                WHERE parent_account_id = $1 AND active = TRUE
                ORDER BY id DESC
                """,
                parent_id,
            )
        return [
            {
                "id": str(r["id"]),
                "title": r["title"],
                "description": r["description"],
                "active": r["active"],
            }
            for r in rows
        ]

    async def create_daily_quest(
        self, parent_id: int, title: str, description: str = ""
    ) -> list[dict]:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO daily_quests (title, description, parent_account_id)
                VALUES ($1, $2, $3)
                """,
                title.strip(),
                description.strip(),
                parent_id,
            )
        return await self.list_daily_quests(parent_id)

    async def delete_daily_quest(self, parent_id: int, quest_id: int) -> list[dict]:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE daily_quests SET active = FALSE
                WHERE id = $1 AND parent_account_id = $2
                """,
                quest_id,
                parent_id,
            )
        return await self.list_daily_quests(parent_id)

    async def adjust_points(
        self, parent_id: int, amount: int, label: str, kind: str
    ) -> dict:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE parent_accounts
                SET points_balance = points_balance + $2
                WHERE id = $1
                RETURNING points_balance
                """,
                parent_id,
                amount,
            )
            await conn.execute(
                """
                INSERT INTO points_ledger (parent_account_id, amount, label, kind)
                VALUES ($1, $2, $3, $4)
                """,
                parent_id,
                amount,
                label,
                kind,
            )
        return {"balance": row["points_balance"] if row else 0}

    def _thread_row_to_dict(self, row, messages: list) -> dict:
        return {
            "id": row["id"],
            "label": row["label"],
            "points": row["points"],
            "status": row["status"],
            "updatedAt": row["updated_at"].replace(tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "messages": messages,
        }

    def _msg_row(self, m) -> dict:
        item = {
            "id": m["id"],
            "role": m["role"],
            "kind": m["kind"],
            "label": m["label"],
            "points": m["points"],
            "at": m["at"].replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        if m["reason"]:
            item["reason"] = m["reason"]
        return item

    async def list_propose_threads(self, parent_id: int) -> list[dict]:
        async with self._pool.acquire() as conn:
            threads = await conn.fetch(
                """
                SELECT id, label, points, status, updated_at
                FROM propose_threads WHERE parent_account_id = $1
                ORDER BY updated_at DESC
                """,
                parent_id,
            )
            out = []
            for t in threads:
                msgs = await conn.fetch(
                    """
                    SELECT id, role, kind, label, points, reason, at
                    FROM propose_messages WHERE thread_id = $1 ORDER BY at
                    """,
                    t["id"],
                )
                out.append(
                    self._thread_row_to_dict(t, [self._msg_row(m) for m in msgs])
                )
        return out

    async def submit_proposal(self, parent_id: int, label: str, points: int) -> dict:
        import uuid

        tid = f"prop-{uuid.uuid4().hex[:8]}"
        mid = f"m-{uuid.uuid4().hex[:8]}"
        at = datetime.now(timezone.utc)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO propose_threads (id, parent_account_id, label, points, status, updated_at)
                VALUES ($1, $2, $3, $4, 'pending', $5)
                """,
                tid,
                parent_id,
                label,
                points,
                at,
            )
            await conn.execute(
                """
                INSERT INTO propose_messages (id, thread_id, role, kind, label, points, at)
                VALUES ($1, $2, 'child', 'proposal', $3, $4, $5)
                """,
                mid,
                tid,
                label,
                points,
                at,
            )
        threads = await self.list_propose_threads(parent_id)
        thread = next((t for t in threads if t["id"] == tid), None)
        return {"thread": thread}

    async def accept_proposal(self, parent_id: int, thread_id: str) -> dict:
        WON_PER_P = 10
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, label, points FROM propose_threads
                WHERE id = $1 AND parent_account_id = $2
                """,
                thread_id,
                parent_id,
            )
            if not row:
                return {"ok": False, "error": "not found"}
            at = datetime.now(timezone.utc)
            await conn.execute(
                "UPDATE propose_threads SET status = 'accepted', updated_at = $2 WHERE id = $1",
                thread_id,
                at,
            )
            await conn.execute(
                """
                INSERT INTO propose_messages (id, thread_id, role, kind, label, points, at)
                VALUES ($1, $2, 'parent', 'accept', $3, $4, $5)
                """,
                f"accept-{thread_id}",
                thread_id,
                row["label"],
                row["points"],
                at,
            )
        won = int(row["points"]) * WON_PER_P
        await self.create_shop_reward(parent_id, str(row["label"]), won)
        return {"ok": True, "reward_won": won}

    async def reject_proposal(self, parent_id: int, thread_id: str, reason: str) -> dict:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, label, points FROM propose_threads
                WHERE id = $1 AND parent_account_id = $2
                """,
                thread_id,
                parent_id,
            )
            if not row:
                return {"ok": False, "error": "not found"}
            at = datetime.now(timezone.utc)
            await conn.execute(
                "UPDATE propose_threads SET status = 'rejected', updated_at = $2 WHERE id = $1",
                thread_id,
                at,
            )
            await conn.execute(
                """
                INSERT INTO propose_messages (id, thread_id, role, kind, label, points, reason, at)
                VALUES ($1, $2, 'parent', 'reject', $3, $4, $5, $6)
                """,
                f"reject-{thread_id}",
                thread_id,
                row["label"],
                row["points"],
                reason,
                at,
            )
        return {"ok": True}


async def get_chungsora_repo() -> ChungsoraRepository:
    from core.database import get_pool

    return ChungsoraRepository(await get_pool())
