from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CatalogBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CategoryCreateRequest(CatalogBaseModel):
    restaurant_id: str
    name: str = Field(min_length=1, max_length=255)
    sort_order: int = 0
    is_active: bool = True


class CategoryUpdateRequest(CatalogBaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    sort_order: int | None = None
    is_active: bool | None = None


class CategoryResponse(CatalogBaseModel):
    id: str
    restaurant_id: str
    name: str
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class MenuItemCreateRequest(CatalogBaseModel):
    restaurant_id: str
    category_id: str | None = None
    sku: str | None = Field(default=None, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    price: Decimal = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    is_active: bool = True
    is_available: bool = True


class MenuItemUpdateRequest(CatalogBaseModel):
    category_id: str | None = None
    sku: str | None = Field(default=None, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_active: bool | None = None
    is_available: bool | None = None


class MenuItemResponse(CatalogBaseModel):
    id: str
    restaurant_id: str
    category_id: str | None
    sku: str | None
    name: str
    description: str | None
    price: float
    currency: str
    is_active: bool
    is_available: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class PublicMenuItemResponse(CatalogBaseModel):
    id: str
    category_id: str | None
    sku: str | None
    name: str
    description: str | None
    price: float
    currency: str
    is_available: bool


class PublicCategoryResponse(CatalogBaseModel):
    id: str
    name: str
    sort_order: int
    items: list[PublicMenuItemResponse]


class CatalogResponse(CatalogBaseModel):
    restaurant_id: str
    categories: list[PublicCategoryResponse]
