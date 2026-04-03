from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from rop.application.dto.requests import PlaceOrderLineRequest, PlaceOrderRequest
from rop.application.ports.repositories import (
    IdempotencyReplayMismatchError as RepoIdempotencyReplayMismatchError,
)
from rop.application.ports.repositories import TableOrderSummaryData
from rop.application.use_cases.context import TraceContext
from rop.application.use_cases.place_order import (
    IdempotencyReplayMismatchError,
    MenuItemUnavailableError,
    PlaceOrder,
    TableNotOpenError,
)
from rop.domain.common.ids import MenuId, MenuItemId, RestaurantId, TableId
from rop.domain.common.money import Money
from rop.domain.menu.entities import Menu, MenuItem
from rop.domain.order.entities import Order, OrderStatus
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

    def restaurant_exists(self, restaurant_id: RestaurantId) -> bool:
        return True

    def list_for_restaurant(self, restaurant_id, status, limit, cursor):
        return [], None


class FakeOrderRepository:
    def __init__(self) -> None:
        self.saved_order: Order | None = None
        self.by_idempotency: dict[tuple[str, str, str], tuple[Order, str]] = {}

    def add(self, order: Order) -> None:
        self.saved_order = order

    def get(self, order_id):
        return self.saved_order

    def update(self, order: Order) -> None:
        self.saved_order = order

    def get_by_idempotency(
        self,
        restaurant_id: RestaurantId,
        table_id: TableId,
        key: str,
    ) -> Order | None:
        row = self.by_idempotency.get((str(restaurant_id), str(table_id), key))
        if row is None:
            return None
        return row[0]

    def add_with_idempotency(
        self,
        order: Order,
        key: str,
        payload_hash: str,
    ) -> Order:
        lookup = (str(order.restaurant_id), str(order.table_id), key)
        existing = self.by_idempotency.get(lookup)
        if existing is not None:
            existing_order, existing_hash = existing
            if existing_hash != payload_hash:
                raise RepoIdempotencyReplayMismatchError(
                    f"idempotency key replay with different payload: {key}"
                )
            return existing_order
        self.saved_order = order
        self.by_idempotency[lookup] = (order, payload_hash)
        return order

    def update_status_with_version(
        self,
        order_id,
        new_status: OrderStatus,
        expected_version: int,
    ) -> Order:
        if self.saved_order is None:
            raise RuntimeError("order not found")
        if str(self.saved_order.order_id) != str(order_id):
            raise RuntimeError("order not found")
        if self.saved_order.version != expected_version:
            raise RuntimeError("version conflict")
        self.saved_order = Order(
            order_id=self.saved_order.order_id,
            restaurant_id=self.saved_order.restaurant_id,
            table_id=self.saved_order.table_id,
            status=new_status,
            lines=self.saved_order.lines,
            total=self.saved_order.total,
            created_at=self.saved_order.created_at,
            version=self.saved_order.version + 1,
            idempotency_key=self.saved_order.idempotency_key,
            idempotency_hash=self.saved_order.idempotency_hash,
        )
        return self.saved_order

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


def test_place_order_rejects_non_positive_quantity() -> None:
    use_case = PlaceOrder(
        menu_repository=FakeMenuRepository(_sample_menu()),
        table_repository=FakeTableRepository(_table(TableStatus.OPEN)),
        order_repository=FakeOrderRepository(),
        publisher=FakePublisher(),
    )
    with pytest.raises(MenuItemUnavailableError):
        use_case.execute(
            restaurant_id=RestaurantId("rst_001"),
            table_id=TableId("tbl_001"),
            request_dto=_request(quantity=0),
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


def test_place_order_idempotency_returns_same_order_for_same_payload() -> None:
    order_repository = FakeOrderRepository()
    publisher = FakePublisher()
    use_case = PlaceOrder(
        menu_repository=FakeMenuRepository(_sample_menu()),
        table_repository=FakeTableRepository(_table(TableStatus.OPEN)),
        order_repository=order_repository,
        publisher=publisher,
    )

    first = use_case.execute(
        restaurant_id=RestaurantId("rst_001"),
        table_id=TableId("tbl_001"),
        request_dto=_request(quantity=1),
        trace_ctx=TraceContext(trace_id="trace-1", request_id="req-1"),
        idempotency_key="idem-001",
    )
    second = use_case.execute(
        restaurant_id=RestaurantId("rst_001"),
        table_id=TableId("tbl_001"),
        request_dto=_request(quantity=1),
        trace_ctx=TraceContext(trace_id="trace-2", request_id="req-2"),
        idempotency_key="idem-001",
    )

    assert first.orderId == second.orderId
    assert len(publisher.calls) == 1


def test_place_order_idempotency_replay_mismatch_raises() -> None:
    order_repository = FakeOrderRepository()
    use_case = PlaceOrder(
        menu_repository=FakeMenuRepository(_sample_menu()),
        table_repository=FakeTableRepository(_table(TableStatus.OPEN)),
        order_repository=order_repository,
        publisher=FakePublisher(),
    )

    use_case.execute(
        restaurant_id=RestaurantId("rst_001"),
        table_id=TableId("tbl_001"),
        request_dto=_request(quantity=1),
        trace_ctx=TraceContext(trace_id="trace-1", request_id="req-1"),
        idempotency_key="idem-001",
    )
    with pytest.raises(IdempotencyReplayMismatchError):
        use_case.execute(
            restaurant_id=RestaurantId("rst_001"),
            table_id=TableId("tbl_001"),
            request_dto=_request(quantity=2),
            trace_ctx=TraceContext(trace_id="trace-2", request_id="req-2"),
            idempotency_key="idem-001",
        )
