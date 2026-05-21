# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from api.deps.auth_deps import get_current_parent_id
from domain.chungsora.chungsora_repository import get_chungsora_repo

router = APIRouter()


class VerifyBody(BaseModel):
    code: str = Field(min_length=4, max_length=8)


class IssueBody(BaseModel):
    child_display_name: str | None = Field(default=None, max_length=64)


class RefreshBody(BaseModel):
    device_id: str = Field(min_length=4, max_length=64)


@router.get("/status")
async def pair_code_status(
    code: str = Query(min_length=4, max_length=8),
    parent_id: int = Depends(get_current_parent_id),
):
    repo = await get_chungsora_repo()
    return await repo.get_pair_code_status(parent_id, code)


@router.post("/issue")
async def issue_pair_code(
    parent_id: int = Depends(get_current_parent_id),
    body: IssueBody | None = None,
):
    repo = await get_chungsora_repo()
    if body and body.child_display_name and body.child_display_name.strip():
        await repo.update_parent_profile(
            parent_id,
            {"child_display_name": body.child_display_name.strip()},
        )
    return await repo.issue_pair_code(parent_id)


@router.post("/verify")
async def verify_pair_code(body: VerifyBody):
    repo = await get_chungsora_repo()
    return await repo.verify_pair_code(body.code)


@router.post("/refresh")
async def refresh_child_token(body: RefreshBody):
    """기존 등록 기기 — 토큰만 재발급 (폰 교체·만료 시 코드 페어링과 별도)."""
    repo = await get_chungsora_repo()
    return await repo.refresh_child_device_token(body.device_id)
