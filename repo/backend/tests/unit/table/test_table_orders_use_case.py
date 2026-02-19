from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from rop.application.ports.repositories import InvalidCursorError, TableOrderSummaryData
from rop.application.use_cases.open_table import TableNotFoundError
from rop.application.use_cases.table_orders import (
    InvalidTableOrdersCursorError,
    InvalidTableOrdersStatusError,
    TableOrders,
)
from rop.domain.common.ids import MenuItemId, OrderId, OrderLineId, RestaurantId, TableId
from rop.domain.common.money import Money
from rop.domain.order.entities import Order, OrderLine, OrderStatus
from rop.domain.table.entities import Table, TableStatus


class FakeTableRepository:
    def __init__(self, table: Table | None) -> None:
        self._table = table

    def get(self, table_id: TableId, restaurant_id: RestaurantId) -> Table | None:
        return self._table

    def upsert(self, table: Table) -> None:
        self._table = table


class FakeOrderRepository:
    def add(self, order: Order) -> None:
        return None

    def get(self, order_id: OrderId) -> Order | None:
        return None

    def update(self, order: Order) -> None:
        return None

    def get_by_idempotency(
        self,
        restaurant_id: RestaurantId,
        table_id: TableId,
        key: str,
    ) -> Order | None:
        return None

    def add_with_idempotency(self, order: Order, key: str, payload_hash: str) -> Order:
        return order

    def update_status_with_version(
        self,
        order_id: OrderId,
        new_status: OrderStatus,
        expected_version: int,
    ) -> Order:
        raise RuntimeError("not used")

    def list_for_kitchen(
        self,
        restaurant_id: RestaurantId,
        status: OrderStatus | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[Order], str | None]:
        return [], None

    def list_for_table(
        self,
        restaurant_id: RestaurantId,
        table_id: TableId,
        status: OrderStatus | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[Order], str | None]:
        if cursor == "bad":
            raise InvalidCursorError("invalid cursor")
        line = OrderLine(
            line_id=OrderLineId("orl_001"),
            item_id=MenuItemId("itm_001"),
            name="Pizza",
            quantity=1,
            unit_price=Money(amount_cents=1450, currency="USD"),
            line_total=Money(amount_cents=1450, currency="USD"),
            notes=None,
        )
        order = Order(
            order_id=OrderId("ord_001"),
            restaurant_id=restaurant_id,
            table_id=table_id,
            status=status or OrderStatus.PLACED,
            lines=[line],
            total=Money(amount_cents=1450, currency="USD"),
            created_at=datetime.now(timezone.utc),
        )
        return [order], "next-cursor"

    def summarize_for_table(
        self,
        restaurant_id: RestaurantId,
        table_id: TableId,
    ) -> TableOrderSummaryData:
        return TableOrderSummaryData(
            orders_total=0,
            placed=0,
            accepted=0,
            ready=0,
            amount_cents=0,
            currency="USD",
            last_order_at=None,
        )


def _open_table() -> Table:
    return Table(
        table_id=TableId("tbl_001"),
        restaurant_id=RestaurantId("rst_001"),
        status=TableStatus.OPEN,
        opened_at=datetime.now(timezone.utc),
        closed_at=None,
    )


def test_table_orders_returns_orders() -> None:
    payload = TableOrders(
        order_repository=FakeOrderRepository(),
        table_repository=FakeTableRepository(_open_table()),
    ).execute(
        restaurant_id=RestaurantId("rst_001"),
        table_id=TableId("tbl_001"),
        status="ALL",
        limit=50,
        cursor=None,
    )
    assert len(payload.orders) == 1
    assert payload.nextCursor == "next-cursor"


def test_table_orders_rejects_bad_status() -> None:
    with pytest.raises(InvalidTableOrdersStatusError):
        TableOrders(
            order_repository=FakeOrderRepository(),
            table_repository=FakeTableRepository(_open_table()),
        ).execute(
            restaurant_id=RestaurantId("rst_001"),
            table_id=TableId("tbl_001"),
            status="BROKEN",
            limit=50,
            cursor=None,
        )


def test_table_orders_rejects_bad_cursor() -> None:
    with pytest.raises(InvalidTableOrdersCursorError):
        TableOrders(
            order_repository=FakeOrderRepository(),
            table_repository=FakeTableRepository(_open_table()),
        ).execute(
            restaurant_id=RestaurantId("rst_001"),
            table_id=TableId("tbl_001"),
            status="ALL",
            limit=50,
            cursor="bad",
        )


def test_table_orders_requires_existing_table() -> None:
    with pytest.raises(TableNotFoundError):
        TableOrders(
            order_repository=FakeOrderRepository(),
            table_repository=FakeTableRepository(None),
        ).execute(
            restaurant_id=RestaurantId("rst_001"),
            table_id=TableId("tbl_001"),
            status="ALL",
            limit=50,
            cursor=None,
        )
