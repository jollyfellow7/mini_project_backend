# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from typing import Literal

from pydantic import BaseModel, Field

CoachCharacterId = Literal["jiu", "seoyeon", "hajun"]

from api.deps.auth_deps import FamilyContext, get_current_parent_id, get_family_context
from domain.chungsora.chungsora_repository import get_chungsora_repo

router = APIRouter()


class ProfileBody(BaseModel):
    onboard_done: bool | None = None
    child_display_name: str | None = None
    base_clean_won: int | None = None
    lock_time: str | None = None
    lock_days: str | None = None
    pass_score: int | None = Field(default=None, ge=50, le=100)
    allow_phone: bool | None = None
    allowlist: list[str] | None = None
    baseline_url: str | None = None
    baseline_urls: list[str | None] | None = None  # 슬롯별 baseline 사진 URL 목록
    baseline_verified: bool | None = None           # 베이스라인 촬영 완료 여부 (프론트 CaptureCoachBody에서 true로 저장)
    notification_prefs: dict | None = None
    coach_character_id: CoachCharacterId | None = None
    child_coach_character_id: CoachCharacterId | None = None


@router.get("/summary")
async def family_summary(ctx: FamilyContext = Depends(get_family_context)):
    repo = await get_chungsora_repo()
    return await repo.get_family_summary(ctx.parent_id)


@router.patch("/summary")
async def update_summary(
    body: ProfileBody,
    parent_id: int = Depends(get_current_parent_id),
):
    """프론트 updateFamilyProfile()이 호출하는 엔드포인트 (PATCH /family/summary)."""
    repo = await get_chungsora_repo()
    return await repo.update_parent_profile(
        parent_id, body.model_dump(exclude_none=True)
    )


@router.patch("/profile")
async def update_profile(
    body: ProfileBody,
    parent_id: int = Depends(get_current_parent_id),
):
    """하위 호환 유지."""
    repo = await get_chungsora_repo()
    return await repo.update_parent_profile(
        parent_id, body.model_dump(exclude_none=True)
    )
