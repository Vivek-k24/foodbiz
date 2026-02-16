from __future__ import annotations

import json
from uuid import uuid4

from rop.domain.order.entities import Order
from rop.domain.order.events import OrderPlaced


def to_order_placed_envelope_json(
    event: OrderPlaced,
    order: Order,
    trace_id: str | None,
    request_id: str | None,
) -> str:
    envelope = {
        "event_id": str(uuid4()),
        "event_type": "order.placed",
        "occurred_at": event.created_at.isoformat(),
        "trace_id": trace_id,
        "request_id": request_id,
        "restaurant_id": str(event.restaurant_id),
        "payload": {
            "orderId": str(event.order_id),
            "tableId": str(event.table_id),
            "totalMoney": {
                "amountCents": event.total.amount_cents,
                "currency": event.total.currency,
            },
            "createdAt": event.created_at.isoformat(),
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
    }
    return json.dumps(envelope, separators=(",", ":"), ensure_ascii=False)
