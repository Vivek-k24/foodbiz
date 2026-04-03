from __future__ import annotations

from fastapi import APIRouter
from opentelemetry import trace

from rop.api.middleware.request_id import get_request_id
from rop.application.dto.responses import TableResponse, TableSummaryResponse
from rop.application.use_cases.close_table import CloseTable
from rop.application.use_cases.context import TraceContext
from rop.application.use_cases.open_table import GetTable, OpenTable
from rop.application.use_cases.table_summary import GetTableSummary
from rop.domain.common.ids import RestaurantId, TableId
from rop.infrastructure.db.repositories.order_repo import SqlAlchemyOrderRepository
from rop.infrastructure.db.repositories.table_repo import SqlAlchemyTableRepository
from rop.infrastructure.messaging.redis_publisher import RedisEventPublisher

router = APIRouter()


def _current_trace_id() -> str | None:
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return None
    return format(span_context.trace_id, "032x")


def _open_table_use_case() -> OpenTable:
    return OpenTable(
        table_repository=SqlAlchemyTableRepository(),
        publisher=RedisEventPublisher(),
    )


def _get_table_use_case() -> GetTable:
    return GetTable(table_repository=SqlAlchemyTableRepository())


def _close_table_use_case() -> CloseTable:
    return CloseTable(
        table_repository=SqlAlchemyTableRepository(),
        order_repository=SqlAlchemyOrderRepository(),
        publisher=RedisEventPublisher(),
    )


def _get_table_summary_use_case() -> GetTableSummary:
    return GetTableSummary(
        table_repository=SqlAlchemyTableRepository(),
        order_repository=SqlAlchemyOrderRepository(),
    )


@router.post("/v1/restaurants/{restaurant_id}/tables/{table_id}/open", response_model=TableResponse)
def open_table(restaurant_id: str, table_id: str) -> TableResponse:
    payload = _open_table_use_case().execute(
        restaurant_id=RestaurantId(restaurant_id),
        table_id=TableId(table_id),
        trace_ctx=TraceContext(trace_id=_current_trace_id(), request_id=get_request_id()),
    )
    return payload


@router.get("/v1/restaurants/{restaurant_id}/tables/{table_id}", response_model=TableResponse)
def get_table(restaurant_id: str, table_id: str) -> TableResponse:
    return _get_table_use_case().execute(
        restaurant_id=RestaurantId(restaurant_id),
        table_id=TableId(table_id),
    )


@router.post(
    "/v1/restaurants/{restaurant_id}/tables/{table_id}/close", response_model=TableResponse
)
def close_table(restaurant_id: str, table_id: str) -> TableResponse:
    return _close_table_use_case().execute(
        restaurant_id=RestaurantId(restaurant_id),
        table_id=TableId(table_id),
        trace_ctx=TraceContext(trace_id=_current_trace_id(), request_id=get_request_id()),
    )


@router.get(
    "/v1/restaurants/{restaurant_id}/tables/{table_id}/summary",
    response_model=TableSummaryResponse,
)
def get_table_summary(restaurant_id: str, table_id: str) -> TableSummaryResponse:
    return _get_table_summary_use_case().execute(
        restaurant_id=RestaurantId(restaurant_id),
        table_id=TableId(table_id),
    )
