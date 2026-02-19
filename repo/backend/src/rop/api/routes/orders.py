from __future__ import annotations

from fastapi import APIRouter, Header, status
from opentelemetry import trace

from rop.api.middleware.request_id import get_request_id
from rop.application.dto.requests import PlaceOrderRequest
from rop.application.dto.responses import OrderResponse
from rop.application.use_cases.context import TraceContext
from rop.application.use_cases.get_order import GetOrder
from rop.application.use_cases.place_order import PlaceOrder
from rop.domain.common.ids import OrderId, RestaurantId, TableId
from rop.infrastructure.db.repositories.menu_repo import SqlAlchemyMenuRepository
from rop.infrastructure.db.repositories.order_repo import SqlAlchemyOrderRepository
from rop.infrastructure.db.repositories.table_repo import SqlAlchemyTableRepository
from rop.infrastructure.messaging.redis_publisher import RedisEventPublisher

router = APIRouter()


def _current_trace_id() -> str | None:
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return None
    return format(span_context.trace_id, "032x")


def _place_order_use_case() -> PlaceOrder:
    return PlaceOrder(
        menu_repository=SqlAlchemyMenuRepository(),
        table_repository=SqlAlchemyTableRepository(),
        order_repository=SqlAlchemyOrderRepository(),
        publisher=RedisEventPublisher(),
    )


def _get_order_use_case() -> GetOrder:
    return GetOrder(order_repository=SqlAlchemyOrderRepository())


@router.post(
    "/v1/restaurants/{restaurant_id}/tables/{table_id}/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def place_order(
    restaurant_id: str,
    table_id: str,
    request_dto: PlaceOrderRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> OrderResponse:
    use_case = _place_order_use_case()
    normalized_key = idempotency_key.strip() if idempotency_key else None
    return use_case.execute(
        restaurant_id=RestaurantId(restaurant_id),
        table_id=TableId(table_id),
        request_dto=request_dto,
        trace_ctx=TraceContext(trace_id=_current_trace_id(), request_id=get_request_id()),
        idempotency_key=normalized_key,
    )


@router.get("/v1/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: str) -> OrderResponse:
    return _get_order_use_case().execute(order_id=OrderId(order_id))
