from __future__ import annotations

from rop.application.dto.responses import (
    MoneyResponse,
    TableRegistryItemResponse,
    TableRegistryResponse,
    TableSummaryCountsResponse,
)
from rop.application.metrics.order_lifecycle import record_tables_list_request
from rop.application.ports.repositories import InvalidCursorError, TableRepository
from rop.domain.common.ids import RestaurantId
from rop.domain.table.entities import TableStatus

_STATUS_MAP: dict[str, TableStatus | None] = {
    "ALL": None,
    "OPEN": TableStatus.OPEN,
    "CLOSED": TableStatus.CLOSED,
}


class InvalidTableRegistryStatusError(Exception):
    pass


class InvalidTableRegistryCursorError(Exception):
    pass


class RestaurantNotFoundError(Exception):
    pass


class ListTables:
    def __init__(self, table_repository: TableRepository) -> None:
        self._table_repository = table_repository

    def execute(
        self,
        restaurant_id: RestaurantId,
        *,
        status: str = "ALL",
        limit: int = 50,
        cursor: str | None = None,
    ) -> TableRegistryResponse:
        normalized_status = status.upper()
        if normalized_status not in _STATUS_MAP:
            raise InvalidTableRegistryStatusError(f"invalid table registry status: {status}")
        if limit < 1 or limit > 200:
            raise InvalidTableRegistryStatusError("limit must be between 1 and 200")

        if not self._table_repository.restaurant_exists(restaurant_id):
            raise RestaurantNotFoundError(f"restaurant {restaurant_id} not found")

        try:
            rows, next_cursor = self._table_repository.list_for_restaurant(
                restaurant_id=restaurant_id,
                status=_STATUS_MAP[normalized_status],
                limit=limit,
                cursor=cursor,
            )
        except InvalidCursorError as exc:
            raise InvalidTableRegistryCursorError("invalid cursor") from exc

        record_tables_list_request(
            restaurant_id=str(restaurant_id),
            status=normalized_status,
        )
        return TableRegistryResponse(
            tables=[
                TableRegistryItemResponse(
                    tableId=str(row.table.table_id),
                    restaurantId=str(row.table.restaurant_id),
                    status=row.table.status.value,
                    openedAt=row.table.opened_at,
                    closedAt=row.table.closed_at,
                    lastOrderAt=row.summary.last_order_at,
                    totals=MoneyResponse(
                        amountCents=row.summary.amount_cents,
                        currency=row.summary.currency,
                    ),
                    counts=TableSummaryCountsResponse(
                        ordersTotal=row.summary.orders_total,
                        placed=row.summary.placed,
                        accepted=row.summary.accepted,
                        ready=row.summary.ready,
                    ),
                )
                for row in rows
            ],
            nextCursor=next_cursor,
        )
