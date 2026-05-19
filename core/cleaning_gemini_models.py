# -*- coding: utf-8 -*-
"""Gemini model whitelist (skillstack / MINI doc — 5 only)."""

GEMINI_MODELS: list[str] = [
    "gemini-3.1-pro-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.1-flash-image-preview",
    "gemini-3-pro-image-preview",
    "gemini-3-flash-preview",
]

VISION_MODEL_ORDER: list[str] = [
    "gemini-3.1-flash-image-preview",
    "gemini-3-pro-image-preview",
    "gemini-3-flash-preview",
    "gemini-3.1-pro-preview",
    "gemini-3.1-flash-lite-preview",
]

CHAT_MODEL_ORDER: list[str] = [
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
    "gemini-3.1-pro-preview",
    "gemini-3.1-flash-image-preview",
    "gemini-3-pro-image-preview",
]
