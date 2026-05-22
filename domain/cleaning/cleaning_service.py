# -*- coding: utf-8 -*-
"""Cleaning service — Gemini API only."""
from __future__ import annotations

import logging
from typing import Any, List

from domain.cleaning import cleaning_gemini_adapter as gemini
from domain.cleaning.cleaning_dto import (
    AiInfoResponse,
    BaselineEvalResponse,
    ChatResponse,
    DetectedMonster,
    ScanResponse,
    VerifyResponse,
)
from domain.cleaning.cleaning_model_labels import format_model_label
from core.cleaning_gemini_models import CHAT_MODEL_ORDER, VISION_MODEL_ORDER

logger = logging.getLogger(__name__)

_MONSTER_TEMPLATES = [
    {"id": "dust_spirit", "name": "먼지 정령", "grade": "E", "icon": "🌫",
     "ability": "분진 공격", "ability_desc": "방치할수록 강해진다", "exp": 10, "gold": 5},
    {"id": "mold_beast", "name": "곰팡이 수인", "grade": "C", "icon": "🍄",
     "ability": "포자 방출", "ability_desc": "습도 높을수록 증식", "exp": 30, "gold": 15},
    {"id": "grease_golem", "name": "기름 골렘", "grade": "B", "icon": "🛢",
     "ability": "접착 슬라임", "ability_desc": "세제 없이는 처치 불가", "exp": 50, "gold": 25},
    {"id": "clutter_wyrm", "name": "잡동사니 와이번", "grade": "D", "icon": "📦",
     "ability": "물량 공세", "ability_desc": "물건이 많을수록 강화", "exp": 20, "gold": 10},
    {"id": "odor_shade", "name": "악취 망령", "grade": "C", "icon": "💨",
     "ability": "독기 발산", "ability_desc": "환기로 약화", "exp": 25, "gold": 12},
]
_TEMPLATE_MAP = {t["id"]: t for t in _MONSTER_TEMPLATES}
_VALID_IDS = set(_TEMPLATE_MAP.keys())


def _monster_from_id(mid: str, location: str) -> DetectedMonster:
    t = _TEMPLATE_MAP.get(mid, _TEMPLATE_MAP["clutter_wyrm"])
    return DetectedMonster(
        id=t["id"], name=t["name"], grade=t["grade"], location=location[:80],
        icon=t["icon"], ability=t["ability"], ability_desc=t["ability_desc"],
        exp=t["exp"], gold=t["gold"],
    )


class CleaningService:
    async def get_ai_info(self) -> AiInfoResponse:
        vision = VISION_MODEL_ORDER[0]
        chat = CHAT_MODEL_ORDER[0]
        return AiInfoResponse(
            vision_model=vision,
            vision_label=format_model_label(vision),
            chat_model=chat,
            chat_label=format_model_label(chat),
        )

    async def scan_room(self, image_bytes: bytes, room_name: str) -> ScanResponse:
        valid_ids_str = ", ".join(sorted(_VALID_IDS))
        prompt = (
            f"이 사진은 아이 방의 '{room_name}' 구역입니다.\n"
            "사진을 꼼꼼히 분석하여 실제로 눈에 보이는 오염·정리 상태만 근거로 판단하세요.\n\n"
            "각 monster_id 선택 기준:\n"
            "- dust_spirit : 먼지 쌓임, 오래된 얼룩, 방치된 표면\n"
            "- mold_beast  : 곰팡이·습기 흔적, 변색\n"
            "- grease_golem: 기름때, 끈적한 오염, 음식 흔적\n"
            "- clutter_wyrm: 바닥·책상·선반에 물건이 어지럽게 쌓임\n"
            "- odor_shade  : 쓰레기통 넘침, 음식물 방치, 환기 필요 징후\n\n"
            f"monster_ids: 위 기준 중 사진에서 실제 확인된 것만 선택 ({valid_ids_str})\n"
            "pollution_level: 0(완전 깨끗)~100(매우 지저분) 정수\n"
            "  - 바닥·책상이 깔끔하고 먼지 없음 → 5~25\n"
            "  - 물건 조금 어지러움, 약간 먼지 → 30~55\n"
            "  - 물건 많이 쌓임·뚜렷한 오염 → 60~80\n"
            "  - 심각하게 지저분함 → 85~100\n"
            "summary: 현재 상태를 한국어 한 문장으로 구체적으로 묘사.\n\n"
            "JSON만 출력:\n"
            '{"monster_ids":["clutter_wyrm"],"pollution_level":40,"summary":"책상 위에 책과 물건이 쌓여 있어요."}'
        )
        try:
            raw, model_id = await gemini.generate_vision(
                image_bytes, "image/jpeg", prompt
            )
            data = gemini.parse_json_response(raw)
            ids = [x for x in data.get("monster_ids", []) if x in _VALID_IDS][:5]
            if not ids:
                ids = ["clutter_wyrm"]
            monsters = [_monster_from_id(i, room_name) for i in ids]
            pollution = max(0, min(100, int(data.get("pollution_level", 40))))
            summary = str(data.get("summary", f"{room_name} 스캔 완료."))[:200]
            return ScanResponse(
                monsters=monsters,
                pollution_level=pollution,
                summary=summary,
                model_id=model_id,
                model_label=format_model_label(model_id),
            )
        except Exception as e:
            logger.warning("[scan] Gemini failed: %s", e)
            raise RuntimeError("scan_failed") from e

    async def verify_cleanliness(self, image_bytes: bytes, room_name: str) -> VerifyResponse:
        prompt = (
            f"이 사진은 아이가 '{room_name}' 구역을 청소한 뒤 촬영한 결과물입니다.\n"
            "실제로 보이는 상태만 근거로 청결도를 평가하세요.\n\n"
            "채점 기준:\n"
            "- 바닥·책상·선반이 정리되고 먼지가 없으면 85~100\n"
            "- 대체로 깨끗하나 작은 정리 미흡이 있으면 65~84\n"
            "- 부분적으로 청소됐지만 여전히 어수선하면 40~64\n"
            "- 거의 청소가 안 된 상태면 0~39\n\n"
            "comment: 잘한 점과 아쉬운 점을 한국어 한 문장으로.\n\n"
            "JSON만 출력:\n"
            '{"cleanliness": 88, "comment": "바닥과 책상이 깔끔하게 정리되었어요!"}'
        )
        try:
            raw, model_id = await gemini.generate_vision(
                image_bytes, "image/jpeg", prompt
            )
            data = gemini.parse_json_response(raw)
            cleanliness = max(0, min(100, int(data.get("cleanliness", 70))))
            comment = str(data.get("comment", "청소 결과를 확인했습니다."))[:300]
            return VerifyResponse(
                cleanliness=cleanliness,
                comment=comment,
                model_id=model_id,
                model_label=format_model_label(model_id),
            )
        except Exception as e:
            logger.warning("[verify] Gemini failed: %s", e)
            raise RuntimeError("verify_failed") from e

    async def evaluate_baseline(self, image_bytes: bytes, slot_label: str) -> BaselineEvalResponse:
        prompt = (
            f"이 이미지는 부모가 등록한 아이 방 '{slot_label}' 구역의 baseline 기준 사진입니다.\n"
            "이후 자녀 청소 결과와 비교하는 데 쓸 수 있는 품질인지 평가하세요.\n\n"
            "합격 기준 (quality_score >= 50이면 acceptable: true):\n"
            "- 사진이 선명하고 흔들리지 않음\n"
            "- 구역이 화면의 50% 이상 차지함\n"
            "- 극단적으로 어둡거나 역광이 아님\n"
            "- 손이나 물체로 대부분 가려지지 않음\n\n"
            "comment: 한국어 한 문장으로 품질 평가 결과 설명.\n\n"
            "JSON만 출력:\n"
            '{"quality_score": 80, "acceptable": true, "comment": "선명하고 구도가 좋습니다."}'
        )
        try:
            raw, model_id = await gemini.generate_vision(
                image_bytes, "image/jpeg", prompt
            )
            data = gemini.parse_json_response(raw)
            quality = max(0, min(100, int(data.get("quality_score", 0))))
            # 합격 기준을 50점으로 낮춰 실사용 환경(핸드폰 촬영)에서 통과율 향상
            threshold = 50
            acceptable = bool(data.get("acceptable", quality >= threshold)) and quality >= threshold
            comment = str(data.get("comment", ""))[:300]
            return BaselineEvalResponse(
                quality_score=quality,
                acceptable=acceptable,
                comment=comment or f"{slot_label} baseline 품질 {quality}점",
                model_id=model_id,
                model_label=format_model_label(model_id),
            )
        except Exception as e:
            logger.warning("[baseline-eval] Gemini failed: %s", e)
            raise RuntimeError("baseline_eval_failed") from e

    async def compare_with_baseline(
        self, baseline_bytes: bytes, after_bytes: bytes, slot_label: str
    ) -> VerifyResponse:
        prompt = (
            f"두 장의 사진을 비교하세요.\n"
            f"첫 번째: 부모가 등록한 '{slot_label}' 구역의 깨끗한 baseline 기준 사진.\n"
            f"두 번째: 자녀가 청소 후 촬영한 같은 '{slot_label}' 구역 사진.\n\n"
            "비교 시 주목할 요소:\n"
            "- 바닥·책상·선반의 정리 상태\n"
            "- 물건 배치가 baseline과 얼마나 유사한지\n"
            "- 먼지·오염·쓰레기 제거 여부\n\n"
            "cleanliness: baseline 대비 청결도 0~100 정수\n"
            "  - baseline과 거의 동일하게 깨끗함 → 85~100\n"
            "  - 대체로 비슷하나 소소한 차이 → 65~84\n"
            "  - 절반 정도 달성 → 40~64\n"
            "  - baseline보다 많이 부족 → 0~39\n"
            "comment: 한국어 한 문장으로 구체적인 비교 결과 설명.\n\n"
            "JSON만 출력:\n"
            '{"cleanliness": 85, "comment": "책상 정리가 잘 됐고 바닥도 깨끗해요."}'
        )
        try:
            raw, model_id = await gemini.generate_vision_pair(
                baseline_bytes, after_bytes, prompt
            )
            data = gemini.parse_json_response(raw)
            cleanliness = max(0, min(100, int(data.get("cleanliness", 0))))
            comment = str(data.get("comment", "비교 채점 완료."))[:300]
            return VerifyResponse(
                cleanliness=cleanliness,
                comment=comment,
                model_id=model_id,
                model_label=format_model_label(model_id),
            )
        except Exception as e:
            logger.warning("[compare-baseline] Gemini failed: %s", e)
            raise RuntimeError("compare_baseline_failed") from e

    async def coach_chat(self, body: dict[str, Any]) -> ChatResponse:
        history = body.get("history") or []
        hist_lines = "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history[-6:]
        )
        prompt = (
            f"당신은 '{body.get('room_name', '방')}' 청소 코치입니다. "
            f"오염도 {body.get('pollution_level', 0)}, 남은 마수: {body.get('monsters_remaining', [])}.\n"
            f"{hist_lines}\n"
            f"사용자: {body.get('user_message', '')}\n"
            "한국어로 2~4문장만 답하세요."
        )
        try:
            reply, model_id = await gemini.generate_text(prompt)
            return ChatResponse(
                reply=reply[:2000],
                model_id=model_id,
                model_label=format_model_label(model_id),
            )
        except Exception as e:
            logger.warning("[chat] Gemini failed: %s", e)
            raise RuntimeError("chat_failed") from e


_service = CleaningService()


async def get_ai_info() -> AiInfoResponse:
    return await _service.get_ai_info()


async def scan_room(image_bytes: bytes, room_name: str) -> ScanResponse:
    return await _service.scan_room(image_bytes, room_name)


async def verify_cleanliness(image_bytes: bytes, room_name: str) -> VerifyResponse:
    return await _service.verify_cleanliness(image_bytes, room_name)


async def evaluate_baseline(image_bytes: bytes, slot_label: str) -> BaselineEvalResponse:
    return await _service.evaluate_baseline(image_bytes, slot_label)


async def compare_with_baseline(
    baseline_bytes: bytes, after_bytes: bytes, slot_label: str
) -> VerifyResponse:
    return await _service.compare_with_baseline(baseline_bytes, after_bytes, slot_label)


async def coach_chat(body: dict[str, Any]) -> ChatResponse:
    return await _service.coach_chat(body)


_service = CleaningService()


async def get_ai_info() -> AiInfoResponse:
    return await _service.get_ai_info()


async def scan_room(image_bytes: bytes, room_name: str) -> ScanResponse:
    return await _service.scan_room(image_bytes, room_name)


async def verify_cleanliness(image_bytes: bytes, room_name: str) -> VerifyResponse:
    return await _service.verify_cleanliness(image_bytes, room_name)


async def evaluate_baseline(image_bytes: bytes, slot_label: str) -> BaselineEvalResponse:
    return await _service.evaluate_baseline(image_bytes, slot_label)


async def compare_with_baseline(
    baseline_bytes: bytes, after_bytes: bytes, slot_label: str
) -> VerifyResponse:
    return await _service.compare_with_baseline(baseline_bytes, after_bytes, slot_label)


async def coach_chat(body: dict[str, Any]) -> ChatResponse:
    return await _service.coach_chat(body)
