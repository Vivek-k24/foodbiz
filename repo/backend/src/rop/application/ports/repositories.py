from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from rop.domain.common.ids import (
    LocationId,
    OrderEventId,
    OrderId,
    RestaurantId,
    RoleId,
    SessionId,
    TableId,
)
from rop.domain.location.entities import Location, LocationType
from rop.domain.menu.entities import Menu
from rop.domain.order.entities import Order, OrderSource, OrderStatus
from rop.domain.restaurant.entities import Restaurant
from rop.domain.role.entities import RoleDefinition
from rop.domain.session.entities import Session, SessionStatus
from rop.domain.table.entities import Table, TableStatus


class MenuRepository(Protocol):
    def get_menu_by_restaurant_id(self, restaurant_id: RestaurantId) -> Menu | None: ...


class RestaurantRepository(Protocol):
    def list_restaurants(self) -> list[Restaurant]: ...

    def get_restaurant(self, restaurant_id: RestaurantId) -> Restaurant | None: ...


class LocationRepository(Protocol):
    def list_for_restaurant(
        self,
        restaurant_id: RestaurantId,
        location_type: LocationType | None,
        is_active: bool | None,
        session_status: SessionStatus | None,
    ) -> list[LocationRowData]: ...

    def get_location(
        self, restaurant_id: RestaurantId, location_id: LocationId
    ) -> Location | None: ...


class SessionRepository(Protocol):
    def open_session(
        self,
        restaurant_id: RestaurantId,
        location_id: LocationId,
        opened_by_role_id: RoleId | None,
        opened_by_source: str | None,
        notes: str | None,
    ) -> Session: ...

    def close_session(self, session_id: SessionId) -> Session | None: ...

    def get_session(self, session_id: SessionId) -> Session | None: ...

    def get_active_for_location(
        self,
        restaurant_id: RestaurantId,
        location_id: LocationId,
    ) -> Session | None: ...

    def list_sessions(
        self,
        restaurant_id: RestaurantId,
        location_id: LocationId | None,
        status: SessionStatus | None,
    ) -> list[Session]: ...


class TableRepository(Protocol):
    def get(self, table_id: TableId, restaurant_id: RestaurantId) -> Table | None: ...

    def upsert(self, table: Table) -> None: ...

    def restaurant_exists(self, restaurant_id: RestaurantId) -> bool: ...

    def get_active_session_id(
        self, table_id: TableId, restaurant_id: RestaurantId
    ) -> SessionId | None: ...

    def list_for_restaurant(
        self,
        restaurant_id: RestaurantId,
        status: TableStatus | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[TableRegistryRowData], str | None]: ...


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

    def append_event(self, event: OrderEventRecord) -> None: ...

    def list_events(
        self,
        restaurant_id: RestaurantId,
        order_id: OrderId | None = None,
    ) -> list[OrderEventRecord]: ...


class RoleRepository(Protocol):
    def list_roles(self) -> list[RoleDefinition]: ...


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
    served: int = 0
    settled: int = 0


@dataclass(frozen=True)
class TableRegistryRowData:
    table: Table
    summary: TableOrderSummaryData


@dataclass(frozen=True)
class LocationRowData:
    location: Location
    session_status: SessionStatus | None
    active_session_id: SessionId | None
    last_session_opened_at: datetime | None


@dataclass(frozen=True)
class OrderEventRecord:
    event_id: OrderEventId
    order_id: OrderId
    restaurant_id: RestaurantId
    location_id: LocationId
    session_id: SessionId | None
    event_type: str
    order_status_after: OrderStatus
    triggered_by_source: OrderSource
    created_at: datetime
    metadata: dict[str, object] | None = None
