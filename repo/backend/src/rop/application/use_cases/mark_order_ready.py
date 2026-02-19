from __future__ import annotations

from datetime import datetime, timezone

from rop.application.dto.responses import OrderResponse
from rop.application.mappers.event_envelope import serialize_order_event
from rop.application.mappers.order_mapper import to_order_response
from rop.application.metrics.order_lifecycle import (
    record_order_status,
    record_time_to_ready,
    record_transition,
)
from rop.application.ports.publisher import EventPublisher
from rop.application.ports.repositories import OptimisticConcurrencyError, OrderRepository
from rop.application.use_cases.context import TraceContext
from rop.domain.common.ids import OrderId
from rop.domain.order.entities import OrderStatus, OrderTransitionError
from rop.domain.order.events import OrderReady


class OrderNotFoundError(Exception):
    pass


class InvalidOrderTransitionError(Exception):
    pass


class OrderConflictError(Exception):
    pass


class MarkOrderReady:
    def __init__(self, order_repository: OrderRepository, publisher: EventPublisher) -> None:
        self._order_repository = order_repository
        self._publisher = publisher

    def execute(self, order_id: OrderId, trace_ctx: TraceContext) -> OrderResponse:
        order = self._order_repository.get(order_id)
        if order is None:
            raise OrderNotFoundError(f"order {order_id} not found")

        if order.status == OrderStatus.READY:
            return to_order_response(order)
        if order.status == OrderStatus.PLACED:
            raise InvalidOrderTransitionError("cannot mark ready from status=PLACED")

        try:
            ready_order = order.mark_ready()
        except OrderTransitionError as exc:
            raise InvalidOrderTransitionError(str(exc)) from exc

        try:
            persisted_order = self._order_repository.update_status_with_version(
                order_id=ready_order.order_id,
                new_status=OrderStatus.READY,
                expected_version=order.version,
            )
        except OptimisticConcurrencyError:
            current = self._order_repository.get(order_id)
            if current is None:
                raise OrderNotFoundError(f"order {order_id} not found")
            if current.status == OrderStatus.READY:
                return to_order_response(current)
            if current.status == OrderStatus.PLACED:
                raise InvalidOrderTransitionError("cannot mark ready from status=PLACED")
            raise OrderConflictError(f"order {order_id} status update conflict")

        event = OrderReady(
            order_id=persisted_order.order_id,
            restaurant_id=persisted_order.restaurant_id,
            table_id=persisted_order.table_id,
            occurred_at=datetime.now(timezone.utc),
        )
        message = serialize_order_event(
            event_type="order.ready",
            occurred_at=event.occurred_at,
            order=persisted_order,
            trace_id=trace_ctx.trace_id,
            request_id=trace_ctx.request_id,
        )
        record_transition(from_status=order.status, to_status=OrderStatus.READY)
        record_order_status(persisted_order)
        record_time_to_ready(persisted_order, now=event.occurred_at)
        try:
            self._publisher.publish(
                channel=f"events:{persisted_order.restaurant_id}",
                message=message,
            )
        except Exception:
            pass

        return to_order_response(persisted_order)
