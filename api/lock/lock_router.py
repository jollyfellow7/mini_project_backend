# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.deps.auth_deps import FamilyContext, get_current_parent_id, get_family_context
from domain.chungsora.chungsora_repository import get_chungsora_repo

router = APIRouter()


class LockPolicyBody(BaseModel):
    lock_time: str | None = None
    lock_days: str | None = None
    pass_score: int | None = Field(default=None, ge=50, le=100)
    allow_phone: bool | None = None
    allowlist: list[str] | None = None


@router.get("/policy")
async def get_lock_policy(ctx: FamilyContext = Depends(get_family_context)):
    repo = await get_chungsora_repo()
    return await repo.get_lock_policy(ctx.parent_id)


@router.put("/policy")
async def put_lock_policy(
    body: LockPolicyBody,
    parent_id: int = Depends(get_current_parent_id),
):
    repo = await get_chungsora_repo()
    payload = body.model_dump(exclude_none=True)
    return await repo.put_lock_policy(parent_id, payload)
