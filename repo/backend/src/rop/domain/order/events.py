from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from rop.domain.common.ids import OrderId, RestaurantId, TableId
from rop.domain.common.money import Money


@dataclass(frozen=True)
class OrderPlaced:
    order_id: OrderId
    restaurant_id: RestaurantId
    table_id: TableId
    total: Money
    created_at: datetime
