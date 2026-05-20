# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps.auth_deps import FamilyContext, get_current_parent_id, get_family_context
from domain.chungsora.chungsora_repository import get_chungsora_repo

router = APIRouter()


class PointsBody(BaseModel):
    amount: int = Field(ge=1, le=10000)
    label: str = Field(min_length=1, max_length=120)


class SpendBody(BaseModel):
    won: int = Field(ge=500, le=100000)
    label: str = Field(min_length=1, max_length=120)


@router.get("/balance")
async def get_balance(ctx: FamilyContext = Depends(get_family_context)):
    repo = await get_chungsora_repo()
    profile = await repo.get_parent_by_id(ctx.parent_id)
    return {"balance": profile["points_balance"] if profile else 0}


@router.post("/earn")
async def earn_points(body: PointsBody, ctx: FamilyContext = Depends(get_family_context)):
    repo = await get_chungsora_repo()
    return await repo.adjust_points(ctx.parent_id, body.amount, body.label, "earn")


@router.post("/spend")
async def spend_points(body: SpendBody, ctx: FamilyContext = Depends(get_family_context)):
    cost = max(1, body.won // 10)
    repo = await get_chungsora_repo()
    profile = await repo.get_parent_by_id(ctx.parent_id)
    if not profile or profile["points_balance"] < cost:
        raise HTTPException(status_code=400, detail="insufficient_points")
    return await repo.adjust_points(ctx.parent_id, -cost, body.label, "spend")
