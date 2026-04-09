from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from rop.api.dependencies import get_kitchen_service
from rop.application.commerce.schemas import OrderResponse
from rop.application.kitchen.schemas import KitchenQueueResponse
from rop.application.kitchen.service import KitchenService
from rop.domain.commerce.enums import OrderStatus

router = APIRouter()


@router.get("/v1/restaurants/{restaurant_id}/kitchen/orders", response_model=KitchenQueueResponse)
def kitchen_queue(
    restaurant_id: str,
    status: OrderStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    service: KitchenService = Depends(get_kitchen_service),
) -> KitchenQueueResponse:
    return service.queue(restaurant_id, status, limit)


@router.post("/v1/orders/{order_id}/accept", response_model=OrderResponse)
def accept_order(
    order_id: str,
    service: KitchenService = Depends(get_kitchen_service),
) -> OrderResponse:
    return service.transition(order_id, "accept")


@router.post("/v1/orders/{order_id}/ready", response_model=OrderResponse)
def mark_ready(
    order_id: str,
    service: KitchenService = Depends(get_kitchen_service),
) -> OrderResponse:
    return service.transition(order_id, "ready")


@router.post("/v1/orders/{order_id}/served", response_model=OrderResponse)
def mark_served(
    order_id: str,
    service: KitchenService = Depends(get_kitchen_service),
) -> OrderResponse:
    return service.transition(order_id, "served")


@router.post("/v1/orders/{order_id}/settled", response_model=OrderResponse)
def mark_settled(
    order_id: str,
    service: KitchenService = Depends(get_kitchen_service),
) -> OrderResponse:
    return service.transition(order_id, "settled")
