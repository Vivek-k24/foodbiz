from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from rop.domain.common.ids import InventoryItemId, RestaurantId


@dataclass(frozen=True)
class InventoryItemStub:
    inventory_item_id: InventoryItemId
    restaurant_id: RestaurantId
    name: str
    created_at: datetime
