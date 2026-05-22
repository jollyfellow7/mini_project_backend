# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel


class ScriptSegment(BaseModel):
    type: Literal["tts", "sfx"]
    text: Optional[str] = None
    sfx_key: Optional[str] = None
    pause_after_ms: int = 0


class PersonaMeta(BaseModel):
    id: str
    name: str
    emoji: str
    tone: str
    supports_informal: bool
    recommended_ages: List[int]


class PersonaListResponse(BaseModel):
    personas: List[PersonaMeta]


class ScriptRequest(BaseModel):
    persona_id: str
    informal_mode: bool = False


class ScriptResponse(BaseModel):
    persona_id: str
    informal_mode: bool
    segments: List[ScriptSegment]


class PersonaUpdateRequest(BaseModel):
    persona_id: str
    informal_mode: bool = False


class PersonaUpdateResponse(BaseModel):
    scope: str
    persona_id: str
    informal_mode: bool
    effective_coach_character_id: Optional[str] = None
    effective_informal_mode: Optional[bool] = None


class PersonaHistoryItem(BaseModel):
    id: int
    changed_by: str
    scope: str
    from_persona: Optional[str] = None
    to_persona: str
    from_informal: Optional[bool] = None
    to_informal: bool
    parent_seen: bool
    at: str


class PersonaHistoryResponse(BaseModel):
    items: List[PersonaHistoryItem]
    unseen_count: int
