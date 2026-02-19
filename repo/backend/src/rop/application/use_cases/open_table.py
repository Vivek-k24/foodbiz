from __future__ import annotations

from datetime import datetime, timezone

from rop.application.dto.responses import TableResponse
from rop.application.mappers.event_envelope import serialize_table_opened_event
from rop.application.mappers.table_mapper import to_table_response
from rop.application.metrics.order_lifecycle import record_table_opened
from rop.application.ports.publisher import EventPublisher
from rop.application.ports.repositories import TableRepository
from rop.application.use_cases.context import TraceContext
from rop.domain.common.ids import RestaurantId, TableId
from rop.domain.table.entities import Table, TableStatus


class TableNotFoundError(Exception):
    pass


class OpenTable:
    def __init__(
        self,
        table_repository: TableRepository,
        publisher: EventPublisher,
    ) -> None:
        self._table_repository = table_repository
        self._publisher = publisher

    def execute(
        self,
        restaurant_id: RestaurantId,
        table_id: TableId,
        trace_ctx: TraceContext,
    ) -> TableResponse:
        table = self._table_repository.get(table_id=table_id, restaurant_id=restaurant_id)
        now = datetime.now(timezone.utc)
        should_publish = table is None or table.status != TableStatus.OPEN

        if table is None:
            updated = Table(
                table_id=table_id,
                restaurant_id=restaurant_id,
                status=TableStatus.OPEN,
                opened_at=now,
                closed_at=None,
            )
        else:
            updated = table.open(now)

        self._table_repository.upsert(updated)
        if should_publish:
            opened_at = updated.opened_at or now
            message = serialize_table_opened_event(
                occurred_at=now,
                restaurant_id=str(restaurant_id),
                table_id=str(table_id),
                opened_at=opened_at,
                trace_id=trace_ctx.trace_id,
                request_id=trace_ctx.request_id,
            )
            record_table_opened(restaurant_id=str(restaurant_id))
            try:
                self._publisher.publish(channel=f"events:{restaurant_id}", message=message)
            except Exception:
                pass
        return to_table_response(updated)


class GetTable:
    def __init__(self, table_repository: TableRepository) -> None:
        self._table_repository = table_repository

    def execute(self, restaurant_id: RestaurantId, table_id: TableId) -> TableResponse:
        table = self._table_repository.get(table_id=table_id, restaurant_id=restaurant_id)
        if table is None:
            raise TableNotFoundError(
                f"table not found for restaurant_id={restaurant_id}, table_id={table_id}"
            )
        return to_table_response(table)
