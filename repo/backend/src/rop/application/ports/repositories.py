from __future__ import annotations

from typing import Protocol

from rop.domain.common.ids import OrderId, RestaurantId, TableId
from rop.domain.menu.entities import Menu
from rop.domain.order.entities import Order
from rop.domain.table.entities import Table


class MenuRepository(Protocol):
    def get_menu_by_restaurant_id(self, restaurant_id: RestaurantId) -> Menu | None: ...


class TableRepository(Protocol):
    def get(self, table_id: TableId, restaurant_id: RestaurantId) -> Table | None: ...

    def upsert(self, table: Table) -> None: ...


class OrderRepository(Protocol):
    def add(self, order: Order) -> None: ...

    def get(self, order_id: OrderId) -> Order | None: ...

    def update(self, order: Order) -> None: ...
