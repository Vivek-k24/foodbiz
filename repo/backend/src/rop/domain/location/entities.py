from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from rop.domain.common.ids import LocationId, RestaurantId


class LocationType(str, Enum):
    TABLE = "TABLE"
    BAR_SEAT = "BAR_SEAT"
    ONLINE_PICKUP = "ONLINE_PICKUP"
    ONLINE_DELIVERY = "ONLINE_DELIVERY"


@dataclass(frozen=True)
class Location:
    location_id: LocationId
    restaurant_id: RestaurantId
    location_type: LocationType
    name: str
    display_label: str
    capacity: int | None
    zone: str | None
    is_active: bool
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("location name must be non-empty")
        if not self.display_label.strip():
            raise ValueError("location display_label must be non-empty")
        if self.capacity is not None and self.capacity < 0:
            raise ValueError("location capacity must be >= 0")
