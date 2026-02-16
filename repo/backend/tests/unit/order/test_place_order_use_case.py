from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from rop.application.dto.requests import PlaceOrderLineRequest, PlaceOrderRequest
from rop.application.use_cases.place_order import (
    MenuItemUnavailableError,
    PlaceOrder,
    TableNotOpenError,
    TraceContext,
)
from rop.domain.common.ids import MenuId, MenuItemId, RestaurantId, TableId
from rop.domain.common.money import Money
from rop.domain.menu.entities import Menu, MenuItem
from rop.domain.order.entities import Order
from rop.domain.table.entities import Table, TableStatus


class FakeMenuRepository:
    def __init__(self, menu: Menu | None):
        self._menu = menu

    def get_menu_by_restaurant_id(self, restaurant_id: RestaurantId) -> Menu | None:
        return self._menu


class FakeTableRepository:
    def __init__(self, table: Table | None):
        self._table = table

    def get(self, table_id: TableId, restaurant_id: RestaurantId) -> Table | None:
        return self._table

    def upsert(self, table: Table) -> None:
        self._table = table


class FakeOrderRepository:
    def __init__(self) -> None:
        self.saved_order: Order | None = None

    def add(self, order: Order) -> None:
        self.saved_order = order

    def get(self, order_id):
        return self.saved_order


@dataclass
class PublishCall:
    channel: str
    message: str


class FakePublisher:
    def __init__(self) -> None:
        self.calls: list[PublishCall] = []

    def publish(self, channel: str, message: str) -> None:
        self.calls.append(PublishCall(channel=channel, message=message))


def _sample_menu(item_available: bool = True) -> Menu:
    return Menu(
        menu_id=MenuId("men_001"),
        restaurant_id=RestaurantId("rst_001"),
        version=1,
        categories=[],
        items=[
            MenuItem(
                item_id=MenuItemId("itm_001"),
                name="Pizza",
                description=None,
                price_money=Money(amount_cents=1450, currency="USD"),
                is_available=item_available,
            )
        ],
        updated_at=datetime.now(timezone.utc),
    )


def _table(status: TableStatus) -> Table:
    now = datetime.now(timezone.utc)
    return Table(
        table_id=TableId("tbl_001"),
        restaurant_id=RestaurantId("rst_001"),
        status=status,
        opened_at=now,
        closed_at=now if status == TableStatus.CLOSED else None,
    )


def _request(quantity: int = 1) -> PlaceOrderRequest:
    return PlaceOrderRequest(lines=[PlaceOrderLineRequest(item_id="itm_001", quantity=quantity)])


def test_place_order_rejects_closed_table() -> None:
    use_case = PlaceOrder(
        menu_repository=FakeMenuRepository(_sample_menu()),
        table_repository=FakeTableRepository(_table(TableStatus.CLOSED)),
        order_repository=FakeOrderRepository(),
        publisher=FakePublisher(),
    )
    with pytest.raises(TableNotOpenError):
        use_case.execute(
            restaurant_id=RestaurantId("rst_001"),
            table_id=TableId("tbl_001"),
            request_dto=_request(),
            trace_ctx=TraceContext(trace_id=None, request_id=None),
        )


def test_place_order_rejects_unavailable_item() -> None:
    use_case = PlaceOrder(
        menu_repository=FakeMenuRepository(_sample_menu(item_available=False)),
        table_repository=FakeTableRepository(_table(TableStatus.OPEN)),
        order_repository=FakeOrderRepository(),
        publisher=FakePublisher(),
    )
    with pytest.raises(MenuItemUnavailableError):
        use_case.execute(
            restaurant_id=RestaurantId("rst_001"),
            table_id=TableId("tbl_001"),
            request_dto=_request(),
            trace_ctx=TraceContext(trace_id=None, request_id=None),
        )


def test_place_order_happy_path_persists_and_publishes() -> None:
    order_repository = FakeOrderRepository()
    publisher = FakePublisher()
    use_case = PlaceOrder(
        menu_repository=FakeMenuRepository(_sample_menu()),
        table_repository=FakeTableRepository(_table(TableStatus.OPEN)),
        order_repository=order_repository,
        publisher=publisher,
    )

    response = use_case.execute(
        restaurant_id=RestaurantId("rst_001"),
        table_id=TableId("tbl_001"),
        request_dto=_request(quantity=2),
        trace_ctx=TraceContext(trace_id="trace-1", request_id="req-1"),
    )

    assert response.total.amountCents == 2900
    assert order_repository.saved_order is not None
    assert len(publisher.calls) == 1
    assert publisher.calls[0].channel == "events:rst_001"
    assert '"event_type":"order.placed"' in publisher.calls[0].message
