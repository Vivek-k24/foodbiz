from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from rop.application.dto.requests import PlaceOrderRequest
from rop.application.dto.responses import OrderResponse
from rop.application.mappers.event_envelope import serialize_order_event
from rop.application.mappers.order_mapper import to_order_response
from rop.application.metrics.order_lifecycle import record_order_status
from rop.application.ports.publisher import EventPublisher
from rop.application.ports.repositories import (
    IdempotencyReplayMismatchError as RepoIdempotencyReplayMismatchError,
)
from rop.application.ports.repositories import (
    MenuRepository,
    OrderRepository,
    TableRepository,
)
from rop.application.use_cases.context import TraceContext
from rop.domain.common.ids import OrderId, OrderLineId, RestaurantId, TableId
from rop.domain.common.money import Money
from rop.domain.order.entities import OrderLine, create_placed_order
from rop.domain.order.events import OrderPlaced
from rop.domain.table.entities import TableClosedError


class TableNotFoundError(Exception):
    pass


class TableNotOpenError(Exception):
    pass


class MenuNotFoundError(Exception):
    pass


class MenuItemUnavailableError(Exception):
    pass


class IdempotencyReplayMismatchError(Exception):
    pass


class PlaceOrder:
    def __init__(
        self,
        menu_repository: MenuRepository,
        table_repository: TableRepository,
        order_repository: OrderRepository,
        publisher: EventPublisher,
    ) -> None:
        self._menu_repository = menu_repository
        self._table_repository = table_repository
        self._order_repository = order_repository
        self._publisher = publisher

    def execute(
        self,
        restaurant_id: RestaurantId,
        table_id: TableId,
        request_dto: PlaceOrderRequest,
        trace_ctx: TraceContext,
        idempotency_key: str | None = None,
    ) -> OrderResponse:
        table = self._table_repository.get(table_id=table_id, restaurant_id=restaurant_id)
        if table is None:
            raise TableNotFoundError(
                f"table not found for restaurant_id={restaurant_id}, table_id={table_id}"
            )
        try:
            table.ensure_open()
        except TableClosedError as exc:
            raise TableNotOpenError(str(exc)) from exc

        menu = self._menu_repository.get_menu_by_restaurant_id(restaurant_id)
        if menu is None:
            raise MenuNotFoundError(f"menu not found for restaurant_id={restaurant_id}")

        menu_items = {str(item.item_id): item for item in menu.items}
        order_lines: list[OrderLine] = []
        for request_line in request_dto.lines:
            if request_line.quantity < 1:
                raise MenuItemUnavailableError("quantity must be >= 1")

            menu_item = menu_items.get(request_line.item_id)
            if menu_item is None:
                raise MenuItemUnavailableError(f"menu item {request_line.item_id} does not exist")
            if not menu_item.is_available:
                raise MenuItemUnavailableError(f"menu item {request_line.item_id} is unavailable")

            unit_price = menu_item.price_money
            line_total = Money(
                amount_cents=unit_price.amount_cents * request_line.quantity,
                currency=unit_price.currency,
            )
            order_lines.append(
                OrderLine(
                    line_id=OrderLineId(f"orl_{uuid4().hex[:12]}"),
                    item_id=menu_item.item_id,
                    name=menu_item.name,
                    quantity=request_line.quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                    notes=request_line.notes,
                )
            )

        now = datetime.now(timezone.utc)
        payload_hash = _request_hash(request_dto)
        order = create_placed_order(
            order_id=OrderId(f"ord_{uuid4().hex[:12]}"),
            restaurant_id=restaurant_id,
            table_id=table_id,
            lines=order_lines,
            now=now,
            idempotency_key=idempotency_key,
            idempotency_hash=payload_hash if idempotency_key else None,
        )
        created = True
        persisted_order = order
        if idempotency_key:
            try:
                persisted_order = self._order_repository.add_with_idempotency(
                    order=order,
                    key=idempotency_key,
                    payload_hash=payload_hash,
                )
            except RepoIdempotencyReplayMismatchError as exc:
                raise IdempotencyReplayMismatchError(str(exc)) from exc
            created = persisted_order.order_id == order.order_id
        else:
            self._order_repository.add(order)

        if created:
            event = OrderPlaced(
                order_id=persisted_order.order_id,
                restaurant_id=persisted_order.restaurant_id,
                table_id=persisted_order.table_id,
                total=persisted_order.total,
                created_at=persisted_order.created_at,
            )
            message = serialize_order_event(
                event_type="order.placed",
                occurred_at=event.created_at,
                order=persisted_order,
                trace_id=trace_ctx.trace_id,
                request_id=trace_ctx.request_id,
            )
            record_order_status(persisted_order)
            try:
                self._publisher.publish(channel=f"events:{restaurant_id}", message=message)
            except Exception:
                pass

        return to_order_response(persisted_order)


def _request_hash(request_dto: PlaceOrderRequest) -> str:
    normalized_payload = request_dto.model_dump(mode="json", by_alias=True, exclude_none=False)
    canonical = json.dumps(normalized_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
