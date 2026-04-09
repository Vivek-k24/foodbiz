from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from rop.application.dto.responses import OrderResponse
from rop.application.mappers.event_envelope import serialize_order_event
from rop.application.mappers.order_mapper import to_order_response
from rop.application.metrics.order_lifecycle import record_order_status, record_transition
from rop.application.ports.publisher import EventPublisher
from rop.application.ports.repositories import (
    OptimisticConcurrencyError,
    OrderEventRecord,
    OrderRepository,
    SessionRepository,
)
from rop.application.use_cases.context import TraceContext
from rop.domain.common.ids import OrderEventId, OrderId
from rop.domain.order.entities import OrderSource, OrderStatus, OrderTransitionError
from rop.domain.order.events import OrderSettled


class OrderNotFoundError(Exception):
    pass


class InvalidOrderTransitionError(Exception):
    pass


class OrderConflictError(Exception):
    pass


class MarkOrderSettled:
    def __init__(
        self,
        order_repository: OrderRepository,
        publisher: EventPublisher,
        session_repository: SessionRepository | None = None,
    ) -> None:
        self._order_repository = order_repository
        self._publisher = publisher
        self._session_repository = session_repository

    def execute(self, order_id: OrderId, trace_ctx: TraceContext) -> OrderResponse:
        order = self._order_repository.get(order_id)
        if order is None:
            raise OrderNotFoundError(f"order {order_id} not found")

        if order.status == OrderStatus.SETTLED:
            return to_order_response(order)
        if order.status != OrderStatus.SERVED:
            raise InvalidOrderTransitionError(
                f"cannot mark settled from status={order.status.value}"
            )

        try:
            settled_order = order.mark_settled()
        except OrderTransitionError as exc:
            raise InvalidOrderTransitionError(str(exc)) from exc

        try:
            persisted_order = self._order_repository.update_status_with_version(
                order_id=settled_order.order_id,
                new_status=OrderStatus.SETTLED,
                expected_version=order.version,
            )
        except OptimisticConcurrencyError:
            current = self._order_repository.get(order_id)
            if current is None:
                raise OrderNotFoundError(f"order {order_id} not found")
            if current.status == OrderStatus.SETTLED:
                return to_order_response(current)
            if current.status != OrderStatus.SERVED:
                raise InvalidOrderTransitionError(
                    f"cannot mark settled from status={current.status.value}"
                )
            raise OrderConflictError(f"order {order_id} status update conflict")

        location_id = persisted_order.location_id
        assert location_id is not None
        event = OrderSettled(
            order_id=persisted_order.order_id,
            restaurant_id=persisted_order.restaurant_id,
            location_id=location_id,
            table_id=persisted_order.table_id,
            session_id=persisted_order.session_id,
            source=OrderSource.STAFF_CONSOLE,
            occurred_at=datetime.now(timezone.utc),
        )
        append_event = getattr(self._order_repository, "append_event", None)
        if callable(append_event):
            append_event(
                OrderEventRecord(
                    event_id=OrderEventId(f"evt_{uuid4().hex[:12]}"),
                    order_id=persisted_order.order_id,
                    restaurant_id=persisted_order.restaurant_id,
                    location_id=location_id,
                    session_id=persisted_order.session_id,
                    event_type="ORDER_SETTLED",
                    order_status_after=OrderStatus.SETTLED,
                    triggered_by_source=OrderSource.STAFF_CONSOLE,
                    created_at=event.occurred_at,
                    metadata={"request_id": trace_ctx.request_id, "trace_id": trace_ctx.trace_id},
                )
            )
        message = serialize_order_event(
            event_type="order.settled",
            occurred_at=event.occurred_at,
            order=persisted_order,
            trace_id=trace_ctx.trace_id,
            request_id=trace_ctx.request_id,
        )
        record_transition(from_status=order.status, to_status=OrderStatus.SETTLED)
        record_order_status(persisted_order)
        if (
            self._session_repository is not None
            and persisted_order.session_id is not None
            and persisted_order.source in {OrderSource.ONLINE_PICKUP, OrderSource.ONLINE_DELIVERY}
        ):
            self._session_repository.close_session(persisted_order.session_id)
        try:
            self._publisher.publish(
                channel=f"events:{persisted_order.restaurant_id}",
                message=message,
            )
        except Exception:
            pass

        return to_order_response(persisted_order)
