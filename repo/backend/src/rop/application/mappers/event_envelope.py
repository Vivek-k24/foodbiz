from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from rop.domain.order.entities import Order


def _serialize_event(
    *,
    event_type: str,
    occurred_at: datetime,
    restaurant_id: str,
    payload: dict[str, Any],
    trace_id: str | None,
    request_id: str | None,
) -> str:
    envelope = {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "occurred_at": occurred_at.isoformat(),
        "request_id": request_id,
        "trace_id": trace_id,
        "restaurant_id": restaurant_id,
        "payload": payload,
    }
    return json.dumps(envelope, separators=(",", ":"), ensure_ascii=False)


def serialize_order_event(
    *,
    event_type: str,
    occurred_at: datetime,
    order: Order,
    trace_id: str | None,
    request_id: str | None,
) -> str:
    return _serialize_event(
        event_type=event_type,
        occurred_at=occurred_at,
        restaurant_id=str(order.restaurant_id),
        trace_id=trace_id,
        request_id=request_id,
        payload={
            "orderId": str(order.order_id),
            "tableId": str(order.table_id),
            "status": order.status.value,
            "totalMoney": {
                "amountCents": order.total.amount_cents,
                "currency": order.total.currency,
            },
            "createdAt": order.created_at.isoformat(),
            "lines": [
                {
                    "lineId": str(line.line_id),
                    "itemId": str(line.item_id),
                    "name": line.name,
                    "quantity": line.quantity,
                    "unitPrice": {
                        "amountCents": line.unit_price.amount_cents,
                        "currency": line.unit_price.currency,
                    },
                    "lineTotal": {
                        "amountCents": line.line_total.amount_cents,
                        "currency": line.line_total.currency,
                    },
                    "notes": line.notes,
                }
                for line in order.lines
            ],
        },
    )


def serialize_table_closed_event(
    *,
    occurred_at: datetime,
    restaurant_id: str,
    table_id: str,
    status: str,
    closed_at: datetime,
    trace_id: str | None,
    request_id: str | None,
) -> str:
    return _serialize_event(
        event_type="table.closed",
        occurred_at=occurred_at,
        restaurant_id=restaurant_id,
        trace_id=trace_id,
        request_id=request_id,
        payload={
            "tableId": table_id,
            "restaurantId": restaurant_id,
            "status": status,
            "closedAt": closed_at.isoformat(),
        },
    )
