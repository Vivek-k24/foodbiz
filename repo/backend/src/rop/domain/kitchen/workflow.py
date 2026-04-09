from __future__ import annotations

from rop.domain.commerce.enums import OrderStatus
from rop.domain.errors import ConflictError

_WORKFLOW_ACTIONS: dict[str, tuple[OrderStatus, OrderStatus]] = {
    "accept": (OrderStatus.PENDING, OrderStatus.ACCEPTED),
    "ready": (OrderStatus.ACCEPTED, OrderStatus.READY),
    "served": (OrderStatus.READY, OrderStatus.SERVED),
    "settled": (OrderStatus.SERVED, OrderStatus.SETTLED),
}


def apply_action(status: OrderStatus, action: str) -> OrderStatus:
    if action not in _WORKFLOW_ACTIONS:
        raise ConflictError(
            f"unsupported workflow action '{action}'",
            code="INVALID_ORDER_TRANSITION",
        )

    expected_current, next_status = _WORKFLOW_ACTIONS[action]
    if status is not expected_current:
        raise ConflictError(
            f"cannot {action} order while status is '{status.value}'",
            code="INVALID_ORDER_TRANSITION",
            details={
                "current_status": status.value,
                "required_status": expected_current.value,
                "action": action,
            },
        )
    return next_status
