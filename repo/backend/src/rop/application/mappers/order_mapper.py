from __future__ import annotations

from rop.application.dto.responses import (
    MoneyResponse,
    OrderLineResponse,
    OrderResponse,
)
from rop.domain.order.entities import Order


def to_order_response(order: Order) -> OrderResponse:
    return OrderResponse(
        orderId=str(order.order_id),
        restaurantId=str(order.restaurant_id),
        tableId=str(order.table_id),
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
            )
            for line in order.lines
        ],
        total=MoneyResponse(
            amountCents=order.total.amount_cents,
            currency=order.total.currency,
        ),
        createdAt=order.created_at,
    )
