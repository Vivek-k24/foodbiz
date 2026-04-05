from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from rop.application.ports.repositories import OptimisticConcurrencyError, TableOrderSummaryData
from rop.application.use_cases.context import TraceContext
from rop.application.use_cases.mark_order_settled import (
    InvalidOrderTransitionError,
    MarkOrderSettled,
)
from rop.domain.common.ids import MenuItemId, OrderId, OrderLineId, RestaurantId, TableId
from rop.domain.common.money import Money
from rop.domain.order.entities import Order, OrderLine, OrderStatus


class FakeOrderRepository:
    def __init__(self, order: Order) -> None:
        self._order = order

    def add(self, order: Order) -> None:
        self._order = order

    def get(self, order_id: OrderId) -> Order | None:
        return self._order if self._order.order_id == order_id else None

    def update(self, order: Order) -> None:
        self._order = order

    def get_by_idempotency(
        self,
        restaurant_id: RestaurantId,
        table_id: TableId,
        key: str,
    ) -> Order | None:
        return None

    def add_with_idempotency(self, order: Order, key: str, payload_hash: str) -> Order:
        self._order = order
        return order

    def update_status_with_version(
        self,
        order_id: OrderId,
        new_status: OrderStatus,
        expected_version: int,
    ) -> Order:
        if self._order.order_id != order_id or self._order.version != expected_version:
            raise OptimisticConcurrencyError("version conflict")
        self._order = Order(
            order_id=self._order.order_id,
            restaurant_id=self._order.restaurant_id,
            table_id=self._order.table_id,
            status=new_status,
            lines=self._order.lines,
            total=self._order.total,
            created_at=self._order.created_at,
            version=self._order.version + 1,
            idempotency_key=self._order.idempotency_key,
            idempotency_hash=self._order.idempotency_hash,
        )
        return self._order

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
        return [], None

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


class FakePublisher:
    def __init__(self) -> None:
        self.calls = 0

    def publish(self, channel: str, message: str) -> None:
        self.calls += 1


def _order(status: OrderStatus) -> Order:
    line = OrderLine(
        line_id=OrderLineId("orl_001"),
        item_id=MenuItemId("itm_001"),
        name="Margherita Pizza",
        quantity=1,
        unit_price=Money(amount_cents=1450, currency="USD"),
        line_total=Money(amount_cents=1450, currency="USD"),
        notes=None,
        modifiers=[],
    )
    return Order(
        order_id=OrderId("ord_001"),
        restaurant_id=RestaurantId("rst_001"),
        table_id=TableId("tbl_001"),
        status=status,
        lines=[line],
        total=Money(amount_cents=1450, currency="USD"),
        created_at=datetime.now(timezone.utc),
    )


def test_mark_order_settled_happy_path() -> None:
    repository = FakeOrderRepository(_order(OrderStatus.SERVED))
    publisher = FakePublisher()

    response = MarkOrderSettled(order_repository=repository, publisher=publisher).execute(
        order_id=OrderId("ord_001"),
        trace_ctx=TraceContext(trace_id=None, request_id=None),
    )

    assert response.status == "SETTLED"
    assert publisher.calls == 1


def test_mark_order_settled_rejects_non_served_order() -> None:
    repository = FakeOrderRepository(_order(OrderStatus.READY))

    with pytest.raises(InvalidOrderTransitionError):
        MarkOrderSettled(order_repository=repository, publisher=FakePublisher()).execute(
            order_id=OrderId("ord_001"),
            trace_ctx=TraceContext(trace_id=None, request_id=None),
        )
