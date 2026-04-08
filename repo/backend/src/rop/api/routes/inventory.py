from __future__ import annotations

from fastapi import APIRouter

from rop.application.dto.responses import InventoryStubResponse

router = APIRouter()


@router.get("/v1/inventory/status", response_model=InventoryStubResponse)
def inventory_status() -> InventoryStubResponse:
    return InventoryStubResponse(
        status="NOT_IMPLEMENTED",
        message="Inventory subsystem boundary exists, but stock logic is intentionally deferred.",
        implemented=False,
    )
