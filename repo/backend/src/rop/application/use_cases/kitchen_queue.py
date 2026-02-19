from __future__ import annotations

from rop.application.dto.responses import KitchenQueueResponse
from rop.application.mappers.order_mapper import to_order_response
from rop.application.metrics.order_lifecycle import record_kitchen_queue_size
from rop.application.ports.repositories import InvalidCursorError, OrderRepository
from rop.domain.common.ids import RestaurantId
from rop.domain.order.entities import OrderStatus

_STATUS_MAP: dict[str, OrderStatus | None] = {
    "ALL": None,
    "PLACED": OrderStatus.PLACED,
    "ACCEPTED": OrderStatus.ACCEPTED,
    "READY": OrderStatus.READY,
}


class InvalidKitchenQueueStatusError(Exception):
    pass


class InvalidKitchenQueueCursorError(Exception):
    pass


class KitchenQueue:
    def __init__(self, order_repository: OrderRepository) -> None:
        self._order_repository = order_repository

    def execute(
        self,
        restaurant_id: RestaurantId,
        status: str = "ALL",
        limit: int = 50,
        cursor: str | None = None,
    ) -> KitchenQueueResponse:
        normalized_status = status.upper()
        if normalized_status not in _STATUS_MAP:
            raise InvalidKitchenQueueStatusError(f"invalid kitchen queue status: {status}")
        if limit < 1 or limit > 200:
            raise InvalidKitchenQueueStatusError("limit must be between 1 and 200")

        try:
            orders, next_cursor = self._order_repository.list_for_kitchen(
                restaurant_id=restaurant_id,
                status=_STATUS_MAP[normalized_status],
                limit=limit,
                cursor=cursor,
            )
        except InvalidCursorError as exc:
            raise InvalidKitchenQueueCursorError("invalid cursor") from exc

        record_kitchen_queue_size(
            restaurant_id=str(restaurant_id),
            status=normalized_status,
            size=len(orders),
        )

        return KitchenQueueResponse(
            orders=[to_order_response(order) for order in orders],
            nextCursor=next_cursor,
        )
