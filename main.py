# -*- coding: utf-8 -*-
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.router import api_router
from core.config import settings
from core.database import close_pool, get_pool
from core.upload_paths import resolve_upload_root, upload_dir_writable

_UPLOAD_DIR = resolve_upload_root()


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await get_pool()
    from domain.cleaning.cleaning_repository import init_cleaning_tables
    from domain.chungsora.chungsora_repository import init_chungsora_tables

    await init_cleaning_tables(pool)
    await init_chungsora_tables(pool)
    yield
    await close_pool()


app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready():
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        uploads_ok = upload_dir_writable()
        body = {"status": "ready", "database": "ok", "uploads": "ok" if uploads_ok else "not_writable"}
        if not uploads_ok:
            from fastapi.responses import JSONResponse

            return JSONResponse(status_code=503, content=body)
        return body
    except Exception as exc:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": str(exc)},
        )


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.mount("/uploads", StaticFiles(directory=str(_UPLOAD_DIR)), name="uploads")
