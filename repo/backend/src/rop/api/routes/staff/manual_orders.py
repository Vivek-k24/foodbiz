from __future__ import annotations

from fastapi import APIRouter, Depends, Header, status

from rop.api.dependencies import get_staff_service
from rop.application.commerce.schemas import OrderResponse
from rop.application.staff.schemas import ManualOrderRequest
from rop.application.staff.service import StaffService

router = APIRouter()


@router.post(
    "/v1/staff/manual-orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_manual_order(
    request: ManualOrderRequest,
    service: StaffService = Depends(get_staff_service),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> OrderResponse:
    return service.create_manual_order(request, idempotency_key=idempotency_key)
