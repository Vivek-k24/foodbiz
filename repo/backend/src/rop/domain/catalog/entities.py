from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class CategorySnapshot:
    id: str
    restaurant_id: str
    name: str
    sort_order: int
    is_active: bool
    deleted_at: datetime | None


@dataclass(slots=True)
class MenuItemSnapshot:
    id: str
    restaurant_id: str
    category_id: str | None
    sku: str | None
    name: str
    description: str | None
    currency: str
    is_active: bool
    is_available: bool
    deleted_at: datetime | None
