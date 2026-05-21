# -*- coding: utf-8 -*-
from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from core.database import get_pool
from domain.cleaning.cleaning_dto import (
    AiInfoResponse,
    BaselineEvalResponse,
    ChatRequest,
    ChatResponse,
    MemoryRequest,
    MemoryResponse,
    ScanResponse,
    VerifyResponse,
)
from domain.cleaning.cleaning_repository import CleaningRepository
from domain.cleaning import cleaning_service

router = APIRouter()
logger = logging.getLogger(__name__)

GUEST_USER_ID = "guest"


@router.get("/ai-info", response_model=AiInfoResponse)
async def ai_info() -> AiInfoResponse:
    return await cleaning_service.get_ai_info()


@router.post("/scan", response_model=ScanResponse)
async def scan_room(
    file: UploadFile = File(...),
    room_id: str = Form(...),
    room_name: str = Form(...),
) -> ScanResponse:
    image_bytes = await file.read()
    try:
        return await cleaning_service.scan_room(image_bytes, room_name)
    except RuntimeError:
        raise HTTPException(status_code=502, detail="AI 스캔에 실패했습니다. GEMINI_API_KEY를 확인해 주세요.")
    except Exception as e:
        logger.error("[cleaning] /scan error: %s", e)
        raise HTTPException(status_code=500, detail="스캔 중 오류가 발생했습니다.")


@router.post("/verify", response_model=VerifyResponse)
async def verify_room(
    file: UploadFile = File(...),
    room_id: str = Form(...),
    room_name: str = Form(...),
) -> VerifyResponse:
    image_bytes = await file.read()
    try:
        return await cleaning_service.verify_cleanliness(image_bytes, room_name)
    except RuntimeError:
        raise HTTPException(status_code=502, detail="AI 채점에 실패했습니다. GEMINI_API_KEY를 확인해 주세요.")
    except Exception as e:
        logger.error("[cleaning] /verify error: %s", e)
        raise HTTPException(status_code=500, detail="채점 중 오류가 발생했습니다.")


@router.post("/baseline-eval", response_model=BaselineEvalResponse)
async def baseline_eval(
    file: UploadFile = File(...),
    slot_label: str = Form(...),
) -> BaselineEvalResponse:
    image_bytes = await file.read()
    try:
        return await cleaning_service.evaluate_baseline(image_bytes, slot_label)
    except Exception as e:
        logger.error("[cleaning] /baseline-eval error: %s", e)
        raise HTTPException(status_code=502, detail="baseline AI 평가에 실패했습니다.")


@router.post("/compare-baseline", response_model=VerifyResponse)
async def compare_baseline(
    baseline_file: UploadFile = File(...),
    after_file: UploadFile = File(...),
    slot_label: str = Form(...),
) -> VerifyResponse:
    baseline_bytes = await baseline_file.read()
    after_bytes = await after_file.read()
    try:
        return await cleaning_service.compare_with_baseline(
            baseline_bytes, after_bytes, slot_label
        )
    except Exception as e:
        logger.error("[cleaning] /compare-baseline error: %s", e)
        raise HTTPException(status_code=502, detail="baseline 비교 채점에 실패했습니다.")


@router.post("/chat", response_model=ChatResponse)
async def coach_chat(body: ChatRequest) -> ChatResponse:
    try:
        return await cleaning_service.coach_chat(body.model_dump())
    except RuntimeError:
        raise HTTPException(status_code=502, detail="AI 코치에 연결할 수 없습니다.")
    except Exception as e:
        logger.error("[cleaning] /chat error: %s", e)
        raise HTTPException(status_code=500, detail="AI 코치 응답 오류.")


@router.post("/memory", response_model=MemoryResponse)
async def save_memory(body: MemoryRequest) -> MemoryResponse:
    pool = await get_pool()
    repo = CleaningRepository(pool)
    try:
        result = await repo.save_memory(
            user_id=GUEST_USER_ID,
            room_id=body.room_id,
            room_name=body.room_name,
            cleanliness=body.cleanliness,
            monsters_cleared=body.monsters_cleared,
            duration_sec=body.duration_seconds,
            exp_gained=body.exp_gained,
            gold_gained=body.gold_gained,
        )
        return MemoryResponse(id=result["id"], saved_at=str(result["created_at"]))
    except Exception as e:
        logger.error("[cleaning] /memory error: %s", e)
        raise HTTPException(status_code=500, detail="기억 저장 중 오류.")
