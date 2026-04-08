from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


def _to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class CamelBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
    )


class PlaceOrderLineModifierRequest(CamelBaseModel):
    code: str
    label: str
    value: str


class PlaceOrderLineRequest(CamelBaseModel):
    item_id: str
    quantity: int
    notes: str | None = None
    modifiers: list[PlaceOrderLineModifierRequest] | None = None


class PlaceOrderRequest(CamelBaseModel):
    lines: list[PlaceOrderLineRequest] = Field(min_length=1)
    note: str | None = None
    source: str | None = None


class CreateOrderRequest(PlaceOrderRequest):
    restaurant_id: str
    location_id: str
    session_id: str | None = None
    table_id: str | None = None


class OpenSessionRequest(CamelBaseModel):
    opened_by_role_id: str | None = None
    opened_by_source: str | None = None
    notes: str | None = None
