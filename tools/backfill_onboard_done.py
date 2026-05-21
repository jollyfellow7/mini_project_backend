# -*- coding: utf-8 -*-
"""자녀 기기가 있는데 onboard_done=false 인 계정 일괄 보정 (B-1).

Usage:
  cd mini_backend
  python -m tools.backfill_onboard_done
  python -m tools.backfill_onboard_done --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.database import close_pool, get_pool
from domain.chungsora.chungsora_repository import get_chungsora_repo, init_chungsora_tables


async def _run(dry_run: bool) -> None:
    pool = await get_pool()
    await init_chungsora_tables(pool)
    repo = await get_chungsora_repo()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT p.id, p.login_id, p.onboard_done
            FROM parent_accounts p
            INNER JOIN child_devices d ON d.parent_account_id = p.id
            WHERE p.onboard_done = FALSE
            ORDER BY p.id
            """
        )

    if not rows:
        print("No accounts need backfill.")
        return

    print(f"Found {len(rows)} parent(s) with child device but onboard_done=false")
    for row in rows:
        pid = row["id"]
        lid = row["login_id"]
        if dry_run:
            print(f"  [dry-run] would fix parent id={pid} login_id={lid}")
            continue
        profile = await repo.sync_onboard_done_if_paired(pid)
        print(
            f"  fixed id={pid} login_id={lid} onboard_done={profile.get('onboard_done') if profile else None}"
        )

    await close_pool()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(_run(args.dry_run))


if __name__ == "__main__":
    main()
