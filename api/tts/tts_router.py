# -*- coding: utf-8 -*-
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.deps.auth_deps import FamilyContext, get_family_context
from domain.tts import tts_service
from domain.tts.tts_dto import (
    PersonaHistoryResponse,
    PersonaListResponse,
    PersonaUpdateRequest,
    PersonaUpdateResponse,
    ScriptRequest,
    ScriptResponse,
)
from domain.chungsora.chungsora_repository import (
    COACH_CHARACTER_IDS,
    get_chungsora_repo,
)

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


@router.patch("/persona", response_model=PersonaUpdateResponse)
async def update_persona(
    body: PersonaUpdateRequest,
    ctx: FamilyContext = Depends(get_family_context),
) -> PersonaUpdateResponse:
    """안내 친구(페르소나) 변경. 부모면 family 기본, 자녀면 자녀 오버라이드.

    자녀 토큰도 허용(get_family_context) → 자녀 변경이 Neon 에 저장되고
    변경 이력이 기록되어 부모 알림으로 이어진다.
    """
    if body.persona_id not in COACH_CHARACTER_IDS:
        raise HTTPException(status_code=404, detail="persona_not_found")
    repo = await get_chungsora_repo()
    return await repo.update_persona(
        ctx.parent_id, ctx.is_parent, body.persona_id, body.informal_mode
    )


@router.get("/persona-history", response_model=PersonaHistoryResponse)
async def persona_history(
    ctx: FamilyContext = Depends(get_family_context),
) -> PersonaHistoryResponse:
    repo = await get_chungsora_repo()
    return await repo.get_persona_history(ctx.parent_id)


@router.post("/persona-history/seen", response_model=PersonaHistoryResponse)
async def persona_history_seen(
    ctx: FamilyContext = Depends(get_family_context),
) -> PersonaHistoryResponse:
    """부모가 변경 알림을 확인 → unseen 플래그 해제."""
    repo = await get_chungsora_repo()
    await repo.mark_persona_history_seen(ctx.parent_id)
    return await repo.get_persona_history(ctx.parent_id)
