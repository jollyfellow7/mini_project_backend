# -*- coding: utf-8 -*-
import asyncio
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from api.deps.auth_deps import FamilyContext, get_family_context
from core.upload_paths import resolve_upload_logs_root
from domain.chungsora.chungsora_repository import get_chungsora_repo

router = APIRouter()
logger = logging.getLogger(__name__)

_UPLOAD_ROOT = resolve_upload_logs_root()
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_YEAR_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")

# 업로드 크기 제한: 이미지 20MB / 동영상 200MB
_MAX_IMAGE_BYTES = 20 * 1024 * 1024
_MAX_VIDEO_BYTES = 200 * 1024 * 1024
_VIDEO_SUFFIXES = {".mp4", ".webm"}


def _write_bytes_sync(dest: Path, content: bytes) -> None:
    """동기 파일 쓰기 — asyncio.to_thread 에서 실행."""
    dest.write_bytes(content)


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

    is_video = suffix in _VIDEO_SUFFIXES
    max_bytes = _MAX_VIDEO_BYTES if is_video else _MAX_IMAGE_BYTES

    # 청크 단위 읽기 — 대용량 동영상 업로드 시 메모리 초과 방지
    chunks: list[bytes] = []
    total = 0
    chunk_size = 1024 * 1024  # 1 MB
    try:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                limit_mb = max_bytes // (1024 * 1024)
                raise HTTPException(
                    status_code=413,
                    detail=f"파일 크기 초과: 최대 {limit_mb}MB까지 허용됩니다.",
                )
            chunks.append(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[upload_photo] 파일 읽기 실패 parent=%s date=%s: %s", ctx.parent_id, date, exc)
        raise HTTPException(status_code=400, detail="파일을 읽는 중 오류가 발생했습니다.")

    content = b"".join(chunks)

    dest_dir = _UPLOAD_ROOT / str(ctx.parent_id) / date
    dest_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{phase}_{slot}" if slot is not None else phase
    dest = dest_dir / f"{stem}{suffix}"

    # 동기 파일 쓰기를 스레드풀로 분리 — 이벤트 루프 블로킹 방지
    try:
        await asyncio.to_thread(_write_bytes_sync, dest, content)
    except Exception as exc:
        logger.error("[upload_photo] 파일 저장 실패 path=%s: %s", dest, exc)
        raise HTTPException(status_code=500, detail="파일 저장 중 오류가 발생했습니다.")

    url = f"/uploads/logs/{ctx.parent_id}/{date}/{stem}{suffix}"
    repo = await get_chungsora_repo()
    try:
        if phase == "baseline":
            await repo.set_baseline_slot(ctx.parent_id, slot or 0, url)
        elif slot is None or slot >= 2:
            await repo.set_log_photo(ctx.parent_id, date, phase, url)
    except Exception as exc:
        logger.error("[upload_photo] DB 업데이트 실패 parent=%s: %s", ctx.parent_id, exc)
        raise HTTPException(status_code=500, detail="업로드 정보 저장 중 오류가 발생했습니다.")

    logger.info(
        "[upload_photo] 완료 parent=%s date=%s phase=%s slot=%s size=%dB",
        ctx.parent_id, date, phase, slot, total,
    )
    return {"date": date, "phase": phase, "slot": slot, "url": url}
