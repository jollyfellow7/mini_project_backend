# -*- coding: utf-8 -*-
"""
실제 Gemini 비교 채점 증명 테스트 (가짜 아님).

이 스크립트는 백엔드 운영 코드 그대로 (domain.cleaning.cleaning_service.compare_with_baseline)
를 호출한다. 별도 재구현 없음 → "진짜로 채점하는지"를 운영 경로로 검증한다.

검증 시나리오:
  1) baseline(깨끗) vs after_clean(깨끗)  → 높은 점수 기대 (>= pass_score → 통과)
  2) baseline(깨끗) vs after_messy(엉망)  → 낮은 점수 기대 (<  pass_score → 실패)

만약 채점이 가짜(상수 반환)라면 두 점수가 비슷하게 나온다.
점수가 내용에 따라 갈리면 = 진짜 Gemini 비전 비교가 동작하는 것.

실행 (네트워크 + GEMINI_API_KEY 필요. 로컬 PC 또는 EC2에서):
    cd mini_backend
    python -m tools.test_real_baseline_compare           # 기본 pass_score=80
    python -m tools.test_real_baseline_compare --pass-score 70
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# mini_backend 를 import 경로에 추가 (tools/ 의 부모)
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

# .env 로드 (core.config 가 .env 를 읽지만, 명시적으로도 확인)
from core.config import settings  # noqa: E402
from domain.cleaning import cleaning_service  # noqa: E402  ← 운영 코드 그대로

SAMPLES = Path(__file__).resolve().parent / "sample_rooms"


def _load(name: str) -> bytes:
    p = SAMPLES / name
    if not p.exists():
        raise SystemExit(f"샘플 이미지 없음: {p}")
    return p.read_bytes()


async def run(pass_score: int) -> int:
    if not settings.GEMINI_API_KEY:
        raise SystemExit("GEMINI_API_KEY 가 비어 있습니다 (.env 확인).")

    baseline = _load("baseline_clean.jpg")
    after_clean = _load("after_clean.jpg")
    after_messy = _load("after_messy.jpg")

    print("=" * 64)
    print("실제 Gemini compare_with_baseline 채점 (운영 코드 호출)")
    print(f"부모 기준 통과 점수 pass_score = {pass_score}")
    print("=" * 64)

    cases = [
        ("깨끗→깨끗 (통과 기대)", after_clean),
        ("깨끗→엉망 (실패 기대)", after_messy),
    ]
    results = []
    for label, after_bytes in cases:
        res = await cleaning_service.compare_with_baseline(
            baseline, after_bytes, slot_label="책상"
        )
        passed = res.cleanliness >= pass_score
        results.append((label, res.cleanliness, passed))
        print(f"\n[{label}]")
        print(f"  AI 청결도 점수 : {res.cleanliness}/100")
        print(f"  사용 모델       : {res.model_id} ({res.model_label})")
        print(f"  코멘트          : {res.comment}")
        print(f"  pass_score 비교 : {res.cleanliness} >= {pass_score} → "
              f"{'✅ 통과(잠금 해제)' if passed else '❌ 실패(잠금 유지/재청소)'}")

    clean_score = results[0][1]
    messy_score = results[1][1]
    print("\n" + "=" * 64)
    print(f"청결 점수 {clean_score}  vs  엉망 점수 {messy_score}  (차이 {clean_score - messy_score})")
    if clean_score - messy_score >= 20:
        print("=> 점수가 사진 내용에 따라 분명히 갈림. 진짜 채점 동작 확인 ✅")
        return 0
    print("=> 점수 차이가 작음. 프롬프트/모델/이미지 확인 필요 ⚠️")
    return 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass-score", type=int, default=80)
    args = ap.parse_args()
    rc = asyncio.run(run(args.pass_score))
    sys.exit(rc)


if __name__ == "__main__":
    main()
