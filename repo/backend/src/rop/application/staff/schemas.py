from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from rop.application.commerce.schemas import OrderLineRequest


class StaffBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WalkInSessionRequest(StaffBaseModel):
    restaurant_id: str
    location_id: str
    table_id: str
    metadata: dict[str, Any] | None = None
    expires_at: datetime | None = None


class ManualOrderRequest(StaffBaseModel):
    restaurant_id: str
    session_id: str
    notes: str | None = None
    lines: list[OrderLineRequest] = Field(min_length=1)


class CounterOrderRequest(StaffBaseModel):
    restaurant_id: str
    location_id: str
    notes: str | None = None
    customer_reference: str | None = None
    metadata: dict[str, Any] | None = None
    lines: list[OrderLineRequest] = Field(min_length=1)
