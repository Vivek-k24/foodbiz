from __future__ import annotations

from fastapi import APIRouter, HTTPException
from opentelemetry import trace

from rop.api.middleware.request_id import get_request_id
from rop.application.dto.responses import OrderResponse
from rop.application.use_cases.accept_order import (
    AcceptOrder,
)
from rop.application.use_cases.accept_order import (
    InvalidOrderTransitionError as AcceptTransitionError,
)
from rop.application.use_cases.accept_order import (
    OrderNotFoundError as AcceptOrderNotFoundError,
)
from rop.application.use_cases.context import TraceContext
from rop.application.use_cases.mark_order_ready import (
    InvalidOrderTransitionError as ReadyTransitionError,
)
from rop.application.use_cases.mark_order_ready import (
    MarkOrderReady,
)
from rop.application.use_cases.mark_order_ready import (
    OrderNotFoundError as ReadyOrderNotFoundError,
)
from rop.domain.common.ids import OrderId
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


@router.post("/v1/orders/{order_id}/accept", response_model=OrderResponse)
def accept_order(order_id: str) -> OrderResponse:
    try:
        return _accept_order_use_case().execute(
            order_id=OrderId(order_id),
            trace_ctx=TraceContext(trace_id=_current_trace_id(), request_id=get_request_id()),
        )
    except AcceptOrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AcceptTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/v1/orders/{order_id}/ready", response_model=OrderResponse)
def mark_order_ready(order_id: str) -> OrderResponse:
    try:
        return _mark_order_ready_use_case().execute(
            order_id=OrderId(order_id),
            trace_ctx=TraceContext(trace_id=_current_trace_id(), request_id=get_request_id()),
        )
    except ReadyOrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReadyTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
