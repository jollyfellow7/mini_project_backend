# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.deps.auth_deps import FamilyContext, get_current_parent_id, get_family_context
from domain.chungsora.chungsora_repository import get_chungsora_repo

router = APIRouter()

WON_PER_P = 10


class RejectBody(BaseModel):
    reason: str = ""


class SubmitBody(BaseModel):
    label: str
    points: int


@router.get("/propose")
async def list_for_parent(parent_id: int = Depends(get_current_parent_id)):
    repo = await get_chungsora_repo()
    return {"threads": await repo.list_propose_threads(parent_id)}


@router.post("/propose/{thread_id}/accept")
async def accept_proposal(thread_id: str, parent_id: int = Depends(get_current_parent_id)):
    repo = await get_chungsora_repo()
    return await repo.accept_proposal(parent_id, thread_id)


@router.post("/propose/{thread_id}/reject")
async def reject_proposal(
    thread_id: str,
    body: RejectBody,
    parent_id: int = Depends(get_current_parent_id),
):
    repo = await get_chungsora_repo()
    return await repo.reject_proposal(parent_id, thread_id, body.reason)
