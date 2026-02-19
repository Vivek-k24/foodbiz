from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from rop.domain.common.ids import OrderId, RestaurantId, TableId
from rop.domain.menu.entities import Menu
from rop.domain.order.entities import Order, OrderStatus
from rop.domain.table.entities import Table


class MenuRepository(Protocol):
    def get_menu_by_restaurant_id(self, restaurant_id: RestaurantId) -> Menu | None: ...


class TableRepository(Protocol):
    def get(self, table_id: TableId, restaurant_id: RestaurantId) -> Table | None: ...

    def upsert(self, table: Table) -> None: ...


class OrderRepository(Protocol):
    def add(self, order: Order) -> None: ...

    def get(self, order_id: OrderId) -> Order | None: ...

    def update(self, order: Order) -> None: ...

    def get_by_idempotency(
        self,
        restaurant_id: RestaurantId,
        table_id: TableId,
        key: str,
    ) -> Order | None: ...

    def add_with_idempotency(
        self,
        order: Order,
        key: str,
        payload_hash: str,
    ) -> Order: ...

    def update_status_with_version(
        self,
        order_id: OrderId,
        new_status: OrderStatus,
        expected_version: int,
    ) -> Order: ...

    def list_for_kitchen(
        self,
        restaurant_id: RestaurantId,
        status: OrderStatus | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[Order], str | None]: ...

    def list_for_table(
        self,
        restaurant_id: RestaurantId,
        table_id: TableId,
        status: OrderStatus | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[Order], str | None]: ...

    def summarize_for_table(
        self,
        restaurant_id: RestaurantId,
        table_id: TableId,
    ) -> TableOrderSummaryData: ...


class IdempotencyReplayMismatchError(Exception):
    pass


class OptimisticConcurrencyError(Exception):
    pass


class InvalidCursorError(Exception):
    pass


@dataclass(frozen=True)
class TableOrderSummaryData:
    orders_total: int
    placed: int
    accepted: int
    ready: int
    amount_cents: int
    currency: str
    last_order_at: datetime | None
