# -*- coding: utf-8 -*-
from typing import List
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )

    PROJECT_NAME: str = "Mini Cleaning API"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    GEMINI_API_KEY: str = ""
    JWT_SECRET: str = ""

    CORS_ORIGINS: List[str] = [
        "http://localhost:34567",
        "http://localhost:3111",
        "http://localhost:3000",
        "https://mini3.cloud",
        "https://www.mini3.cloud",
    ]

    DATABASE_URL: str = ""
    NEON_DB_URL: str = ""
    NEON_DB_USERNAME: str = ""
    NEON_DB_PASSWORD: str = ""

    # EC2: /app/uploads (호스트 볼륨 마운트). 비우면 mini_backend/uploads
    UPLOAD_DIR: str = ""

    # ── 사진 저장 백엔드 (S3 클라우드 저장 준비) ────────────────────────────
    # STORAGE_BACKEND: "auto"(기본) | "local" | "s3"
    #   auto → AWS_S3_BUCKET 가 설정돼 있으면 s3, 아니면 local(EC2 디스크).
    #   키를 .env 에 채우기 전까지는 기존과 동일하게 로컬 디스크에 저장된다.
    STORAGE_BACKEND: str = "auto"
    AWS_S3_BUCKET: str = ""
    AWS_REGION: str = "ap-northeast-2"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_PREFIX: str = "uploads"          # 버킷 내 키 접두사
    # CloudFront/공개 도메인이 있으면 그 베이스 URL, 없으면 비워두면 S3 가상호스트 URL 사용
    S3_PUBLIC_BASE_URL: str = ""

    @property
    def storage_backend(self) -> str:
        b = (self.STORAGE_BACKEND or "auto").strip().lower()
        if b == "auto":
            return "s3" if self.AWS_S3_BUCKET.strip() else "local"
        return b

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        url = self.NEON_DB_URL.replace("jdbc:", "")
        if "://" in url and self.NEON_DB_USERNAME:
            proto, rest = url.split("://", 1)
            pw = quote_plus(self.NEON_DB_PASSWORD or "")
            user = quote_plus(self.NEON_DB_USERNAME)
            return f"{proto}://{user}:{pw}@{rest}"
        return url


settings = Settings()
