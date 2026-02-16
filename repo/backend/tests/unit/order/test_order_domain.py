from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from rop.domain.common.ids import MenuItemId, OrderId, OrderLineId, RestaurantId, TableId
from rop.domain.common.money import Money
from rop.domain.order.entities import Order, OrderLine, OrderStatus, create_placed_order


def test_order_line_quantity_must_be_gte_one() -> None:
    with pytest.raises(ValueError):
        OrderLine(
            line_id=OrderLineId("orl_001"),
            item_id=MenuItemId("itm_001"),
            name="Item",
            quantity=0,
            unit_price=Money(amount_cents=100, currency="USD"),
            line_total=Money(amount_cents=0, currency="USD"),
            notes=None,
        )


def test_order_total_must_match_lines() -> None:
    line = OrderLine(
        line_id=OrderLineId("orl_001"),
        item_id=MenuItemId("itm_001"),
        name="Item",
        quantity=1,
        unit_price=Money(amount_cents=100, currency="USD"),
        line_total=Money(amount_cents=100, currency="USD"),
        notes=None,
    )
    with pytest.raises(ValueError):
        Order(
            order_id=OrderId("ord_001"),
            restaurant_id=RestaurantId("rst_001"),
            table_id=TableId("tbl_001"),
            status=OrderStatus.PLACED,
            lines=[line],
            total=Money(amount_cents=90, currency="USD"),
            created_at=datetime.now(timezone.utc),
        )


def test_create_placed_order_calculates_total() -> None:
    now = datetime.now(timezone.utc)
    lines = [
        OrderLine(
            line_id=OrderLineId("orl_001"),
            item_id=MenuItemId("itm_001"),
            name="Item 1",
            quantity=2,
            unit_price=Money(amount_cents=300, currency="USD"),
            line_total=Money(amount_cents=600, currency="USD"),
            notes=None,
        ),
        OrderLine(
            line_id=OrderLineId("orl_002"),
            item_id=MenuItemId("itm_002"),
            name="Item 2",
            quantity=1,
            unit_price=Money(amount_cents=250, currency="USD"),
            line_total=Money(amount_cents=250, currency="USD"),
            notes=None,
        ),
    ]
    order = create_placed_order(
        order_id=OrderId("ord_001"),
        restaurant_id=RestaurantId("rst_001"),
        table_id=TableId("tbl_001"),
        lines=lines,
        now=now,
    )

    assert order.total.amount_cents == 850
    assert order.total.currency == "USD"
