# -*- coding: utf-8 -*-
"""Gemini model ID -> UI label (no Ollama/YOLO)."""

_STATIC: dict[str, str] = {
    "gemini-3.1-pro-preview": "Gemini 3.1 Pro",
    "gemini-3.1-flash-lite-preview": "Gemini 3.1 Flash Lite",
    "gemini-3.1-flash-image-preview": "Gemini 3.1 Flash Image",
    "gemini-3-pro-image-preview": "Gemini 3 Pro Image",
    "gemini-3-flash-preview": "Gemini 3 Flash",
    "fallback": "기본 탐지",
}


def format_model_label(model_id: str | None) -> str:
    if not model_id:
        return "Gemini"
    if model_id in _STATIC:
        return _STATIC[model_id]
    return model_id.replace("-", " ").title()
