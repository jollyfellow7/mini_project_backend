# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps.auth_deps import get_current_parent_id
from core.jwt_utils import create_access_token
from domain.chungsora.chungsora_repository import get_chungsora_repo

router = APIRouter()


class LoginBody(BaseModel):
    login_id: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class SignupBody(BaseModel):
    login_id: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=4, max_length=128)
    display_name: str = Field(default="", max_length=120)


def _auth_payload(user: dict, profile: dict | None = None) -> dict:
    token = create_access_token({"sub": str(user["id"]), "login_id": user["login_id"]})
    return {
        "ok": True,
        "token": token,
        "id": user["id"],
        "login_id": user["login_id"],
        "display_name": user["display_name"],
        "onboard_done": profile["onboard_done"] if profile else False,
        "child_display_name": profile["child_display_name"] if profile else "자녀",
    }


@router.get("/me")
async def parent_me(parent_id: int = Depends(get_current_parent_id)):
    repo = await get_chungsora_repo()
    profile = await repo.sync_onboard_done_if_paired(parent_id)
    if not profile:
        profile = await repo.get_parent_by_id(parent_id)
    if not profile:
        raise HTTPException(status_code=404, detail="not_found")
    return {
        "id": profile["id"],
        "login_id": profile["login_id"],
        "display_name": profile["display_name"],
        "onboard_done": profile["onboard_done"],
        "child_display_name": profile["child_display_name"],
        "points_balance": profile["points_balance"],
        "base_clean_won": profile["base_clean_won"],
        "lock_time": profile["lock_time"],
        "lock_days": profile["lock_days"],
        "pass_score": profile["pass_score"],
        "notification_prefs": profile["notification_prefs"],
        "coach_character_id": profile.get("coach_character_id") or "jiu",
        "child_coach_character_id": profile.get("child_coach_character_id"),
        "token": create_access_token(
            {"sub": str(profile["id"]), "login_id": profile["login_id"]}
        ),
    }


@router.post("/login")
async def parent_login(body: LoginBody):
    repo = await get_chungsora_repo()
    user = await repo.verify_parent_login(body.login_id, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    profile = await repo.sync_onboard_done_if_paired(user["id"])
    if not profile:
        profile = await repo.get_parent_by_id(user["id"])
    return _auth_payload(user, profile)


@router.post("/signup")
async def parent_signup(body: SignupBody):
    repo = await get_chungsora_repo()
    try:
        user = await repo.create_parent_account(
            body.login_id, body.password, body.display_name
        )
    except ValueError as exc:
        if str(exc) == "duplicate_login_id":
            raise HTTPException(status_code=409, detail="duplicate_login_id") from exc
        raise
    profile = await repo.get_parent_by_id(user["id"])
    return _auth_payload(user, profile)
