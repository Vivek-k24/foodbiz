from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum

from rop.domain.common.ids import (
    LocationId,
    MenuItemId,
    OrderId,
    OrderLineId,
    RestaurantId,
    SessionId,
    TableId,
)
from rop.domain.common.location_keys import table_location_id
from rop.domain.common.money import Money
from rop.domain.order.value_objects import OrderLineModifier


class OrderSource(str, Enum):
    WEB_DINE_IN = "WEB_DINE_IN"
    STAFF_CONSOLE = "STAFF_CONSOLE"
    ONLINE_PICKUP = "ONLINE_PICKUP"
    ONLINE_DELIVERY = "ONLINE_DELIVERY"
    KITCHEN_INTERNAL = "KITCHEN_INTERNAL"
    EMPLOYEE_MEAL = "EMPLOYEE_MEAL"
    SYSTEM = "SYSTEM"


class OrderStatus(str, Enum):
    PLACED = "PLACED"
    ACCEPTED = "ACCEPTED"
    READY = "READY"
    SERVED = "SERVED"
    SETTLED = "SETTLED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class OrderLine:
    line_id: OrderLineId
    item_id: MenuItemId
    name: str
    quantity: int
    unit_price: Money
    line_total: Money
    notes: str | None
    modifiers: list[OrderLineModifier] = field(default_factory=list)

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
    status: OrderStatus
    lines: list[OrderLine]
    total: Money
    created_at: datetime
    location_id: LocationId | None = None
    table_id: TableId | None = None
    session_id: SessionId | None = None
    source: OrderSource = OrderSource.WEB_DINE_IN
    updated_at: datetime | None = None
    version: int = 1
    idempotency_key: str | None = None
    idempotency_hash: str | None = None

    def __post_init__(self) -> None:
        if self.location_id is None:
            if self.table_id is None:
                raise ValueError("order must include either location_id or table_id")
            object.__setattr__(self, "location_id", table_location_id(self.table_id))
        if self.updated_at is None:
            object.__setattr__(self, "updated_at", self.created_at)
        if not self.lines:
            raise ValueError("order must contain at least one line")
        if self.version < 1:
            raise ValueError("order version must be >= 1")
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

    def mark_served(self) -> Order:
        if self.status != OrderStatus.READY:
            raise OrderTransitionError(f"cannot mark served from status={self.status.value}")
        return replace(self, status=OrderStatus.SERVED)

    def mark_settled(self) -> Order:
        if self.status != OrderStatus.SERVED:
            raise OrderTransitionError(f"cannot mark settled from status={self.status.value}")
        return replace(self, status=OrderStatus.SETTLED)


def create_placed_order(
    order_id: OrderId,
    restaurant_id: RestaurantId,
    lines: list[OrderLine],
    now: datetime,
    *,
    location_id: LocationId | None = None,
    table_id: TableId | None = None,
    session_id: SessionId | None = None,
    source: OrderSource = OrderSource.WEB_DINE_IN,
    idempotency_key: str | None = None,
    idempotency_hash: str | None = None,
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
        location_id=location_id,
        table_id=table_id,
        session_id=session_id,
        source=source,
        status=OrderStatus.PLACED,
        lines=lines,
        total=total,
        created_at=now,
        updated_at=now,
        version=1,
        idempotency_key=idempotency_key,
        idempotency_hash=idempotency_hash,
    )


class OrderTransitionError(Exception):
    pass
