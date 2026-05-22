# -*- coding: utf-8 -*-
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from domain.tts import tts_service
from domain.tts.tts_dto import PersonaListResponse, ScriptRequest, ScriptResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/personas", response_model=PersonaListResponse)
async def list_personas() -> PersonaListResponse:
    return tts_service.get_personas()


@router.post("/script", response_model=ScriptResponse)
async def get_script(body: ScriptRequest) -> ScriptResponse:
    result = tts_service.get_script(body.persona_id, body.informal_mode)
    if result is None:
        raise HTTPException(status_code=404, detail="persona_not_found")
    return result
