from __future__ import annotations

from fastapi import APIRouter

from rop.api.routes.admin.categories import router as categories_router
from rop.api.routes.admin.locations import router as locations_router
from rop.api.routes.admin.menu_items import router as menu_items_router
from rop.api.routes.admin.restaurants import router as restaurants_router

router = APIRouter()
router.include_router(restaurants_router)
router.include_router(locations_router)
router.include_router(categories_router)
router.include_router(menu_items_router)
