from __future__ import annotations

from typing import Protocol

from rop.domain.common.ids import RestaurantId
from rop.domain.menu.entities import Menu


class MenuRepository(Protocol):
    def get_menu_by_restaurant_id(self, restaurant_id: RestaurantId) -> Menu | None: ...
