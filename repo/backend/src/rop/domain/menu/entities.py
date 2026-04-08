from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from rop.domain.common.ids import CategoryId, MenuId, MenuItemId, RestaurantId
from rop.domain.common.money import Money

ModifierKind = Literal["toggle", "choice", "text"]
CategoryKind = Literal["FOOD", "DRINK"]


@dataclass(frozen=True)
class MenuCategory:
    category_id: CategoryId
    name: str
    category_kind: CategoryKind
    cuisine_or_family: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("category name must be non-empty")
        if not self.cuisine_or_family.strip():
            raise ValueError("cuisine_or_family must be non-empty")


@dataclass(frozen=True)
class AllowedModifier:
    code: str
    label: str
    kind: ModifierKind
    options: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("modifier code must be non-empty")
        if not self.label.strip():
            raise ValueError("modifier label must be non-empty")
        if self.kind == "choice" and not self.options:
            raise ValueError("choice modifiers must define options")


@dataclass(frozen=True)
class MenuItem:
    item_id: MenuItemId
    name: str
    description: str | None
    price_money: Money
    is_available: bool
    category_id: str | None = None
    allowed_modifiers: list[AllowedModifier] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name must be non-empty")


@dataclass(frozen=True)
class Menu:
    menu_id: MenuId
    restaurant_id: RestaurantId
    version: int
    categories: list[MenuCategory] = field(default_factory=list)
    items: list[MenuItem] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("version must be >= 1")
