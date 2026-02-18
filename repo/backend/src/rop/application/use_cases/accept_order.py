from __future__ import annotations

from datetime import datetime, timezone

from rop.application.dto.responses import OrderResponse
from rop.application.mappers.event_envelope import serialize_order_event
from rop.application.mappers.order_mapper import to_order_response
from rop.application.ports.publisher import EventPublisher
from rop.application.ports.repositories import OrderRepository
from rop.application.use_cases.context import TraceContext
from rop.domain.common.ids import OrderId
from rop.domain.order.entities import OrderTransitionError
from rop.domain.order.events import OrderAccepted


class OrderNotFoundError(Exception):
    pass


class InvalidOrderTransitionError(Exception):
    pass


class AcceptOrder:
    def __init__(self, order_repository: OrderRepository, publisher: EventPublisher) -> None:
        self._order_repository = order_repository
        self._publisher = publisher

    def execute(self, order_id: OrderId, trace_ctx: TraceContext) -> OrderResponse:
        order = self._order_repository.get(order_id)
        if order is None:
            raise OrderNotFoundError(f"order {order_id} not found")

        try:
            accepted_order = order.accept()
        except OrderTransitionError as exc:
            raise InvalidOrderTransitionError(str(exc)) from exc

        self._order_repository.update(accepted_order)

        event = OrderAccepted(
            order_id=accepted_order.order_id,
            restaurant_id=accepted_order.restaurant_id,
            table_id=accepted_order.table_id,
            occurred_at=datetime.now(timezone.utc),
        )
        message = serialize_order_event(
            event_type="order.accepted",
            occurred_at=event.occurred_at,
            order=accepted_order,
            trace_id=trace_ctx.trace_id,
            request_id=trace_ctx.request_id,
        )
        try:
            self._publisher.publish(
                channel=f"events:{accepted_order.restaurant_id}",
                message=message,
            )
        except Exception:
            pass

        return to_order_response(accepted_order)
