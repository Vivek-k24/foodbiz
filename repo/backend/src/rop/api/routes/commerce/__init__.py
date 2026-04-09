from __future__ import annotations

from fastapi import APIRouter

from rop.api.routes.commerce.orders import router as orders_router
from rop.api.routes.commerce.sessions import router as sessions_router
from rop.api.routes.commerce.storefront import router as storefront_router

router = APIRouter()
router.include_router(storefront_router)
router.include_router(sessions_router)
router.include_router(orders_router)
