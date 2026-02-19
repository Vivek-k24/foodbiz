from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from rop.application.ports.repositories import TableOrderSummaryData
from rop.application.use_cases.close_table import (
    CloseTable,
    TableCloseBlockedError,
    TableNotOpenForCloseError,
)
from rop.application.use_cases.context import TraceContext
from rop.domain.common.ids import OrderId, RestaurantId, TableId
from rop.domain.order.entities import Order, OrderStatus
from rop.domain.table.entities import Table, TableStatus


class FakeTableRepository:
    def __init__(self, table: Table | None) -> None:
        self._table = table

    def get(self, table_id: TableId, restaurant_id: RestaurantId) -> Table | None:
        return self._table

    def upsert(self, table: Table) -> None:
        self._table = table


class FakeOrderRepository:
    def __init__(self, summary: TableOrderSummaryData) -> None:
        self._summary = summary

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
        raise RuntimeError("not used in close table tests")

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
        return self._summary


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


def test_close_table_succeeds_when_no_non_ready_orders() -> None:
    table_repo = FakeTableRepository(_open_table())
    order_repo = FakeOrderRepository(
        TableOrderSummaryData(
            orders_total=1,
            placed=0,
            accepted=0,
            ready=1,
            amount_cents=1450,
            currency="USD",
            last_order_at=datetime.now(timezone.utc),
        )
    )
    publisher = FakePublisher()

    payload = CloseTable(
        table_repository=table_repo,
        order_repository=order_repo,
        publisher=publisher,
    ).execute(
        restaurant_id=RestaurantId("rst_001"),
        table_id=TableId("tbl_001"),
        trace_ctx=TraceContext(trace_id=None, request_id="req-1"),
    )

    assert payload.status == "CLOSED"
    assert payload.closedAt is not None
    assert len(publisher.messages) == 1
    assert publisher.messages[0][0] == "events:rst_001"
    assert '"event_type":"table.closed"' in publisher.messages[0][1]


def test_close_table_blocked_when_non_ready_orders_exist() -> None:
    use_case = CloseTable(
        table_repository=FakeTableRepository(_open_table()),
        order_repository=FakeOrderRepository(
            TableOrderSummaryData(
                orders_total=2,
                placed=1,
                accepted=1,
                ready=0,
                amount_cents=2900,
                currency="USD",
                last_order_at=datetime.now(timezone.utc),
            )
        ),
        publisher=FakePublisher(),
    )

    with pytest.raises(TableCloseBlockedError):
        use_case.execute(
            restaurant_id=RestaurantId("rst_001"),
            table_id=TableId("tbl_001"),
            trace_ctx=TraceContext(trace_id=None, request_id="req-1"),
        )


def test_close_table_rejects_non_open_table() -> None:
    closed_table = Table(
        table_id=TableId("tbl_001"),
        restaurant_id=RestaurantId("rst_001"),
        status=TableStatus.CLOSED,
        opened_at=datetime.now(timezone.utc),
        closed_at=datetime.now(timezone.utc),
    )
    use_case = CloseTable(
        table_repository=FakeTableRepository(closed_table),
        order_repository=FakeOrderRepository(
            TableOrderSummaryData(
                orders_total=0,
                placed=0,
                accepted=0,
                ready=0,
                amount_cents=0,
                currency="USD",
                last_order_at=None,
            )
        ),
        publisher=FakePublisher(),
    )

    with pytest.raises(TableNotOpenForCloseError):
        use_case.execute(
            restaurant_id=RestaurantId("rst_001"),
            table_id=TableId("tbl_001"),
            trace_ctx=TraceContext(trace_id=None, request_id="req-1"),
        )
