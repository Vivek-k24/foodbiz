from __future__ import annotations

from fastapi import APIRouter

from rop.api.routes.staff.counter_orders import router as counter_orders_router
from rop.api.routes.staff.manual_orders import router as manual_orders_router
from rop.api.routes.staff.tables import router as tables_router
from rop.api.routes.staff.walk_in_sessions import router as walk_in_sessions_router

router = APIRouter()
router.include_router(tables_router)
router.include_router(manual_orders_router)
router.include_router(walk_in_sessions_router)
router.include_router(counter_orders_router)
