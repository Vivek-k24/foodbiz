from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MoneyResponse(BaseModel):
    amountCents: int
    currency: str


class AllowedModifierResponse(BaseModel):
    code: str
    label: str
    kind: str
    options: list[str] | None = None


class MenuCategoryResponse(BaseModel):
    categoryId: str
    name: str
    categoryKind: str
    cuisineOrFamily: str


class MenuItemResponse(BaseModel):
    itemId: str
    name: str
    description: str | None = None
    priceMoney: MoneyResponse
    isAvailable: bool
    categoryId: str | None = None
    allowedModifiers: list[AllowedModifierResponse] | None = None


class MenuResponse(BaseModel):
    menuId: str
    restaurantId: str
    menuVersion: int
    categories: list[MenuCategoryResponse] = Field(default_factory=list)
    items: list[MenuItemResponse] = Field(default_factory=list)
    updatedAt: datetime


class OrderLineModifierResponse(BaseModel):
    code: str
    label: str
    value: str


class OrderLineResponse(BaseModel):
    lineId: str
    itemId: str
    name: str
    quantity: int
    unitPrice: MoneyResponse
    lineTotal: MoneyResponse
    notes: str | None = None
    modifiers: list[OrderLineModifierResponse] | None = None


class OrderResponse(BaseModel):
    orderId: str
    restaurantId: str
    locationId: str
    tableId: str | None = None
    sessionId: str | None = None
    source: str
    status: str
    lines: list[OrderLineResponse] = Field(default_factory=list)
    total: MoneyResponse
    createdAt: datetime
    updatedAt: datetime


class OrderEventResponse(BaseModel):
    eventId: str
    orderId: str
    restaurantId: str
    locationId: str
    sessionId: str | None = None
    eventType: str
    orderStatusAfter: str
    triggeredBySource: str
    createdAt: datetime
    metadata: dict[str, object] | None = None


class TableResponse(BaseModel):
    tableId: str
    restaurantId: str
    status: str
    openedAt: datetime | None = None
    closedAt: datetime | None = None


class KitchenQueueResponse(BaseModel):
    orders: list[OrderResponse] = Field(default_factory=list)
    nextCursor: str | None = None


class TableOrdersResponse(BaseModel):
    orders: list[OrderResponse] = Field(default_factory=list)
    nextCursor: str | None = None


class TableSummaryCountsResponse(BaseModel):
    ordersTotal: int
    placed: int
    accepted: int
    ready: int
    served: int
    settled: int


class TableSummaryResponse(BaseModel):
    tableId: str
    restaurantId: str
    status: str
    openedAt: datetime | None = None
    closedAt: datetime | None = None
    totals: MoneyResponse
    counts: TableSummaryCountsResponse
    lastOrderAt: datetime | None = None


class TableRegistryItemResponse(BaseModel):
    tableId: str
    restaurantId: str
    status: str
    openedAt: datetime | None = None
    closedAt: datetime | None = None
    lastOrderAt: datetime | None = None
    totals: MoneyResponse
    counts: TableSummaryCountsResponse


class TableRegistryResponse(BaseModel):
    tables: list[TableRegistryItemResponse] = Field(default_factory=list)
    nextCursor: str | None = None


class RestaurantResponse(BaseModel):
    restaurantId: str
    name: str
    timezone: str
    currency: str
    createdAt: datetime


class RestaurantsResponse(BaseModel):
    restaurants: list[RestaurantResponse] = Field(default_factory=list)


class LocationResponse(BaseModel):
    locationId: str
    restaurantId: str
    type: str
    name: str
    displayLabel: str
    capacity: int | None = None
    zone: str | None = None
    isActive: bool
    createdAt: datetime
    sessionStatus: str | None = None
    activeSessionId: str | None = None
    lastSessionOpenedAt: datetime | None = None


class LocationsResponse(BaseModel):
    locations: list[LocationResponse] = Field(default_factory=list)


class SessionResponse(BaseModel):
    sessionId: str
    restaurantId: str
    locationId: str
    status: str
    openedAt: datetime
    closedAt: datetime | None = None
    openedByRoleId: str | None = None
    openedBySource: str | None = None
    notes: str | None = None


class SessionsResponse(BaseModel):
    sessions: list[SessionResponse] = Field(default_factory=list)


class RoleResponse(BaseModel):
    roleId: str
    code: str
    displayName: str
    roleGroup: str
    createdAt: datetime


class RolesResponse(BaseModel):
    roles: list[RoleResponse] = Field(default_factory=list)


class InventoryStubResponse(BaseModel):
    status: str
    message: str
    implemented: bool
