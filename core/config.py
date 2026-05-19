# -*- coding: utf-8 -*-
from typing import List

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
        "http://localhost:3111",
        "http://localhost:3000",
    ]

    DATABASE_URL: str = ""
    NEON_DB_URL: str = ""
    NEON_DB_USERNAME: str = ""
    NEON_DB_PASSWORD: str = ""

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        url = self.NEON_DB_URL.replace("jdbc:", "")
        if "://" in url and self.NEON_DB_USERNAME:
            proto, rest = url.split("://", 1)
            return f"{proto}://{self.NEON_DB_USERNAME}:{self.NEON_DB_PASSWORD}@{rest}"
        return url


settings = Settings()
