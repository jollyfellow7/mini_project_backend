# -*- coding: utf-8 -*-
"""업로드 파일 루트 — EC2 Docker 볼륨(/app/uploads)과 로컬 개발 경로 통일."""
from pathlib import Path

from core.config import settings

# EC2 deploy.yml: -v /var/lib/mini-cleaning/uploads:/app/uploads -e UPLOAD_DIR=/app/uploads
DEFAULT_CONTAINER_UPLOAD_DIR = "/app/uploads"


def resolve_upload_root() -> Path:
    raw = (settings.UPLOAD_DIR or "").strip()
    if raw:
        root = Path(raw)
    else:
        root = Path(__file__).resolve().parents[1] / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_upload_logs_root() -> Path:
    logs = resolve_upload_root() / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return logs


def upload_dir_writable() -> bool:
    root = resolve_upload_root()
    probe = root / ".write_probe"
    try:
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False
