# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from api.deps.auth_deps import FamilyContext, get_current_parent_id, get_family_context
from domain.chungsora.chungsora_repository import get_chungsora_repo

router = APIRouter()


class PresetBody(BaseModel):
    phrase: str = Field(min_length=1, max_length=40)


@router.get("")
async def list_presets(ctx: FamilyContext = Depends(get_family_context)):
    repo = await get_chungsora_repo()
    return {"presets": await repo.list_presets(ctx.parent_id)}


@router.post("")
async def add_preset(body: PresetBody, parent_id: int = Depends(get_current_parent_id)):
    repo = await get_chungsora_repo()
    return {"presets": await repo.add_preset(parent_id, body.phrase)}


@router.delete("")
async def delete_preset(
    phrase: str = Query(..., min_length=1, max_length=40),
    parent_id: int = Depends(get_current_parent_id),
):
    repo = await get_chungsora_repo()
    return {"presets": await repo.delete_preset(parent_id, phrase)}
