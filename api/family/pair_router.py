# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.deps.auth_deps import get_current_parent_id
from domain.chungsora.chungsora_repository import get_chungsora_repo

router = APIRouter()


class VerifyBody(BaseModel):
    code: str = Field(min_length=4, max_length=8)


@router.post("/issue")
async def issue_pair_code(parent_id: int = Depends(get_current_parent_id)):
    repo = await get_chungsora_repo()
    return await repo.issue_pair_code(parent_id)


@router.post("/verify")
async def verify_pair_code(body: VerifyBody):
    repo = await get_chungsora_repo()
    return await repo.verify_pair_code(body.code)
