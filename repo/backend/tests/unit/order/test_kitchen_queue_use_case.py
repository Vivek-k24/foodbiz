from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from rop.application.ports.repositories import InvalidCursorError
from rop.application.use_cases.kitchen_queue import (
    InvalidKitchenQueueCursorError,
    InvalidKitchenQueueStatusError,
    KitchenQueue,
)
from rop.domain.common.ids import MenuItemId, OrderId, OrderLineId, RestaurantId, TableId
from rop.domain.common.money import Money
from rop.domain.order.entities import Order, OrderLine, OrderStatus


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
        raise RuntimeError("not implemented")

    def list_for_kitchen(
        self,
        restaurant_id: RestaurantId,
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
            restaurant_id=RestaurantId("rst_001"),
            table_id=TableId("tbl_001"),
            status=status or OrderStatus.PLACED,
            lines=[line],
            total=Money(amount_cents=1450, currency="USD"),
            created_at=datetime.now(timezone.utc),
        )
        return [order], "next-cursor"


def test_kitchen_queue_returns_orders() -> None:
    payload = KitchenQueue(order_repository=FakeOrderRepository()).execute(
        restaurant_id=RestaurantId("rst_001"),
        status="PLACED",
        limit=50,
        cursor=None,
    )
    assert len(payload.orders) == 1
    assert payload.orders[0].status == "PLACED"
    assert payload.nextCursor == "next-cursor"


def test_kitchen_queue_rejects_invalid_status() -> None:
    with pytest.raises(InvalidKitchenQueueStatusError):
        KitchenQueue(order_repository=FakeOrderRepository()).execute(
            restaurant_id=RestaurantId("rst_001"),
            status="BROKEN",
            limit=50,
            cursor=None,
        )


def test_kitchen_queue_rejects_invalid_cursor() -> None:
    with pytest.raises(InvalidKitchenQueueCursorError):
        KitchenQueue(order_repository=FakeOrderRepository()).execute(
            restaurant_id=RestaurantId("rst_001"),
            status="PLACED",
            limit=50,
            cursor="bad",
        )
