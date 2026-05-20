# -*- coding: utf-8 -*-
from dataclasses import dataclass

from fastapi import Header, HTTPException

from core.jwt_utils import decode_access_token


def get_bearer_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:].strip() or None


@dataclass
class FamilyContext:
    parent_id: int
    is_parent: bool
    device_id: str | None = None


async def get_current_parent_id(authorization: str | None = Header(default=None)) -> int:
    token = get_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="unauthorized")
    payload = decode_access_token(token)
    if not payload or payload.get("typ") == "child" or "sub" not in payload:
        raise HTTPException(status_code=401, detail="unauthorized")
    return int(payload["sub"])


async def get_family_context(
    authorization: str | None = Header(default=None),
) -> FamilyContext:
    token = get_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="unauthorized")
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="unauthorized")
    if payload.get("typ") == "child":
        if "pid" not in payload or "sub" not in payload:
            raise HTTPException(status_code=401, detail="unauthorized")
        return FamilyContext(
            parent_id=int(payload["pid"]),
            device_id=str(payload["sub"]),
            is_parent=False,
        )
    if "sub" in payload:
        return FamilyContext(parent_id=int(payload["sub"]), is_parent=True)
    raise HTTPException(status_code=401, detail="unauthorized")
