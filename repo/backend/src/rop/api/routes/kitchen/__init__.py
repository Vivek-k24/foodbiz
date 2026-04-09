from __future__ import annotations

from fastapi import APIRouter

from rop.api.routes.kitchen.queue import router as queue_router

router = APIRouter()
router.include_router(queue_router)
