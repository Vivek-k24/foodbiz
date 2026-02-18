from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum

from rop.domain.common.ids import MenuItemId, OrderId, OrderLineId, RestaurantId, TableId
from rop.domain.common.money import Money


class OrderStatus(str, Enum):
    PLACED = "PLACED"
    ACCEPTED = "ACCEPTED"
    READY = "READY"


@dataclass(frozen=True)
class OrderLine:
    line_id: OrderLineId
    item_id: MenuItemId
    name: str
    quantity: int
    unit_price: Money
    line_total: Money
    notes: str | None

    def __post_init__(self) -> None:
        if self.quantity < 1:
            raise ValueError("quantity must be >= 1")
        if self.unit_price.currency != self.line_total.currency:
            raise ValueError("line_total currency must match unit_price currency")
        expected_total = self.unit_price.amount_cents * self.quantity
        if self.line_total.amount_cents != expected_total:
            raise ValueError("line_total must equal unit_price * quantity")


@dataclass(frozen=True)
class Order:
    order_id: OrderId
    restaurant_id: RestaurantId
    table_id: TableId
    status: OrderStatus
    lines: list[OrderLine]
    total: Money
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.lines:
            raise ValueError("order must contain at least one line")
        line_currency = self.lines[0].line_total.currency
        if self.total.currency != line_currency:
            raise ValueError("order total currency must match line currency")
        expected_total = sum(line.line_total.amount_cents for line in self.lines)
        if self.total.amount_cents != expected_total:
            raise ValueError("order total must equal sum of line totals")

    def accept(self) -> Order:
        if self.status != OrderStatus.PLACED:
            raise OrderTransitionError(f"cannot accept order from status={self.status.value}")
        return replace(self, status=OrderStatus.ACCEPTED)

    def mark_ready(self) -> Order:
        if self.status != OrderStatus.ACCEPTED:
            raise OrderTransitionError(f"cannot mark ready from status={self.status.value}")
        return replace(self, status=OrderStatus.READY)


def create_placed_order(
    order_id: OrderId,
    restaurant_id: RestaurantId,
    table_id: TableId,
    lines: list[OrderLine],
    now: datetime,
) -> Order:
    if not lines:
        raise ValueError("order must contain at least one line")

    currency = lines[0].line_total.currency
    total = Money(
        amount_cents=sum(line.line_total.amount_cents for line in lines),
        currency=currency,
    )
    return Order(
        order_id=order_id,
        restaurant_id=restaurant_id,
        table_id=table_id,
        status=OrderStatus.PLACED,
        lines=lines,
        total=total,
        created_at=now,
    )


class OrderTransitionError(Exception):
    pass
