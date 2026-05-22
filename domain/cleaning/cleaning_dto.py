# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List

from pydantic import BaseModel


class DetectedMonster(BaseModel):
    id: str
    name: str
    grade: str
    location: str
    icon: str
    ability: str
    ability_desc: str
    exp: int
    gold: int


class ScanResponse(BaseModel):
    monsters: List[DetectedMonster]
    pollution_level: int
    summary: str
    model_id: str = ""
    model_label: str = ""


class VerifyResponse(BaseModel):
    cleanliness: int
    comment: str
    model_id: str = ""
    model_label: str = ""


class CompareBaselineResponse(VerifyResponse):
    """compare-baseline 전용 응답.

    기존 VerifyResponse 의 cleanliness/comment/model_* 를 그대로 포함하고(하위호환),
    부모가 정한 통과 기준(pass_score)과의 비교 결과를 서버에서 함께 내려준다.
    프론트는 추가 필드를 무시해도 동작하지만, passed 를 신뢰해 잠금 해제를 결정할 수 있다.
    """

    pass_score: int = 70          # 적용된 부모 기준 점수
    passed: bool = False          # cleanliness >= pass_score 여부 (서버 판정)
    pass_score_source: str = "default"  # "policy" | "override" | "default"


class BaselineEvalResponse(BaseModel):
    quality_score: int
    acceptable: bool
    comment: str
    model_id: str = ""
    model_label: str = ""


class AiInfoResponse(BaseModel):
    vision_model: str
    vision_label: str
    chat_model: str
    chat_label: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    room_id: str
    room_name: str
    pollution_level: int
    monsters_remaining: List[str]
    history: List[ChatMessage]
    user_message: str


class ChatResponse(BaseModel):
    reply: str
    model_id: str = ""
    model_label: str = ""


class MemoryRequest(BaseModel):
    room_id: str
    room_name: str
    cleanliness: int
    monsters_cleared: List[str]
    duration_seconds: int
    exp_gained: int
    gold_gained: int


class MemoryResponse(BaseModel):
    id: str
    saved_at: str
