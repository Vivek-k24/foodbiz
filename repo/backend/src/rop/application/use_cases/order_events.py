from __future__ import annotations

from rop.application.dto.responses import OrderEventResponse
from rop.application.mappers.foundation_mapper import to_order_event_response
from rop.application.ports.repositories import OrderRepository
from rop.domain.common.ids import OrderId, RestaurantId


class ListOrderEvents:
    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    def execute(
        self,
        *,
        restaurant_id: RestaurantId,
        order_id: OrderId | None,
    ) -> list[OrderEventResponse]:
        return [
            to_order_event_response(event)
            for event in self._repository.list_events(
                restaurant_id=restaurant_id,
                order_id=order_id,
            )
        ]
