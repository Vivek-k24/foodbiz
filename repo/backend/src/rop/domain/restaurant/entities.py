from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from rop.domain.common.ids import RestaurantId


@dataclass(frozen=True)
class Restaurant:
    restaurant_id: RestaurantId
    name: str
    timezone: str
    currency: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("restaurant name must be non-empty")
        if not self.timezone.strip():
            raise ValueError("restaurant timezone must be non-empty")
        if len(self.currency.strip()) != 3:
            raise ValueError("restaurant currency must be a 3-letter code")
