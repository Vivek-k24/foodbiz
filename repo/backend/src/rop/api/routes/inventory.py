from __future__ import annotations

from fastapi import APIRouter, Depends

from rop.api.dependencies import get_inventory_service
from rop.application.inventory.service import InventoryService

router = APIRouter()


@router.get("/v1/inventory/status")
def inventory_status(
    service: InventoryService = Depends(get_inventory_service),
) -> dict[str, object]:
    return service.status()
