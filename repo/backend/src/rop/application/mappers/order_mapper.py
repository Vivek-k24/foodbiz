from __future__ import annotations

from rop.application.dto.responses import (
    MoneyResponse,
    OrderLineModifierResponse,
    OrderLineResponse,
    OrderResponse,
)
from rop.domain.order.entities import Order


def to_order_response(order: Order) -> OrderResponse:
    location_id = order.location_id
    updated_at = order.updated_at
    assert location_id is not None
    assert updated_at is not None
    return OrderResponse(
        orderId=str(order.order_id),
        restaurantId=str(order.restaurant_id),
        locationId=str(location_id),
        tableId=str(order.table_id) if order.table_id is not None else None,
        sessionId=str(order.session_id) if order.session_id is not None else None,
        source=order.source.value,
        status=order.status.value,
        lines=[
            OrderLineResponse(
                lineId=str(line.line_id),
                itemId=str(line.item_id),
                name=line.name,
                quantity=line.quantity,
                unitPrice=MoneyResponse(
                    amountCents=line.unit_price.amount_cents,
                    currency=line.unit_price.currency,
                ),
                lineTotal=MoneyResponse(
                    amountCents=line.line_total.amount_cents,
                    currency=line.line_total.currency,
                ),
                notes=line.notes,
                modifiers=[
                    OrderLineModifierResponse(
                        code=modifier.code,
                        label=modifier.label,
                        value=modifier.value,
                    )
                    for modifier in line.modifiers
                ]
                or None,
            )
            for line in order.lines
        ],
        total=MoneyResponse(
            amountCents=order.total.amount_cents,
            currency=order.total.currency,
        ),
        createdAt=order.created_at,
        updatedAt=updated_at,
    )
