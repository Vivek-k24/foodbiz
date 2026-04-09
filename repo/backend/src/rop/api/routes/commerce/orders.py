from __future__ import annotations

from fastapi import APIRouter, Depends, Header, status

from rop.api.dependencies import get_commerce_service
from rop.application.commerce.schemas import OrderCreateRequest, OrderResponse, OrderUpdateRequest
from rop.application.commerce.service import CommerceService

router = APIRouter()


@router.post("/v1/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    request: OrderCreateRequest,
    service: CommerceService = Depends(get_commerce_service),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> OrderResponse:
    return service.create_order(request, idempotency_key=idempotency_key)


@router.get("/v1/orders/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: str,
    service: CommerceService = Depends(get_commerce_service),
) -> OrderResponse:
    return service.get_order(order_id)


@router.patch("/v1/orders/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: str,
    request: OrderUpdateRequest,
    service: CommerceService = Depends(get_commerce_service),
) -> OrderResponse:
    return service.update_order(order_id, request)


@router.delete("/v1/orders/{order_id}", response_model=OrderResponse)
def delete_order(
    order_id: str,
    service: CommerceService = Depends(get_commerce_service),
) -> OrderResponse:
    return service.delete_order(order_id)
