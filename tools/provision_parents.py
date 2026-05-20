# -*- coding: utf-8 -*-
"""Neon parent_accounts 프로비저닝 CLI (하드코딩 없음 — 인자로 전달).

Usage:
  python -m tools.provision_parents sung shine silver Iseul --password 1324
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.database import close_pool, get_pool
from domain.chungsora.chungsora_repository import get_chungsora_repo, init_chungsora_tables


async def _run(login_ids: list[str], password: str) -> None:
    pool = await get_pool()
    await init_chungsora_tables(pool)
    repo = await get_chungsora_repo()
    for login_id in login_ids:
        lid = login_id.strip()
        if not lid:
            continue
        try:
            user = await repo.create_parent_account(lid, password, lid)
            print(f"created  id={user['id']} login_id={user['login_id']}")
        except ValueError as exc:
            if str(exc) != "duplicate_login_id":
                raise
            print(f"exists   login_id={lid} (skipped)")
    await close_pool()


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision parent accounts in Neon DB")
    parser.add_argument("login_ids", nargs="+", help="login_id values to create")
    parser.add_argument("--password", required=True, help="shared password")
    args = parser.parse_args()
    asyncio.run(_run(args.login_ids, args.password))


if __name__ == "__main__":
    main()
