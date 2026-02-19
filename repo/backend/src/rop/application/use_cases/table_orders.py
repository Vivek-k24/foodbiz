from __future__ import annotations

from rop.application.dto.responses import TableOrdersResponse
from rop.application.mappers.order_mapper import to_order_response
from rop.application.ports.repositories import InvalidCursorError, OrderRepository, TableRepository
from rop.application.use_cases.open_table import TableNotFoundError
from rop.domain.common.ids import RestaurantId, TableId
from rop.domain.order.entities import OrderStatus

_STATUS_MAP: dict[str, OrderStatus | None] = {
    "ALL": None,
    "PLACED": OrderStatus.PLACED,
    "ACCEPTED": OrderStatus.ACCEPTED,
    "READY": OrderStatus.READY,
}


class InvalidTableOrdersStatusError(Exception):
    pass


class InvalidTableOrdersCursorError(Exception):
    pass


class TableOrders:
    def __init__(
        self,
        order_repository: OrderRepository,
        table_repository: TableRepository,
    ) -> None:
        self._order_repository = order_repository
        self._table_repository = table_repository

    def execute(
        self,
        restaurant_id: RestaurantId,
        table_id: TableId,
        *,
        status: str = "ALL",
        limit: int = 50,
        cursor: str | None = None,
    ) -> TableOrdersResponse:
        table = self._table_repository.get(table_id=table_id, restaurant_id=restaurant_id)
        if table is None:
            raise TableNotFoundError(
                f"table not found for restaurant_id={restaurant_id}, table_id={table_id}"
            )

        normalized_status = status.upper()
        if normalized_status not in _STATUS_MAP:
            raise InvalidTableOrdersStatusError(f"invalid table orders status: {status}")
        if limit < 1 or limit > 200:
            raise InvalidTableOrdersStatusError("limit must be between 1 and 200")

        try:
            orders, next_cursor = self._order_repository.list_for_table(
                restaurant_id=restaurant_id,
                table_id=table_id,
                status=_STATUS_MAP[normalized_status],
                limit=limit,
                cursor=cursor,
            )
        except InvalidCursorError as exc:
            raise InvalidTableOrdersCursorError("invalid cursor") from exc

        return TableOrdersResponse(
            orders=[to_order_response(order) for order in orders],
            nextCursor=next_cursor,
        )
