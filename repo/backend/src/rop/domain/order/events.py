from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from rop.domain.common.ids import LocationId, OrderId, RestaurantId, SessionId, TableId
from rop.domain.common.money import Money
from rop.domain.order.entities import OrderSource


@dataclass(frozen=True)
class OrderPlaced:
    order_id: OrderId
    restaurant_id: RestaurantId
    location_id: LocationId
    table_id: TableId | None
    session_id: SessionId | None
    source: OrderSource
    total: Money
    created_at: datetime


@dataclass(frozen=True)
class OrderAccepted:
    order_id: OrderId
    restaurant_id: RestaurantId
    location_id: LocationId
    table_id: TableId | None
    session_id: SessionId | None
    source: OrderSource
    occurred_at: datetime


@dataclass(frozen=True)
class OrderReady:
    order_id: OrderId
    restaurant_id: RestaurantId
    location_id: LocationId
    table_id: TableId | None
    session_id: SessionId | None
    source: OrderSource
    occurred_at: datetime


@dataclass(frozen=True)
class OrderServed:
    order_id: OrderId
    restaurant_id: RestaurantId
    location_id: LocationId
    table_id: TableId | None
    session_id: SessionId | None
    source: OrderSource
    occurred_at: datetime


@dataclass(frozen=True)
class OrderSettled:
    order_id: OrderId
    restaurant_id: RestaurantId
    location_id: LocationId
    table_id: TableId | None
    session_id: SessionId | None
    source: OrderSource
    occurred_at: datetime
