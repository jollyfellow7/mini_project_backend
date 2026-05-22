# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List

from domain.tts.tts_dto import (
    PersonaListResponse,
    PersonaMeta,
    ScriptResponse,
    ScriptSegment,
)

# ──────────────────────────────────────────────
# 페르소나 메타데이터
# ──────────────────────────────────────────────

_PERSONAS: List[PersonaMeta] = [
    PersonaMeta(
        id="mate",
        name="촬영 메이트",
        emoji="📱",
        tone="편하고 리액션 좋은 또래. 템포 보통~약간 빠름.",
        supports_informal=True,
        recommended_ages=[10, 11, 12],
    ),
    PersonaMeta(
        id="director",
        name="촬영 디렉터",
        emoji="🎬",
        tone="에너지는 있되 과장 칭찬은 줄임. 한 줄 이유 + 다음 지시.",
        supports_informal=False,
        recommended_ages=[13, 14, 15, 16, 17, 18, 19],
    ),
    PersonaMeta(
        id="quest",
        name="촬영 퀘스트 가이드",
        emoji="🎮",
        tone="게임 퀘스트처럼 짧고 명확. 대괄호 구간은 SFX만 재생.",
        supports_informal=False,
        recommended_ages=[10, 11, 12, 16, 17, 18, 19],
    ),
    PersonaMeta(
        id="coach",
        name="코치 / 연습실 선배",
        emoji="🏃",
        tone="당당하고 짧은 지시. 유아 톤 금지.",
        supports_informal=True,
        recommended_ages=[10, 11, 12, 13, 14, 15],
    ),
    PersonaMeta(
        id="mentor",
        name="편한 멘토",
        emoji="☕",
        tone="느리고 부드럽게. 긴장 완화형.",
        supports_informal=False,
        recommended_ages=[13, 14, 15, 16, 17, 18, 19],
    ),
]

_PERSONA_INDEX = {p.id: p for p in _PERSONAS}

# ──────────────────────────────────────────────
# 스크립트 세그먼트 정의
# 규칙:
#   - type="tts"  : text 필드에 읽을 문장, pause_after_ms로 뒤 쉬기
#   - type="sfx"  : sfx_key="ding" (대괄호 구간), pause_after_ms=300
#   - (1초 쉬고)  → 직전 세그먼트 pause_after_ms=1000
#   - (0.5초 쉬고) → 직전 세그먼트 pause_after_ms=500
# ──────────────────────────────────────────────

def _t(text: str, pause: int = 0) -> ScriptSegment:
    return ScriptSegment(type="tts", text=text, pause_after_ms=pause)


def _sfx(pause: int = 300) -> ScriptSegment:
    return ScriptSegment(type="sfx", sfx_key="ding", pause_after_ms=pause)


_SCRIPTS: dict[str, dict[str, List[ScriptSegment]]] = {
    # ① 촬영 메이트
    "mate": {
        "formal": [
            _t("지금 각도 괜찮아요."),
            _t("화면 가운데로 살짝만 들어와 주세요."),
            _t("부담 없이 평소 표정이면 돼요."),
            _t("준비되면 고개만 살짝 들고,", pause=1000),
            _t("자, 찍을게요."),
            _t("셋, 둘, 하나, 끝."),
            _t("이번 거 쓸 만해요."),
        ],
        "informal": [
            _t("지금 각도 괜찮아."),
            _t("화면 가운데로 살짝만 들어와 봐."),
            _t("부담 없이 평소 표정이면 돼."),
            _t("준비되면 고개만 살짝 들고,", pause=1000),
            _t("자, 찍는다."),
            _t("셋, 둘, 하나, 끝."),
            _t("이번 거 쓸 만해."),
        ],
    },
    # ② 촬영 디렉터 (반말 없음)
    "director": {
        "formal": [
            _t("지금 얼굴 라이팅 들어옵니다.", pause=1000),
            _t("그 포즈 그대로 유지하세요."),
            _t("눈은 렌즈 쪽만 보시면 됩니다."),
            _t("어깨는 고정해 주세요."),
            _t("자, 레디,", pause=500),
            _t("이번 컷 갑니다."),
            _t("셋, 둘, 하나, 좋아요."),
            _t("방금 거 프레임 안정적이에요."),
        ],
    },
    # ③ 촬영 퀘스트 가이드 — [대괄호] → SFX, 반말 없음
    "quest": {
        "formal": [
            _sfx(),                                                          # [촬영 퀘스트 시작]
            _t("촬영 퀘스트를 시작합니다."),
            _t("목표는 화면 중앙 정렬, 표정은 자연스럽게 유지입니다."),
            _sfx(),                                                          # [진행]
            _t("시선을 렌즈에 맞춰 주세요."),
            _sfx(),                                                          # [경고]
            _t("움직이면 다시 찍을 수 있어요."),
            _t("셋, 둘, 하나,"),
            _sfx(),                                                          # [완료]
            _t("한 컷 클리어입니다. 다음으로 넘어갈까요?"),
        ],
    },
    # ④ 코치 / 연습실 선배
    "coach": {
        "formal": [
            _t("좋아요, 자세는 지금이 딱입니다."),
            _t("시선만 렌즈로 맞춰 주세요."),
            _t("호흡 한 번만 고르고,", pause=1000),
            _t("움직이지 말고, 마지막 카운트 갑니다."),
            _t("셋, 둘, 하나, 끝."),
            _t("수고하셨어요, 이번 컷 깔끔합니다."),
        ],
        "informal": [
            _t("좋아, 자세는 지금이 딱이야."),
            _t("시선만 렌즈로."),
            _t("호흡 한 번만 고르고,", pause=1000),
            _t("움직이지 말고, 마지막 카운트 간다."),
            _t("셋, 둘, 하나, 끝."),
            _t("수고했어, 이번 컷 깔끔해."),
        ],
    },
    # ⑤ 편한 멘토 (반말 없음)
    "mentor": {
        "formal": [
            _t("급하게 안 하셔도 돼요."),
            _t("지금 위치 그대로 괜찮아요."),
            _t("카메라만 편하게 보시면 됩니다."),
            _t("표정은 억지로 웃지 않아도 돼요."),
            _t("준비되면 살짝만 고개 들고,", pause=1000),
            _t("하나, 둘, 셋, 잘했어요."),
            _t("이번엔 자연스러워요."),
        ],
    },
}


# ──────────────────────────────────────────────
# 공개 함수
# ──────────────────────────────────────────────

def get_personas() -> PersonaListResponse:
    return PersonaListResponse(personas=_PERSONAS)


def get_script(persona_id: str, informal_mode: bool) -> ScriptResponse | None:
    persona = _PERSONA_INDEX.get(persona_id)
    if persona is None:
        return None

    script_map = _SCRIPTS.get(persona_id, {})

    # 반말 미지원 페르소나는 informal_mode=True여도 존댓말 폴백
    use_informal = informal_mode and persona.supports_informal
    key = "informal" if use_informal else "formal"
    segments = script_map.get(key, script_map.get("formal", []))

    return ScriptResponse(
        persona_id=persona_id,
        informal_mode=use_informal,
        segments=segments,
    )
