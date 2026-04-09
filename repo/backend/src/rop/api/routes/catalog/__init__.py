from __future__ import annotations

from fastapi import APIRouter

from rop.api.routes.catalog.public import router as public_router

router = APIRouter()
router.include_router(public_router)
