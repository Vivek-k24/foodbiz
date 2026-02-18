from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from rop.application.dto.requests import PlaceOrderLineRequest, PlaceOrderRequest
from rop.application.use_cases.accept_order import (
    AcceptOrder,
)
from rop.application.use_cases.accept_order import (
    InvalidOrderTransitionError as AcceptTransitionError,
)
from rop.application.use_cases.context import TraceContext
from rop.application.use_cases.mark_order_ready import (
    InvalidOrderTransitionError as ReadyTransitionError,
)
from rop.application.use_cases.mark_order_ready import (
    MarkOrderReady,
)
from rop.application.use_cases.place_order import PlaceOrder
from rop.domain.common.ids import MenuId, MenuItemId, OrderId, RestaurantId, TableId
from rop.domain.common.money import Money
from rop.domain.menu.entities import Menu, MenuItem
from rop.domain.order.entities import Order
from rop.domain.table.entities import Table, TableStatus


class FakeMenuRepository:
    def __init__(self, menu: Menu | None) -> None:
        self._menu = menu

    def get_menu_by_restaurant_id(self, restaurant_id: RestaurantId) -> Menu | None:
        return self._menu


class FakeTableRepository:
    def __init__(self, table: Table) -> None:
        self._table = table

    def get(self, table_id: TableId, restaurant_id: RestaurantId) -> Table | None:
        return self._table

    def upsert(self, table: Table) -> None:
        self._table = table


class FakeOrderRepository:
    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def add(self, order: Order) -> None:
        self._orders[str(order.order_id)] = order

    def get(self, order_id) -> Order | None:
        return self._orders.get(str(order_id))

    def update(self, order: Order) -> None:
        self._orders[str(order.order_id)] = order


class FakePublisher:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def publish(self, channel: str, message: str) -> None:
        self.messages.append((channel, message))


def _open_table() -> Table:
    return Table(
        table_id=TableId("tbl_001"),
        restaurant_id=RestaurantId("rst_001"),
        status=TableStatus.OPEN,
        opened_at=datetime.now(timezone.utc),
        closed_at=None,
    )


def _menu() -> Menu:
    return Menu(
        menu_id=MenuId("men_001"),
        restaurant_id=RestaurantId("rst_001"),
        version=1,
        categories=[],
        items=[
            MenuItem(
                item_id=MenuItemId("itm_001"),
                name="Margherita Pizza",
                description=None,
                price_money=Money(amount_cents=1450, currency="USD"),
                is_available=True,
            )
        ],
        updated_at=datetime.now(timezone.utc),
    )


def _place_request() -> PlaceOrderRequest:
    return PlaceOrderRequest(lines=[PlaceOrderLineRequest(item_id="itm_001", quantity=1)])


def test_order_use_case_transitions_and_publishes() -> None:
    order_repository = FakeOrderRepository()
    publisher = FakePublisher()

    placed = PlaceOrder(
        menu_repository=FakeMenuRepository(_menu()),
        table_repository=FakeTableRepository(_open_table()),
        order_repository=order_repository,
        publisher=publisher,
    ).execute(
        restaurant_id=RestaurantId("rst_001"),
        table_id=TableId("tbl_001"),
        request_dto=_place_request(),
        trace_ctx=TraceContext(trace_id="trace-1", request_id="req-1"),
    )
    assert placed.status == "PLACED"

    accepted = AcceptOrder(order_repository=order_repository, publisher=publisher).execute(
        order_id=OrderId(placed.orderId),
        trace_ctx=TraceContext(trace_id="trace-2", request_id="req-2"),
    )
    assert accepted.status == "ACCEPTED"

    ready = MarkOrderReady(order_repository=order_repository, publisher=publisher).execute(
        order_id=OrderId(accepted.orderId),
        trace_ctx=TraceContext(trace_id="trace-3", request_id="req-3"),
    )
    assert ready.status == "READY"

    event_types = [json.loads(message)["event_type"] for _, message in publisher.messages]
    assert event_types == ["order.placed", "order.accepted", "order.ready"]
    assert all(channel == "events:rst_001" for channel, _ in publisher.messages)


def test_invalid_transitions_raise() -> None:
    order_repository = FakeOrderRepository()
    publisher = FakePublisher()
    placed = PlaceOrder(
        menu_repository=FakeMenuRepository(_menu()),
        table_repository=FakeTableRepository(_open_table()),
        order_repository=order_repository,
        publisher=publisher,
    ).execute(
        restaurant_id=RestaurantId("rst_001"),
        table_id=TableId("tbl_001"),
        request_dto=_place_request(),
        trace_ctx=TraceContext(trace_id=None, request_id=None),
    )

    with pytest.raises(ReadyTransitionError):
        MarkOrderReady(order_repository=order_repository, publisher=publisher).execute(
            order_id=OrderId(placed.orderId),
            trace_ctx=TraceContext(trace_id=None, request_id=None),
        )

    accepted = AcceptOrder(order_repository=order_repository, publisher=publisher).execute(
        order_id=OrderId(placed.orderId),
        trace_ctx=TraceContext(trace_id=None, request_id=None),
    )
    with pytest.raises(AcceptTransitionError):
        AcceptOrder(order_repository=order_repository, publisher=publisher).execute(
            order_id=OrderId(accepted.orderId),
            trace_ctx=TraceContext(trace_id=None, request_id=None),
        )
