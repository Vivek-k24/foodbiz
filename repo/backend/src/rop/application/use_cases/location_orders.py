from __future__ import annotations

from typing import Protocol

from rop.application.dto.responses import LocationOrdersResponse
from rop.application.mappers.order_mapper import to_order_response
from rop.application.ports.repositories import (
    InvalidCursorError,
    LocationRepository,
)
from rop.domain.common.ids import LocationId, RestaurantId
from rop.domain.order.entities import Order, OrderStatus

_STATUS_MAP: dict[str, OrderStatus | None] = {
    "ALL": None,
    "PLACED": OrderStatus.PLACED,
    "ACCEPTED": OrderStatus.ACCEPTED,
    "READY": OrderStatus.READY,
    "SERVED": OrderStatus.SERVED,
    "SETTLED": OrderStatus.SETTLED,
}


class LocationNotFoundError(Exception):
    pass


class InvalidLocationOrdersStatusError(Exception):
    pass


class InvalidLocationOrdersCursorError(Exception):
    pass


class LocationOrderRepository(Protocol):
    def list_for_location(
        self,
        restaurant_id: RestaurantId,
        location_id: LocationId,
        status: OrderStatus | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[Order], str | None]: ...


class LocationOrders:
    def __init__(
        self,
        order_repository: LocationOrderRepository,
        location_repository: LocationRepository,
    ) -> None:
        self._order_repository = order_repository
        self._location_repository = location_repository

    def execute(
        self,
        restaurant_id: RestaurantId,
        location_id: LocationId,
        *,
        status: str = "ALL",
        limit: int = 50,
        cursor: str | None = None,
    ) -> LocationOrdersResponse:
        location = self._location_repository.get_location(
            restaurant_id=restaurant_id,
            location_id=location_id,
        )
        if location is None:
            raise LocationNotFoundError(
                f"location not found for restaurant_id={restaurant_id}, location_id={location_id}"
            )

        normalized_status = status.upper()
        if normalized_status not in _STATUS_MAP:
            raise InvalidLocationOrdersStatusError(f"invalid location orders status: {status}")
        if limit < 1 or limit > 200:
            raise InvalidLocationOrdersStatusError("limit must be between 1 and 200")

        try:
            orders, next_cursor = self._order_repository.list_for_location(
                restaurant_id=restaurant_id,
                location_id=location_id,
                status=_STATUS_MAP[normalized_status],
                limit=limit,
                cursor=cursor,
            )
        except InvalidCursorError as exc:
            raise InvalidLocationOrdersCursorError("invalid cursor") from exc

        return LocationOrdersResponse(
            orders=[to_order_response(order) for order in orders],
            nextCursor=next_cursor,
        )
