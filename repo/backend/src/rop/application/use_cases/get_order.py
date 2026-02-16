from __future__ import annotations

from rop.application.dto.responses import OrderResponse
from rop.application.mappers.order_mapper import to_order_response
from rop.application.ports.repositories import OrderRepository
from rop.domain.common.ids import OrderId


class OrderNotFoundError(Exception):
    pass


class GetOrder:
    def __init__(self, order_repository: OrderRepository) -> None:
        self._order_repository = order_repository

    def execute(self, order_id: OrderId) -> OrderResponse:
        order = self._order_repository.get(order_id)
        if order is None:
            raise OrderNotFoundError(f"order {order_id} not found")
        return to_order_response(order)
