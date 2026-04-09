from __future__ import annotations

import pytest

from rop.domain.commerce.enums import OrderStatus
from rop.domain.errors import ConflictError
from rop.domain.kitchen.workflow import apply_action


def test_ready_requires_accepted_state() -> None:
    with pytest.raises(ConflictError) as exc:
        apply_action(OrderStatus.PENDING, "ready")
    assert exc.value.code == "INVALID_ORDER_TRANSITION"


def test_workflow_happy_path() -> None:
    accepted = apply_action(OrderStatus.PENDING, "accept")
    ready = apply_action(accepted, "ready")
    served = apply_action(ready, "served")
    settled = apply_action(served, "settled")
    assert settled is OrderStatus.SETTLED
