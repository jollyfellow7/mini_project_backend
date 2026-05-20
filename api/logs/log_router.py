# -*- coding: utf-8 -*-
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from api.deps.auth_deps import FamilyContext, get_family_context
from domain.chungsora.chungsora_repository import get_chungsora_repo

router = APIRouter()

_UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads" / "logs"
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_YEAR_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


class MessageBody(BaseModel):
    role: str = Field(pattern="^(parent|child)$")
    text: str
    badge: str | None = None


class LogMetaBody(BaseModel):
    score: int | None = None
    streak_days: int | None = None


@router.get("/calendar/{year_month}")
async def get_calendar(year_month: str, ctx: FamilyContext = Depends(get_family_context)):
    if not _YEAR_MONTH_RE.match(year_month):
        raise HTTPException(status_code=400, detail="invalid year_month")
    repo = await get_chungsora_repo()
    return await repo.calendar(ctx.parent_id, year_month)


@router.get("/{date}")
async def get_log(date: str, ctx: FamilyContext = Depends(get_family_context)):
    if not _DATE_RE.match(date):
        raise HTTPException(status_code=400, detail="invalid date")
    repo = await get_chungsora_repo()
    return await repo.get_log(ctx.parent_id, date)


@router.patch("/{date}")
async def patch_log(
    date: str,
    body: LogMetaBody,
    ctx: FamilyContext = Depends(get_family_context),
):
    if not _DATE_RE.match(date):
        raise HTTPException(status_code=400, detail="invalid date")
    repo = await get_chungsora_repo()
    return await repo.patch_log(ctx.parent_id, date, body.score, body.streak_days)


@router.get("/{date}/messages")
async def get_messages(date: str, ctx: FamilyContext = Depends(get_family_context)):
    if not _DATE_RE.match(date):
        raise HTTPException(status_code=400, detail="invalid date")
    repo = await get_chungsora_repo()
    log = await repo.get_log(ctx.parent_id, date)
    return {"date": date, "messages": log["messages"]}


@router.post("/{date}/messages")
async def post_message(
    date: str,
    body: MessageBody,
    ctx: FamilyContext = Depends(get_family_context),
):
    if not _DATE_RE.match(date):
        raise HTTPException(status_code=400, detail="invalid date")
    repo = await get_chungsora_repo()
    msg = await repo.add_message(ctx.parent_id, date, body.role, body.text, body.badge)
    return {"message": msg}


@router.post("/{date}/photos")
async def upload_photo(
    date: str,
    ctx: FamilyContext = Depends(get_family_context),
    phase: str = Query(..., pattern="^(before|after|baseline)$"),
    slot: int | None = Query(default=None, ge=0, le=2),
    file: UploadFile = File(...),
):
    if not _DATE_RE.match(date):
        raise HTTPException(status_code=400, detail="invalid date")

    suffix = Path(file.filename or "photo.jpg").suffix.lower()
    if suffix not in (".jpg", ".jpeg", ".png", ".webp", ".heic", ".mp4", ".webm"):
        suffix = ".jpg"

    dest_dir = _UPLOAD_ROOT / str(ctx.parent_id) / date
    dest_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{phase}_{slot}" if slot is not None else phase
    dest = dest_dir / f"{stem}{suffix}"

    content = await file.read()
    dest.write_bytes(content)

    url = f"/uploads/logs/{ctx.parent_id}/{date}/{stem}{suffix}"
    repo = await get_chungsora_repo()
    if phase == "baseline":
        await repo.set_baseline_slot(ctx.parent_id, slot or 0, url)
    elif slot is None or slot >= 2:
        await repo.set_log_photo(ctx.parent_id, date, phase, url)

    return {"date": date, "phase": phase, "slot": slot, "url": url}
