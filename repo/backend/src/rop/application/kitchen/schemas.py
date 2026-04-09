from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from rop.domain.commerce.enums import Channel, OrderStatus, SourceType


class KitchenBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KitchenQueueEntryResponse(KitchenBaseModel):
    id: str
    restaurant_id: str
    location_id: str | None
    session_id: str
    table_id: str | None
    table_label: str | None
    channel: Channel
    source_type: SourceType
    status: OrderStatus
    notes: str | None
    age_seconds: int
    created_at: datetime
    updated_at: datetime


class KitchenQueueResponse(KitchenBaseModel):
    orders: list[KitchenQueueEntryResponse]
