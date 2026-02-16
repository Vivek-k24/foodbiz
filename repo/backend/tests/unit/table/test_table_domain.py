from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from rop.domain.common.ids import RestaurantId, TableId
from rop.domain.table.entities import Table, TableClosedError, TableStatus


def test_open_table_requires_opened_at() -> None:
    with pytest.raises(ValueError):
        Table(
            table_id=TableId("tbl_001"),
            restaurant_id=RestaurantId("rst_001"),
            status=TableStatus.OPEN,
            opened_at=None,
            closed_at=None,
        )


def test_closed_table_requires_closed_at() -> None:
    with pytest.raises(ValueError):
        Table(
            table_id=TableId("tbl_001"),
            restaurant_id=RestaurantId("rst_001"),
            status=TableStatus.CLOSED,
            opened_at=datetime.now(timezone.utc),
            closed_at=None,
        )


def test_ensure_open_raises_for_closed_table() -> None:
    table = Table(
        table_id=TableId("tbl_001"),
        restaurant_id=RestaurantId("rst_001"),
        status=TableStatus.CLOSED,
        opened_at=datetime.now(timezone.utc),
        closed_at=datetime.now(timezone.utc),
    )
    with pytest.raises(TableClosedError):
        table.ensure_open()


def test_open_returns_open_table() -> None:
    now = datetime.now(timezone.utc)
    table = Table(
        table_id=TableId("tbl_001"),
        restaurant_id=RestaurantId("rst_001"),
        status=TableStatus.CLOSED,
        opened_at=now,
        closed_at=now,
    )
    reopened = table.open(now)

    assert reopened.status == TableStatus.OPEN
    assert reopened.opened_at == now
    assert reopened.closed_at is None
