# -*- coding: utf-8 -*-
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import api_router
from core.config import settings
from core.database import close_pool, get_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await get_pool()
    from domain.cleaning.cleaning_repository import init_cleaning_tables

    await init_cleaning_tables(pool)
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


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
