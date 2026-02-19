from __future__ import annotations

from fastapi import APIRouter, Query
from opentelemetry import trace

from rop.api.middleware.request_id import get_request_id
from rop.application.dto.responses import KitchenQueueResponse, OrderResponse
from rop.application.use_cases.accept_order import AcceptOrder
from rop.application.use_cases.context import TraceContext
from rop.application.use_cases.kitchen_queue import KitchenQueue
from rop.application.use_cases.mark_order_ready import MarkOrderReady
from rop.domain.common.ids import OrderId, RestaurantId
from rop.infrastructure.db.repositories.order_repo import SqlAlchemyOrderRepository
from rop.infrastructure.messaging.redis_publisher import RedisEventPublisher

router = APIRouter()


def _current_trace_id() -> str | None:
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return None
    return format(span_context.trace_id, "032x")


def _accept_order_use_case() -> AcceptOrder:
    return AcceptOrder(
        order_repository=SqlAlchemyOrderRepository(),
        publisher=RedisEventPublisher(),
    )


def _mark_order_ready_use_case() -> MarkOrderReady:
    return MarkOrderReady(
        order_repository=SqlAlchemyOrderRepository(),
        publisher=RedisEventPublisher(),
    )


def _kitchen_queue_use_case() -> KitchenQueue:
    return KitchenQueue(order_repository=SqlAlchemyOrderRepository())


@router.get(
    "/v1/restaurants/{restaurant_id}/kitchen/orders",
    response_model=KitchenQueueResponse,
)
def kitchen_queue(
    restaurant_id: str,
    status: str = Query(default="PLACED"),
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
) -> KitchenQueueResponse:
    return _kitchen_queue_use_case().execute(
        restaurant_id=RestaurantId(restaurant_id),
        status=status,
        limit=limit,
        cursor=cursor,
    )


@router.post("/v1/orders/{order_id}/accept", response_model=OrderResponse)
def accept_order(order_id: str) -> OrderResponse:
    return _accept_order_use_case().execute(
        order_id=OrderId(order_id),
        trace_ctx=TraceContext(trace_id=_current_trace_id(), request_id=get_request_id()),
    )


@router.post("/v1/orders/{order_id}/ready", response_model=OrderResponse)
def mark_order_ready(order_id: str) -> OrderResponse:
    return _mark_order_ready_use_case().execute(
        order_id=OrderId(order_id),
        trace_ctx=TraceContext(trace_id=_current_trace_id(), request_id=get_request_id()),
    )
