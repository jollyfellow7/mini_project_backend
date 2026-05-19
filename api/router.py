# -*- coding: utf-8 -*-
from fastapi import APIRouter

from api.cleaning.cleaning_router import router as cleaning_router

api_router = APIRouter()
api_router.include_router(cleaning_router, prefix="/cleaning", tags=["cleaning"])
