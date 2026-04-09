from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from rop.domain.commerce.enums import (
    Channel,
    LocationType,
    OrderStatus,
    RestaurantStatus,
    SessionStatus,
    SourceType,
    TableStatus,
)


class CommerceBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RestaurantCreateRequest(CommerceBaseModel):
    slug: str = Field(min_length=2, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    status: RestaurantStatus = RestaurantStatus.ACTIVE


class RestaurantUpdateRequest(CommerceBaseModel):
    slug: str | None = Field(default=None, min_length=2, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: RestaurantStatus | None = None


class RestaurantResponse(CommerceBaseModel):
    id: str
    slug: str
    name: str
    status: RestaurantStatus
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class RestaurantListResponse(CommerceBaseModel):
    restaurants: list[RestaurantResponse]


class LocationCreateRequest(CommerceBaseModel):
    restaurant_id: str
    name: str = Field(min_length=1, max_length=255)
    location_type: LocationType = LocationType.RESTAURANT
    is_active: bool = True
    supports_dine_in: bool = True
    supports_pickup: bool = True
    supports_delivery: bool = True
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = Field(default="US", min_length=2, max_length=2)


class LocationUpdateRequest(CommerceBaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    location_type: LocationType | None = None
    is_active: bool | None = None
    supports_dine_in: bool | None = None
    supports_pickup: bool | None = None
    supports_delivery: bool | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = Field(default=None, min_length=2, max_length=2)


class LocationResponse(CommerceBaseModel):
    id: str
    restaurant_id: str
    name: str
    location_type: LocationType
    is_active: bool
    supports_dine_in: bool
    supports_pickup: bool
    supports_delivery: bool
    address_line_1: str | None
    address_line_2: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    country: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class LocationListResponse(CommerceBaseModel):
    locations: list[LocationResponse]


class TableCreateRequest(CommerceBaseModel):
    restaurant_id: str
    location_id: str | None = None
    label: str = Field(min_length=1, max_length=50)
    capacity: int | None = Field(default=None, gt=0)
    status: TableStatus = TableStatus.AVAILABLE


class TableUpdateRequest(CommerceBaseModel):
    location_id: str | None = None
    label: str | None = Field(default=None, min_length=1, max_length=50)
    capacity: int | None = Field(default=None, gt=0)
    status: TableStatus | None = None


class TableSessionOpenRequest(CommerceBaseModel):
    source_type: SourceType = SourceType.WAITER_ENTERED
    external_source: str | None = None
    external_reference: str | None = None
    metadata: dict[str, Any] | None = None
    expires_at: datetime | None = None


class TableResponse(CommerceBaseModel):
    id: str
    restaurant_id: str
    location_id: str | None
    label: str
    capacity: int | None
    status: TableStatus
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class SessionCreateRequest(CommerceBaseModel):
    restaurant_id: str
    location_id: str
    channel: Channel
    source_type: SourceType
    table_id: str | None = None
    external_source: str | None = None
    external_reference: str | None = None
    metadata: dict[str, Any] | None = None
    expires_at: datetime | None = None


class SessionUpdateRequest(CommerceBaseModel):
    status: SessionStatus | None = None
    external_source: str | None = None
    external_reference: str | None = None
    metadata: dict[str, Any] | None = None
    expires_at: datetime | None = None


class SessionResponse(CommerceBaseModel):
    id: str
    restaurant_id: str
    location_id: str | None
    channel: Channel
    source_type: SourceType
    status: SessionStatus
    table_id: str | None
    table_label: str | None
    external_source: str | None
    external_reference: str | None
    metadata: dict[str, Any] | None
    started_at: datetime
    expires_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OrderLineRequest(CommerceBaseModel):
    menu_item_id: str
    quantity: int = Field(gt=0)
    notes: str | None = None


class OrderCreateRequest(CommerceBaseModel):
    restaurant_id: str
    session_id: str
    location_id: str | None = None
    table_id: str | None = None
    notes: str | None = None
    lines: list[OrderLineRequest] = Field(min_length=1)


class OrderUpdateRequest(CommerceBaseModel):
    notes: str | None = None


class OrderLineResponse(CommerceBaseModel):
    id: str
    menu_item_id: str | None
    item_name_snapshot: str
    unit_price_snapshot: float
    quantity: int
    line_total: float
    notes: str | None


class OrderResponse(CommerceBaseModel):
    id: str
    restaurant_id: str
    location_id: str | None
    session_id: str
    table_id: str | None
    table_label: str | None
    channel: Channel
    source_type: SourceType
    status: OrderStatus
    external_source: str | None
    external_reference: str | None
    subtotal: float
    discount_total: float
    tax_total: float
    total: float
    notes: str | None
    idempotency_key: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    lines: list[OrderLineResponse]
