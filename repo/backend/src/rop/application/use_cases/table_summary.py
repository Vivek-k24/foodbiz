from __future__ import annotations

from rop.application.dto.responses import (
    MoneyResponse,
    TableSummaryCountsResponse,
    TableSummaryResponse,
)
from rop.application.ports.repositories import OrderRepository, TableRepository
from rop.application.use_cases.open_table import TableNotFoundError
from rop.domain.common.ids import RestaurantId, TableId


class GetTableSummary:
    def __init__(
        self,
        table_repository: TableRepository,
        order_repository: OrderRepository,
    ) -> None:
        self._table_repository = table_repository
        self._order_repository = order_repository

    def execute(self, restaurant_id: RestaurantId, table_id: TableId) -> TableSummaryResponse:
        table = self._table_repository.get(table_id=table_id, restaurant_id=restaurant_id)
        if table is None:
            raise TableNotFoundError(
                f"table not found for restaurant_id={restaurant_id}, table_id={table_id}"
            )

        summary = self._order_repository.summarize_for_table(
            restaurant_id=restaurant_id,
            table_id=table_id,
        )
        return TableSummaryResponse(
            tableId=str(table.table_id),
            restaurantId=str(table.restaurant_id),
            status=table.status.value,
            openedAt=table.opened_at,
            closedAt=table.closed_at,
            totals=MoneyResponse(
                amountCents=summary.amount_cents,
                currency=summary.currency,
            ),
            counts=TableSummaryCountsResponse(
                ordersTotal=summary.orders_total,
                placed=summary.placed,
                accepted=summary.accepted,
                ready=summary.ready,
            ),
            lastOrderAt=summary.last_order_at,
        )
