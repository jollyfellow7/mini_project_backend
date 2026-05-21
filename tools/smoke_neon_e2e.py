# -*- coding: utf-8 -*-
"""Neon DB + API E2E 스모크 (로그인 → 페어링 → 제안 → 로그 → 포인트 → 보상).

Usage:
  cd mini_backend
  python -m tools.smoke_neon_e2e
  python -m tools.smoke_neon_e2e --http http://43.201.95.108:8080
  python -m tools.smoke_neon_e2e --keep   # 테스트 계정 유지
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.database import close_pool, get_pool
from core.jwt_utils import create_access_token
from domain.chungsora.chungsora_repository import get_chungsora_repo, init_chungsora_tables

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def add(self, area: str, name: str, status: str, detail: str = "") -> None:
        self.rows.append((area, name, f"{status} {detail}".strip()))

    def ok(self) -> bool:
        return all(r[2].startswith(PASS) or r[2].startswith(SKIP) for r in self.rows)

    def print_summary(self) -> None:
        w = max(len(r[0]) for r in self.rows) if self.rows else 10
        print("\n=== Smoke E2E Report ===")
        for area, name, msg in self.rows:
            mark = "OK" if msg.startswith(PASS) else ("--" if msg.startswith(SKIP) else "NG")
            print(f"  {mark} [{area:{w}}] {name}: {msg}")
        fails = [r for r in self.rows if r[2].startswith(FAIL)]
        print(f"\nTotal: {len(self.rows)}  Fail: {len(fails)}")


def _http_json(method: str, url: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            raw = res.read().decode("utf-8")
            return res.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return e.code, {"detail": raw}


async def cleanup_parent(parent_id: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM propose_messages WHERE thread_id IN (SELECT id FROM propose_threads WHERE parent_account_id = $1)",
            parent_id,
        )
        await conn.execute(
            "DELETE FROM propose_threads WHERE parent_account_id = $1", parent_id
        )
        await conn.execute(
            "DELETE FROM log_messages WHERE parent_account_id = $1", parent_id
        )
        await conn.execute(
            "DELETE FROM cleaning_logs WHERE parent_account_id = $1", parent_id
        )
        await conn.execute(
            "DELETE FROM points_ledger WHERE parent_account_id = $1", parent_id
        )
        await conn.execute(
            "DELETE FROM shop_rewards WHERE parent_account_id = $1", parent_id
        )
        await conn.execute(
            "DELETE FROM daily_quests WHERE parent_account_id = $1", parent_id
        )
        await conn.execute(
            "DELETE FROM praise_presets WHERE parent_account_id = $1", parent_id
        )
        await conn.execute(
            "DELETE FROM child_devices WHERE parent_account_id = $1", parent_id
        )
        await conn.execute(
            "DELETE FROM pair_codes WHERE parent_account_id = $1", parent_id
        )
        await conn.execute("DELETE FROM parent_accounts WHERE id = $1", parent_id)


async def run_db_flow(rep: Report, login_id: str, password: str) -> dict:
    pool = await get_pool()
    await init_chungsora_tables(pool)
    repo = await get_chungsora_repo()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 1) 부모 계정
    try:
        user = await repo.create_parent_account(login_id, password, "스모크부모")
        parent_id = user["id"]
        rep.add("DB", "create_parent", PASS, f"id={parent_id}")
    except ValueError as exc:
        if str(exc) != "duplicate_login_id":
            rep.add("DB", "create_parent", FAIL, str(exc))
            return {}
        user = await repo.verify_parent_login(login_id, password)
        parent_id = user["id"]
        rep.add("DB", "create_parent", SKIP, "already exists")

    # 2) 로그인 프로필 onboard_done
    profile = await repo.get_parent_by_id(parent_id)
    rep.add(
        "DB",
        "profile_fields",
        PASS if profile and "onboard_done" in profile else FAIL,
        f"onboard_done={profile.get('onboard_done') if profile else None}",
    )

    parent_token = create_access_token({"sub": str(parent_id), "login_id": login_id})

    # 3) 페어링
    pair = await repo.issue_pair_code(parent_id)
    code = pair["code"]
    verify = await repo.verify_pair_code(code)
    if not verify.get("ok"):
        rep.add("DB", "pair_verify", FAIL, str(verify.get("reason")))
        return {}
    child_token = verify["device_token"]
    rep.add("DB", "pair_verify", PASS, f"device={verify['device_id']}")

    profile = await repo.sync_onboard_done_if_paired(parent_id)
    rep.add(
        "DB",
        "onboard_after_pair",
        PASS if profile and profile.get("onboard_done") else FAIL,
    )

    await repo.update_parent_profile(
        parent_id, {"child_display_name": "스모크자녀", "onboard_done": True}
    )

    # 4) 제안
    prop = await repo.submit_proposal(parent_id, "침대 정리", 5)
    thread_id = prop.get("thread", {}).get("id")
    threads = await repo.list_propose_threads(parent_id)
    rep.add(
        "DB",
        "propose_submit",
        PASS if thread_id and any(t["id"] == thread_id for t in threads) else FAIL,
        f"threads={len(threads)}",
    )

    if thread_id:
        await repo.accept_proposal(parent_id, thread_id)
        threads2 = await repo.list_propose_threads(parent_id)
        accepted = next((t for t in threads2 if t["id"] == thread_id), None)
        rep.add(
            "DB",
            "propose_accept",
            PASS if accepted and accepted.get("status") == "accepted" else FAIL,
            f"status={accepted.get('status') if accepted else None}",
        )

    # 5) 로그 메시지
    msg = await repo.add_message(parent_id, today, "child", "스모크 로그 메시지", "테스트")
    log = await repo.get_log(parent_id, today)
    rep.add(
        "DB",
        "log_message",
        PASS if any(m.get("text") == "스모크 로그 메시지" for m in log.get("messages", [])) else FAIL,
        f"msg_id={msg.get('id')}",
    )

    await repo.patch_log(parent_id, today, score=85, streak_days=3)
    log2 = await repo.get_log(parent_id, today)
    rep.add(
        "DB",
        "log_patch",
        PASS if log2.get("score") == 85 else FAIL,
        f"score={log2.get('score')}",
    )

    # 6) 포인트
    pts = await repo.adjust_points(parent_id, 10, "스모크 적립", "earn")
    rep.add("DB", "points_earn", PASS if pts.get("balance", 0) >= 10 else FAIL, str(pts))

    # 7) 보상
    rewards = await repo.create_shop_reward(parent_id, "스모크 보상", 5000)
    rep.add(
        "DB",
        "shop_reward",
        PASS if rewards and any(r.get("label") == "스모크 보상" for r in rewards) else FAIL,
        f"count={len(rewards)}",
    )

    quests = await repo.create_daily_quest(parent_id, "스모크 퀘스트", "설명")
    rep.add(
        "DB",
        "daily_quest",
        PASS if quests else FAIL,
        f"count={len(quests)}",
    )

    # 8) ledger 확인
    async with pool.acquire() as conn:
        ledger_n = await conn.fetchval(
            "SELECT COUNT(*)::int FROM points_ledger WHERE parent_account_id = $1",
            parent_id,
        )
        device_n = await conn.fetchval(
            "SELECT COUNT(*)::int FROM child_devices WHERE parent_account_id = $1",
            parent_id,
        )
    rep.add("DB", "points_ledger_rows", PASS if ledger_n and ledger_n > 0 else FAIL, str(ledger_n))
    rep.add("DB", "child_devices_rows", PASS if device_n and device_n > 0 else FAIL, str(device_n))

    result = {
        "parent_id": parent_id,
        "parent_token": parent_token,
        "child_token": child_token,
        "login_id": login_id,
        "password": password,
        "today": today,
    }

    return result


def run_http_flow(rep: Report, base: str, ctx: dict) -> None:
    if not ctx:
        rep.add("HTTP", "all", SKIP, "no db context")
        return
    api = base.rstrip("/") + "/api/v1"
    pt = ctx["parent_token"]
    ct = ctx["child_token"]
    today = ctx["today"]

    st, health = _http_json("GET", base + "/health")
    rep.add("HTTP", "health", PASS if st == 200 else FAIL, str(st))

    st, login = _http_json(
        "POST",
        f"{api}/auth/login",
        {"login_id": ctx["login_id"], "password": ctx["password"]},
    )
    has_onboard = "onboard_done" in login
    rep.add(
        "HTTP",
        "auth_login",
        PASS if st == 200 and has_onboard else FAIL,
        f"onboard_done={login.get('onboard_done')}",
    )
    if st == 200 and login.get("token"):
        pt = login["token"]

    st, me = _http_json("GET", f"{api}/auth/me", token=pt)
    rep.add(
        "HTTP",
        "auth_me",
        PASS if st == 200 and me.get("onboard_done") is True else FAIL,
        str(me.get("onboard_done")),
    )

    st, summary = _http_json("GET", f"{api}/family/summary", token=pt)
    rep.add("HTTP", "family_summary_parent", PASS if st == 200 else FAIL, str(st))

    st, csum = _http_json("GET", f"{api}/family/summary", token=ct)
    rep.add("HTTP", "family_summary_child", PASS if st == 200 else FAIL, str(st))

    st, prop = _http_json(
        "POST",
        f"{api}/child/propose",
        {"label": "HTTP 제안", "points": 3},
        token=ct,
    )
    rep.add("HTTP", "child_propose", PASS if st == 200 else FAIL, str(st))

    st, plist = _http_json("GET", f"{api}/parent/propose", token=pt)
    rep.add(
        "HTTP",
        "parent_propose_list",
        PASS if st == 200 and plist.get("threads") else FAIL,
        f"n={len(plist.get('threads', []))}",
    )

    st, bal = _http_json("GET", f"{api}/points/balance", token=ct)
    rep.add("HTTP", "points_balance", PASS if st == 200 else FAIL, str(bal.get("balance")))

    st, earn = _http_json(
        "POST",
        f"{api}/points/earn",
        {"amount": 5, "label": "HTTP earn"},
        token=ct,
    )
    rep.add("HTTP", "points_earn", PASS if st == 200 else FAIL, str(earn.get("balance")))

    st, log = _http_json("GET", f"{api}/logs/{today}", token=ct)
    rep.add("HTTP", "logs_get", PASS if st == 200 else FAIL, str(st))

    st, msg = _http_json(
        "POST",
        f"{api}/logs/{today}/messages",
        {"role": "child", "text": "HTTP 로그"},
        token=ct,
    )
    rep.add("HTTP", "logs_message", PASS if st == 200 else FAIL, str(st))

    st, shop = _http_json("GET", f"{api}/rewards/shop", token=ct)
    rep.add(
        "HTTP",
        "rewards_shop",
        PASS if st == 200 else FAIL,
        f"n={len(shop.get('rewards', []))}",
    )

    st, patch = _http_json(
        "PATCH",
        f"{api}/family/summary",
        {"child_display_name": "HTTP자녀"},
        token=pt,
    )
    rep.add("HTTP", "family_patch_summary", PASS if st == 200 else FAIL, str(st))


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", default="", help="API base e.g. http://host:8080")
    parser.add_argument("--keep", action="store_true", help="Keep test parent in DB")
    parser.add_argument("--login-id", default="", help="Fixed login_id (default smoke_<ts>)")
    args = parser.parse_args()

    login_id = args.login_id or f"smoke_{int(time.time())}"
    password = "smoke1324"
    rep = Report()

    from core.config import settings

    if not settings.database_url:
        rep.add("DB", "config", FAIL, "DATABASE_URL / NEON_* not set")
        rep.print_summary()
        return 1

    ctx: dict = {}
    try:
        ctx = await run_db_flow(rep, login_id, password)
        if args.http:
            run_http_flow(rep, args.http, ctx)
        if not args.keep and ctx.get("parent_id"):
            try:
                await cleanup_parent(ctx["parent_id"])
                rep.add("DB", "cleanup", PASS)
            except Exception as exc:
                rep.add("DB", "cleanup", FAIL, repr(exc))
    except Exception as exc:
        rep.add("DB", "exception", FAIL, repr(exc))
    finally:
        await close_pool()

    rep.print_summary()
    if ctx and args.keep:
        print(f"\nTest account kept: login_id={login_id} password={password}")
    return 0 if rep.ok() else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
