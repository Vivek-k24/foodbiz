from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from rop.domain.common.ids import RestaurantId, TableId


class TableStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class Table:
    table_id: TableId
    restaurant_id: RestaurantId
    status: TableStatus
    opened_at: datetime | None
    closed_at: datetime | None

    def __post_init__(self) -> None:
        if self.status == TableStatus.OPEN and self.opened_at is None:
            raise ValueError("opened_at must be set when table status is OPEN")
        if self.status == TableStatus.CLOSED and self.closed_at is None:
            raise ValueError("closed_at must be set when table status is CLOSED")

    def open(self, now: datetime) -> Table:
        if self.status == TableStatus.OPEN:
            return self
        return Table(
            table_id=self.table_id,
            restaurant_id=self.restaurant_id,
            status=TableStatus.OPEN,
            opened_at=now,
            closed_at=None,
        )

    def close(self, now: datetime) -> Table:
        if self.status == TableStatus.CLOSED:
            raise TableAlreadyClosedError(f"table {self.table_id} is already closed")
        return Table(
            table_id=self.table_id,
            restaurant_id=self.restaurant_id,
            status=TableStatus.CLOSED,
            opened_at=self.opened_at,
            closed_at=now,
        )

    def ensure_open(self) -> None:
        if self.status != TableStatus.OPEN:
            raise TableClosedError(f"table {self.table_id} is not open")


class TableClosedError(Exception):
    pass


class TableAlreadyClosedError(Exception):
    pass
