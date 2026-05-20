# -*- coding: utf-8 -*-
from fastapi import APIRouter

from api.cleaning.cleaning_router import router as cleaning_router
from api.parent.parent_router import router as parent_router
from api.child.child_router import router as child_router
from api.logs.log_router import router as log_router
from api.praise.praise_router import router as praise_router
from api.family.pair_router import router as pair_router
from api.family.family_router import router as family_router
from api.lock.lock_router import router as lock_router
from api.rewards.rewards_router import router as rewards_router
from api.auth.auth_router import router as auth_router
from api.points.points_router import router as points_router

api_router = APIRouter()
api_router.include_router(cleaning_router, prefix="/cleaning", tags=["cleaning"])
api_router.include_router(parent_router, prefix="/parent", tags=["parent"])
api_router.include_router(child_router, prefix="/child", tags=["child"])
api_router.include_router(log_router, prefix="/logs", tags=["logs"])
api_router.include_router(praise_router, prefix="/praise-presets", tags=["praise-presets"])
api_router.include_router(pair_router, prefix="/family/pair", tags=["family"])
api_router.include_router(family_router, prefix="/family", tags=["family"])
api_router.include_router(lock_router, prefix="/lock", tags=["lock"])
api_router.include_router(rewards_router, prefix="/rewards", tags=["rewards"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(points_router, prefix="/points", tags=["points"])
