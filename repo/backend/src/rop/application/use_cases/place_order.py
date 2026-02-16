from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from rop.application.dto.requests import PlaceOrderRequest
from rop.application.dto.responses import OrderResponse
from rop.application.mappers.events import to_order_placed_envelope_json
from rop.application.mappers.order_mapper import to_order_response
from rop.application.ports.publisher import EventPublisher
from rop.application.ports.repositories import MenuRepository, OrderRepository, TableRepository
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


@dataclass(frozen=True)
class TraceContext:
    trace_id: str | None
    request_id: str | None


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
        order = create_placed_order(
            order_id=OrderId(f"ord_{uuid4().hex[:12]}"),
            restaurant_id=restaurant_id,
            table_id=table_id,
            lines=order_lines,
            now=now,
        )
        self._order_repository.add(order)

        event = OrderPlaced(
            order_id=order.order_id,
            restaurant_id=order.restaurant_id,
            table_id=order.table_id,
            total=order.total,
            created_at=order.created_at,
        )
        message = to_order_placed_envelope_json(
            event=event,
            order=order,
            trace_id=trace_ctx.trace_id,
            request_id=trace_ctx.request_id,
        )
        try:
            self._publisher.publish(channel=f"events:{restaurant_id}", message=message)
        except Exception:
            pass

        return to_order_response(order)
