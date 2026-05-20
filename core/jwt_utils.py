# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from core.config import settings

_ALGORITHM = "HS256"
_EXPIRE_DAYS = 7


def create_access_token(payload: dict[str, Any]) -> str:
    secret = settings.JWT_SECRET or "dev-insecure-change-me"
    data = {
        **payload,
        "exp": datetime.now(timezone.utc) + timedelta(days=_EXPIRE_DAYS),
    }
    return jwt.encode(data, secret, algorithm=_ALGORITHM)


def create_child_token(device_id: str, parent_id: int) -> str:
    return create_access_token(
        {"sub": device_id, "pid": str(parent_id), "typ": "child"}
    )


def decode_access_token(token: str) -> dict[str, Any] | None:
    secret = settings.JWT_SECRET or "dev-insecure-change-me"
    try:
        return jwt.decode(token, secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
