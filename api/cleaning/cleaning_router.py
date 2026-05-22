# -*- coding: utf-8 -*-
from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile

from core.database import get_pool
from core.jwt_utils import decode_access_token
from domain.cleaning.cleaning_dto import (
    AiInfoResponse,
    BaselineEvalResponse,
    ChatRequest,
    ChatResponse,
    CompareBaselineResponse,
    MemoryRequest,
    MemoryResponse,
    ScanResponse,
    VerifyResponse,
)
from domain.cleaning.cleaning_repository import CleaningRepository
from domain.cleaning import cleaning_service
from domain.chungsora.chungsora_repository import get_chungsora_repo

router = APIRouter()
logger = logging.getLogger(__name__)

GUEST_USER_ID = "guest"
DEFAULT_PASS_SCORE = 70


def _parent_id_from_auth(authorization: str | None) -> int | None:
    """compare-baseline 은 인증 없이도(게스트) 동작하므로, 토큰이 있으면 부모 id 를
    추출하고 없거나 잘못되면 None 을 반환한다(예외 던지지 않음)."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    # 부모 토큰: sub=parent_id / 자녀 토큰: typ=child, pid=parent_id
    if payload.get("typ") == "child":
        return int(payload["pid"]) if "pid" in payload else None
    return int(payload["sub"]) if "sub" in payload else None


async def _resolve_pass_score(
    authorization: str | None, override: int | None
) -> tuple[int, str]:
    """적용할 통과 기준 점수와 출처를 결정한다.
    우선순위: 명시 override > 부모 계정 정책(pass_score) > 기본값(70)."""
    if override is not None:
        return max(0, min(100, override)), "override"
    parent_id = _parent_id_from_auth(authorization)
    if parent_id is not None:
        try:
            repo = await get_chungsora_repo()
            profile = await repo.get_parent_by_id(parent_id)
            if profile and profile.get("pass_score") is not None:
                return int(profile["pass_score"]), "policy"
        except Exception as e:  # DB 문제로 채점 자체를 막지 않는다
            logger.warning("[compare-baseline] pass_score lookup failed: %s", e)
    return DEFAULT_PASS_SCORE, "default"


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


@router.post("/compare-baseline", response_model=CompareBaselineResponse)
async def compare_baseline(
    baseline_file: UploadFile = File(...),
    after_file: UploadFile = File(...),
    slot_label: str = Form(...),
    pass_score: int | None = Form(default=None),
    authorization: str | None = Header(default=None),
) -> CompareBaselineResponse:
    baseline_bytes = await baseline_file.read()
    after_bytes = await after_file.read()
    try:
        result = await cleaning_service.compare_with_baseline(
            baseline_bytes, after_bytes, slot_label
        )
    except Exception as e:
        logger.error("[cleaning] /compare-baseline error: %s", e)
        raise HTTPException(status_code=502, detail="baseline 비교 채점에 실패했습니다.")

    # 부모가 정한 통과 기준(pass_score)과의 비교를 서버에서 판정한다.
    effective_pass, source = await _resolve_pass_score(authorization, pass_score)
    return CompareBaselineResponse(
        cleanliness=result.cleanliness,
        comment=result.comment,
        model_id=result.model_id,
        model_label=result.model_label,
        pass_score=effective_pass,
        passed=result.cleanliness >= effective_pass,
        pass_score_source=source,
    )


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
