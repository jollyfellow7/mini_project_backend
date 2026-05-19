# -*- coding: utf-8 -*-
"""Cleaning service — Gemini API only."""
from __future__ import annotations

import logging
from typing import Any, List

from domain.cleaning import cleaning_gemini_adapter as gemini
from domain.cleaning.cleaning_dto import (
    AiInfoResponse,
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


def _fallback_scan(room_name: str) -> ScanResponse:
    t = _TEMPLATE_MAP["clutter_wyrm"]
    return ScanResponse(
        monsters=[DetectedMonster(
            id=t["id"], name=t["name"], grade=t["grade"], location=room_name,
            icon=t["icon"], ability=t["ability"], ability_desc=t["ability_desc"],
            exp=t["exp"], gold=t["gold"],
        )],
        pollution_level=40,
        summary="AI 연결 실패. 기본 마수가 소환되었습니다.",
        model_id="fallback",
        model_label=format_model_label("fallback"),
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
            return _fallback_scan(room_name)

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
            return VerifyResponse(
                cleanliness=85,
                comment="AI 채점을 사용할 수 없어 기본 점수를 적용했습니다.",
                model_id="fallback",
                model_label=format_model_label("fallback"),
            )

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
            return ChatResponse(
                reply="AI 코치에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.",
                model_id="fallback",
                model_label=format_model_label("fallback"),
            )


_service = CleaningService()


async def get_ai_info() -> AiInfoResponse:
    return await _service.get_ai_info()


async def scan_room(image_bytes: bytes, room_name: str) -> ScanResponse:
    return await _service.scan_room(image_bytes, room_name)


async def verify_cleanliness(image_bytes: bytes, room_name: str) -> VerifyResponse:
    return await _service.verify_cleanliness(image_bytes, room_name)


async def coach_chat(body: dict[str, Any]) -> ChatResponse:
    return await _service.coach_chat(body)
