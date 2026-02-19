from __future__ import annotations

from datetime import datetime, timezone

from rop.application.dto.responses import TableResponse
from rop.application.mappers.event_envelope import serialize_table_closed_event
from rop.application.mappers.table_mapper import to_table_response
from rop.application.metrics.order_lifecycle import record_table_close_blocked, record_table_closed
from rop.application.ports.publisher import EventPublisher
from rop.application.ports.repositories import OrderRepository, TableRepository
from rop.application.use_cases.context import TraceContext
from rop.application.use_cases.open_table import TableNotFoundError
from rop.domain.common.ids import RestaurantId, TableId
from rop.domain.table.entities import TableClosedError


class TableNotOpenForCloseError(Exception):
    pass


class TableCloseBlockedError(Exception):
    def __init__(self, message: str, reason: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.details = {"reason": reason}


class CloseTable:
    def __init__(
        self,
        table_repository: TableRepository,
        order_repository: OrderRepository,
        publisher: EventPublisher,
    ) -> None:
        self._table_repository = table_repository
        self._order_repository = order_repository
        self._publisher = publisher

    def execute(
        self,
        restaurant_id: RestaurantId,
        table_id: TableId,
        trace_ctx: TraceContext,
    ) -> TableResponse:
        table = self._table_repository.get(table_id=table_id, restaurant_id=restaurant_id)
        if table is None:
            raise TableNotFoundError(
                f"table not found for restaurant_id={restaurant_id}, table_id={table_id}"
            )

        try:
            table.ensure_open()
        except TableClosedError as exc:
            raise TableNotOpenForCloseError(str(exc)) from exc

        summary = self._order_repository.summarize_for_table(
            restaurant_id=restaurant_id,
            table_id=table_id,
        )
        if summary.placed > 0 or summary.accepted > 0:
            reason = "HAS_NON_READY_ORDERS"
            record_table_close_blocked(restaurant_id=str(restaurant_id), reason=reason)
            raise TableCloseBlockedError(
                f"table {table_id} cannot be closed while non-ready orders exist",
                reason=reason,
            )

        now = datetime.now(timezone.utc)
        closed_table = table.close(now)
        self._table_repository.upsert(closed_table)
        record_table_closed(restaurant_id=str(restaurant_id))

        closed_at = closed_table.closed_at or now
        message = serialize_table_closed_event(
            occurred_at=now,
            restaurant_id=str(restaurant_id),
            table_id=str(table_id),
            status=closed_table.status.value,
            closed_at=closed_at,
            trace_id=trace_ctx.trace_id,
            request_id=trace_ctx.request_id,
        )
        try:
            self._publisher.publish(channel=f"events:{restaurant_id}", message=message)
        except Exception:
            pass

        return to_table_response(closed_table)
