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
        prompt = (
            f"이 사진은 '{room_name}' 방입니다. 청소 게임용 '마수'를 JSON으로만 답하세요.\n"
            "monster_ids는 다음 중에서만 선택: "
            + ", ".join(sorted(_VALID_IDS))
            + ".\n"
            '{"monster_ids":["clutter_wyrm"],"pollution_level":55,"summary":"한국어 한 줄"}'
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
            pollution = max(0, min(100, int(data.get("pollution_level", 50))))
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
            f"'{room_name}' 청소 후 사진입니다. 청결도 0~100과 한국어 comment 한 문장.\n"
            'JSON만: {"cleanliness": 92, "comment": "훌륭합니다!"}'
        )
        try:
            raw, model_id = await gemini.generate_vision(
                image_bytes, "image/jpeg", prompt
            )
            data = gemini.parse_json_response(raw)
            cleanliness = max(0, min(100, int(data.get("cleanliness", 85))))
            comment = str(data.get("comment", "청소가 잘 되었습니다."))[:300]
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
            f"이미지는 아이 방 '{slot_label}' 구역의 깨끗한 baseline 기준 촬영입니다. "
            "AI가 이후 자녀 청소 결과와 비교할 학습 기준으로 쓸 수 있는지 평가하세요. "
            "방이 선명하게 보이고, 너무 어둡거나 흔들리거나 가려지지 않았는지 확인하세요. "
            'JSON만: {"quality_score": 85, "acceptable": true, "comment": "한국어 한 줄"} '
            "acceptable은 quality_score>=70일 때 true."
        )
        try:
            raw, model_id = await gemini.generate_vision(
                image_bytes, "image/jpeg", prompt
            )
            data = gemini.parse_json_response(raw)
            quality = max(0, min(100, int(data.get("quality_score", 0))))
            acceptable = bool(data.get("acceptable", quality >= 70))
            comment = str(data.get("comment", ""))[:300]
            return BaselineEvalResponse(
                quality_score=quality,
                acceptable=acceptable and quality >= 70,
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
            f"첫 번째 이미지: 부모가 등록한 '{slot_label}' 깨끗한 baseline 기준입니다.\n"
            f"두 번째 이미지: 자녀가 청소 후 촬영한 같은 '{slot_label}' 구역입니다.\n"
            "baseline과 비교해 얼마나 비슷하게 깨끗한지 0~100 cleanliness, 한국어 comment 한 문장.\n"
            'JSON만: {"cleanliness": 88, "comment": "..."}'
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
