from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from rop.domain.common.ids import MenuId, MenuItemId, RestaurantId
from rop.domain.common.money import Money


@dataclass(frozen=True)
class MenuItem:
    item_id: MenuItemId
    name: str
    description: str | None
    price_money: Money
    is_available: bool
    category_id: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name must be non-empty")


@dataclass(frozen=True)
class Menu:
    menu_id: MenuId
    restaurant_id: RestaurantId
    version: int
    categories: list[str] = field(default_factory=list)
    items: list[MenuItem] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("version must be >= 1")
