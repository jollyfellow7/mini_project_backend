# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps.auth_deps import FamilyContext, get_current_parent_id, get_family_context
from domain.chungsora.chungsora_repository import get_chungsora_repo

router = APIRouter()


class ShopRewardBody(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    won: int = Field(ge=500, le=100000)


class ShopRewardPatchBody(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    won: int | None = Field(default=None, ge=500, le=100000)


class DailyQuestBody(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = ""


@router.get("/shop")
async def list_shop_rewards(ctx: FamilyContext = Depends(get_family_context)):
    repo = await get_chungsora_repo()
    return {"rewards": await repo.list_shop_rewards(ctx.parent_id)}


@router.post("/shop")
async def create_shop_reward(
    body: ShopRewardBody,
    parent_id: int = Depends(get_current_parent_id),
):
    repo = await get_chungsora_repo()
    rewards = await repo.create_shop_reward(parent_id, body.label, body.won)
    return {"rewards": rewards}


@router.patch("/shop/{reward_id}")
async def update_shop_reward(
    reward_id: int,
    body: ShopRewardPatchBody,
    parent_id: int = Depends(get_current_parent_id),
):
    repo = await get_chungsora_repo()
    rewards = await repo.update_shop_reward(parent_id, reward_id, body.label, body.won)
    return {"rewards": rewards}


@router.delete("/shop/{reward_id}")
async def delete_shop_reward(
    reward_id: int,
    parent_id: int = Depends(get_current_parent_id),
):
    repo = await get_chungsora_repo()
    rewards = await repo.delete_shop_reward(parent_id, reward_id)
    return {"rewards": rewards}


@router.get("/daily-quests")
async def list_daily_quests(ctx: FamilyContext = Depends(get_family_context)):
    repo = await get_chungsora_repo()
    return {"quests": await repo.list_daily_quests(ctx.parent_id)}


@router.post("/daily-quests")
async def create_daily_quest(
    body: DailyQuestBody,
    parent_id: int = Depends(get_current_parent_id),
):
    repo = await get_chungsora_repo()
    quests = await repo.create_daily_quest(parent_id, body.title, body.description)
    return {"quests": quests}


@router.delete("/daily-quests/{quest_id}")
async def delete_daily_quest(
    quest_id: int,
    parent_id: int = Depends(get_current_parent_id),
):
    repo = await get_chungsora_repo()
    quests = await repo.delete_daily_quest(parent_id, quest_id)
    return {"quests": quests}
