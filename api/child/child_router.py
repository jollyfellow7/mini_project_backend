# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps.auth_deps import FamilyContext, get_family_context
from domain.chungsora.chungsora_repository import get_chungsora_repo

router = APIRouter()


class SubmitBody(BaseModel):
    label: str
    points: int


@router.get("/propose")
async def list_for_child(ctx: FamilyContext = Depends(get_family_context)):
    repo = await get_chungsora_repo()
    return {"threads": await repo.list_propose_threads(ctx.parent_id)}


@router.post("/propose")
async def submit_proposal(body: SubmitBody, ctx: FamilyContext = Depends(get_family_context)):
    repo = await get_chungsora_repo()
    return await repo.submit_proposal(ctx.parent_id, body.label, body.points)
