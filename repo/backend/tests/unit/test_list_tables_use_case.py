from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rop.application.ports.repositories import (
    InvalidCursorError,
    TableOrderSummaryData,
    TableRegistryRowData,
)
from rop.application.use_cases.list_tables import (
    InvalidTableRegistryCursorError,
    InvalidTableRegistryStatusError,
    ListTables,
    RestaurantNotFoundError,
)
from rop.domain.common.ids import RestaurantId, TableId
from rop.domain.table.entities import Table, TableStatus


class FakeTableRepository:
    def __init__(
        self,
        rows: list[TableRegistryRowData],
        *,
        exists: bool = True,
    ) -> None:
        self._rows = rows
        self._exists = exists
        self.last_status: TableStatus | None = None

    def get(self, table_id: TableId, restaurant_id: RestaurantId) -> Table | None:
        return None

    def upsert(self, table: Table) -> None:
        return None

    def restaurant_exists(self, restaurant_id: RestaurantId) -> bool:
        return self._exists

    def list_for_restaurant(
        self,
        restaurant_id: RestaurantId,
        status: TableStatus | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[TableRegistryRowData], str | None]:
        self.last_status = status
        if cursor == "bad":
            raise InvalidCursorError("invalid cursor")
        return self._rows[:limit], "next-cursor"


def _row(table_id: str) -> TableRegistryRowData:
    return TableRegistryRowData(
        table=Table(
            table_id=TableId(table_id),
            restaurant_id=RestaurantId("rst_001"),
            status=TableStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
            closed_at=None,
        ),
        summary=TableOrderSummaryData(
            orders_total=0,
            placed=0,
            accepted=0,
            ready=0,
            amount_cents=0,
            currency="USD",
            last_order_at=None,
        ),
    )


def test_list_tables_happy_path_maps_rollup_defaults() -> None:
    repository = FakeTableRepository(rows=[_row("tbl_001")])
    use_case = ListTables(table_repository=repository)
    payload = use_case.execute(
        restaurant_id=RestaurantId("rst_001"),
        status="OPEN",
        limit=50,
        cursor=None,
    )
    assert len(payload.tables) == 1
    assert payload.tables[0].tableId == "tbl_001"
    assert payload.tables[0].totals.amountCents == 0
    assert payload.tables[0].counts.ordersTotal == 0
    assert payload.nextCursor == "next-cursor"
    assert repository.last_status == TableStatus.OPEN


def test_list_tables_rejects_invalid_status() -> None:
    with pytest.raises(InvalidTableRegistryStatusError):
        ListTables(table_repository=FakeTableRepository(rows=[])).execute(
            restaurant_id=RestaurantId("rst_001"),
            status="BROKEN",
            limit=50,
            cursor=None,
        )


def test_list_tables_rejects_invalid_cursor() -> None:
    with pytest.raises(InvalidTableRegistryCursorError):
        ListTables(table_repository=FakeTableRepository(rows=[])).execute(
            restaurant_id=RestaurantId("rst_001"),
            status="ALL",
            limit=50,
            cursor="bad",
        )


def test_list_tables_rejects_unknown_restaurant() -> None:
    with pytest.raises(RestaurantNotFoundError):
        ListTables(table_repository=FakeTableRepository(rows=[], exists=False)).execute(
            restaurant_id=RestaurantId("rst_unknown"),
            status="ALL",
            limit=50,
            cursor=None,
        )


def test_list_tables_limit_bounds() -> None:
    use_case = ListTables(table_repository=FakeTableRepository(rows=[]))
    with pytest.raises(InvalidTableRegistryStatusError):
        use_case.execute(
            restaurant_id=RestaurantId("rst_001"),
            status="ALL",
            limit=0,
            cursor=None,
        )
    with pytest.raises(InvalidTableRegistryStatusError):
        use_case.execute(
            restaurant_id=RestaurantId("rst_001"),
            status="ALL",
            limit=201,
            cursor=None,
        )
