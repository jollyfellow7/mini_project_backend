# -*- coding: utf-8 -*-
"""운영 API에 최신 Fix 배포 여부 확인 (A-1).

Usage:
  python -m tools.verify_production_deploy
  python -m tools.verify_production_deploy --base http://43.201.95.108:8080
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def _post(url: str, body: dict) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            raw = res.read().decode("utf-8")
            return res.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return e.code, {"raw": raw}


def _patch(url: str, body: dict, token: str) -> int:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return res.status
    except urllib.error.HTTPError as e:
        return e.code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://43.201.95.108:8080")
    args = parser.parse_args()
    api = args.base.rstrip("/") + "/api/v1"
    ok = True

    print(f"Checking {args.base} ...\n")

    # health
    try:
        with urllib.request.urlopen(args.base + "/health", timeout=10) as res:
            print(f"[{'OK' if res.status == 200 else 'NG'}] GET /health -> {res.status}")
            if res.status != 200:
                ok = False
    except Exception as exc:
        print(f"[NG] GET /health -> {exc}")
        ok = False

    # login onboard_done (needs real user — skip if no creds, check OpenAPI or dummy)
    print(
        "[--] POST /auth/login onboard_done field: deploy 후 smoke_neon_e2e --http 로 확인"
    )
    print(
        "[--] PATCH /family/summary: deploy 후 smoke_neon_e2e --http 로 확인"
    )
    print(
        "[--] GET /family/pair/status: 배포 후 부모 토큰으로 ?code=XXXXXX 호출 (401/200)"
    )

    print("\nRun after deploy:")
    print(f"  python -m tools.smoke_neon_e2e --http {args.base}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
