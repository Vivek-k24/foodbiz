from __future__ import annotations

from datetime import datetime, timezone

from rop.application.dto.responses import TableResponse
from rop.application.mappers.table_mapper import to_table_response
from rop.application.ports.repositories import TableRepository
from rop.domain.common.ids import RestaurantId, TableId
from rop.domain.table.entities import Table, TableStatus


class TableNotFoundError(Exception):
    pass


class OpenTable:
    def __init__(self, table_repository: TableRepository) -> None:
        self._table_repository = table_repository

    def execute(self, restaurant_id: RestaurantId, table_id: TableId) -> TableResponse:
        table = self._table_repository.get(table_id=table_id, restaurant_id=restaurant_id)
        now = datetime.now(timezone.utc)

        if table is None:
            updated = Table(
                table_id=table_id,
                restaurant_id=restaurant_id,
                status=TableStatus.OPEN,
                opened_at=now,
                closed_at=None,
            )
        else:
            updated = table.open(now)

        self._table_repository.upsert(updated)
        return to_table_response(updated)


class GetTable:
    def __init__(self, table_repository: TableRepository) -> None:
        self._table_repository = table_repository

    def execute(self, restaurant_id: RestaurantId, table_id: TableId) -> TableResponse:
        table = self._table_repository.get(table_id=table_id, restaurant_id=restaurant_id)
        if table is None:
            raise TableNotFoundError(
                f"table not found for restaurant_id={restaurant_id}, table_id={table_id}"
            )
        return to_table_response(table)
