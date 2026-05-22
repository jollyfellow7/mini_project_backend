# -*- coding: utf-8 -*-
"""사진/파일 저장 추상화 — 로컬 디스크(EC2 볼륨) ↔ S3 클라우드 전환.

설계 의도
---------
- 지금은 사진 바이트가 EC2 디스크(/app/uploads, 호스트 볼륨 /var/lib/mini-cleaning/uploads)
  에 저장되고, DB(Neon)에는 URL 문자열만 들어간다. 인스턴스가 교체되면 사진이 사라질 수 있다.
- 이 모듈은 동일한 인터페이스(save_bytes)로 S3 업로드를 지원한다.
  AWS_S3_BUCKET 등 자격증명을 .env 에 채우면 STORAGE_BACKEND=auto 가 s3 로 전환된다.
- 키(자격증명)가 없을 때는 기존과 100% 동일하게 로컬 디스크에 저장하므로,
  지금 배포해도 동작이 바뀌지 않는다(점진적 마이그레이션).

사용 예
-------
    from core.storage import get_storage
    url = await get_storage().save_bytes(
        key="logs/12/2026-05-22/after_2.jpg",
        data=content,
        content_type="image/jpeg",
    )
    # local → "/uploads/logs/12/2026-05-22/after_2.jpg"  (StaticFiles 가 서빙)
    # s3    → "https://<bucket>.s3.<region>.amazonaws.com/uploads/logs/..." 또는 CDN URL
"""
from __future__ import annotations

import asyncio
import logging
import mimetypes
from abc import ABC, abstractmethod
from pathlib import Path

from core.config import settings
from core.upload_paths import resolve_upload_root

logger = logging.getLogger(__name__)


def guess_content_type(filename: str, default: str = "application/octet-stream") -> str:
    ctype, _ = mimetypes.guess_type(filename)
    return ctype or default


class Storage(ABC):
    backend_name: str = "base"

    @abstractmethod
    async def save_bytes(self, key: str, data: bytes, content_type: str | None = None) -> str:
        """key(상대 경로)에 바이트를 저장하고 접근 가능한 URL 을 반환."""
        raise NotImplementedError


class LocalStorage(Storage):
    """EC2 디스크/로컬 볼륨 저장. URL 은 /uploads/<key> (StaticFiles 마운트와 일치)."""

    backend_name = "local"

    def __init__(self) -> None:
        self._root = resolve_upload_root()

    @staticmethod
    def _write_sync(dest: Path, data: bytes) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

    async def save_bytes(self, key: str, data: bytes, content_type: str | None = None) -> str:
        key = key.lstrip("/")
        dest = self._root / key
        await asyncio.to_thread(self._write_sync, dest, data)
        return f"/uploads/{key}"


class S3Storage(Storage):
    """AWS S3 저장. boto3 lazy import. 자격증명은 .env(또는 EC2 IAM 역할)에서."""

    backend_name = "s3"

    def __init__(self) -> None:
        self._bucket = settings.AWS_S3_BUCKET.strip()
        self._region = settings.AWS_REGION.strip() or "ap-northeast-2"
        self._prefix = settings.S3_PREFIX.strip().strip("/")
        self._public_base = settings.S3_PUBLIC_BASE_URL.strip().rstrip("/")
        if not self._bucket:
            raise RuntimeError("AWS_S3_BUCKET 가 설정되지 않았습니다.")
        self._client = self._build_client()

    def _build_client(self):
        import boto3  # lazy import — boto3 미설치/미사용 환경 보호

        kwargs = {"region_name": self._region}
        # 키가 명시되면 사용, 없으면 boto3 기본 체인(EC2 IAM 역할 등) 사용
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
        return boto3.client("s3", **kwargs)

    def _full_key(self, key: str) -> str:
        key = key.lstrip("/")
        return f"{self._prefix}/{key}" if self._prefix else key

    def _public_url(self, full_key: str) -> str:
        if self._public_base:
            return f"{self._public_base}/{full_key}"
        return f"https://{self._bucket}.s3.{self._region}.amazonaws.com/{full_key}"

    def _put_sync(self, full_key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            Bucket=self._bucket,
            Key=full_key,
            Body=data,
            ContentType=content_type,
        )

    async def save_bytes(self, key: str, data: bytes, content_type: str | None = None) -> str:
        full_key = self._full_key(key)
        ctype = content_type or guess_content_type(key)
        await asyncio.to_thread(self._put_sync, full_key, data, ctype)
        return self._public_url(full_key)


_storage: Storage | None = None


def get_storage() -> Storage:
    """설정에 따라 단일 Storage 인스턴스를 반환(지연 초기화)."""
    global _storage
    if _storage is not None:
        return _storage
    backend = settings.storage_backend
    if backend == "s3":
        try:
            _storage = S3Storage()
            logger.info("[storage] S3 backend 사용 bucket=%s", settings.AWS_S3_BUCKET)
        except Exception as e:
            # S3 초기화 실패 시 서비스 중단 대신 로컬로 폴백(사진 분실 방지)
            logger.error("[storage] S3 초기화 실패 → 로컬 폴백: %s", e)
            _storage = LocalStorage()
    else:
        _storage = LocalStorage()
        logger.info("[storage] Local disk backend 사용 root=%s", resolve_upload_root())
    return _storage


def reset_storage_cache() -> None:
    """테스트/설정 변경용 — 캐시된 storage 인스턴스 초기화."""
    global _storage
    _storage = None
