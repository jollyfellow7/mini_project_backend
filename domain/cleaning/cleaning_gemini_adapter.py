# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
from typing import Any, Literal

from core.config import settings
from core.cleaning_gemini_models import (
    CHAT_MODEL_ORDER,
    GEMINI_MODELS,
    VISION_MODEL_ORDER,
)

logger = logging.getLogger(__name__)

Kind = Literal["vision", "chat"]


def _pick_model(kind: Kind) -> str:
    order = VISION_MODEL_ORDER if kind == "vision" else CHAT_MODEL_ORDER
    for m in order:
        if m in GEMINI_MODELS:
            return m
    return GEMINI_MODELS[0]


def _client():
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set")
    from google import genai  # lazy import

    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _strip_json_fence(text: str) -> str:
    t = text.strip()
    if "```" in t:
        parts = t.split("```")
        if len(parts) >= 2:
            inner = parts[1]
            if inner.lstrip().lower().startswith("json"):
                inner = inner.lstrip()[4:].lstrip()
            return inner.strip()
    return t


def _parse_json(text: str) -> dict[str, Any]:
    raw = _strip_json_fence(text)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            return json.loads(m.group(0))
        raise


def _sync_generate_text(prompt: str, model: str | None = None) -> tuple[str, str]:
    model = model or _pick_model("chat")
    client = _client()
    last: BaseException | None = None
    for mid in [model] + [m for m in CHAT_MODEL_ORDER if m != model]:
        try:
            response = client.models.generate_content(
                model=mid,
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
            )
            text = (response.text or "").strip()
            if text:
                return text, mid
        except Exception as exc:
            logger.warning("[gemini text] model=%s failed: %s", mid, exc)
            last = exc
    raise RuntimeError("Gemini text call failed") from last


def _sync_generate_vision(
    image_bytes: bytes,
    mime_type: str,
    prompt: str,
    model: str | None = None,
) -> tuple[str, str]:
    model = model or _pick_model("vision")
    b64 = base64.b64encode(image_bytes).decode("ascii")
    client = _client()
    last: BaseException | None = None
    for mid in [model] + [m for m in VISION_MODEL_ORDER if m != model]:
        try:
            response = client.models.generate_content(
                model=mid,
                contents=[
                    {
                        "role": "user",
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": mime_type, "data": b64}},
                        ],
                    }
                ],
            )
            text = (response.text or "").strip()
            if text:
                return text, mid
        except Exception as exc:
            logger.warning("[gemini vision] model=%s failed: %s", mid, exc)
            last = exc
    raise RuntimeError("Gemini vision call failed") from last


async def generate_text(prompt: str, model: str | None = None) -> tuple[str, str]:
    return await asyncio.to_thread(_sync_generate_text, prompt, model)


async def generate_vision(
    image_bytes: bytes,
    mime_type: str,
    prompt: str,
    model: str | None = None,
) -> tuple[str, str]:
    return await asyncio.to_thread(
        _sync_generate_vision, image_bytes, mime_type, prompt, model
    )


def parse_json_response(text: str) -> dict[str, Any]:
    return _parse_json(text)
