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
