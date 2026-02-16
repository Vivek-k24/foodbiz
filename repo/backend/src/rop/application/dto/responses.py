from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MoneyResponse(BaseModel):
    amountCents: int
    currency: str


class MenuItemResponse(BaseModel):
    itemId: str
    name: str
    description: str | None = None
    priceMoney: MoneyResponse
    isAvailable: bool
    categoryId: str | None = None


class MenuResponse(BaseModel):
    menuId: str
    restaurantId: str
    menuVersion: int
    categories: list[str] = Field(default_factory=list)
    items: list[MenuItemResponse] = Field(default_factory=list)
    updatedAt: datetime


class OrderLineResponse(BaseModel):
    lineId: str
    itemId: str
    name: str
    quantity: int
    unitPrice: MoneyResponse
    lineTotal: MoneyResponse
    notes: str | None = None


class OrderResponse(BaseModel):
    orderId: str
    restaurantId: str
    tableId: str
    status: str
    lines: list[OrderLineResponse] = Field(default_factory=list)
    total: MoneyResponse
    createdAt: datetime


class TableResponse(BaseModel):
    tableId: str
    restaurantId: str
    status: str
    openedAt: datetime | None = None
    closedAt: datetime | None = None
