from __future__ import annotations

from rop.application.dto.responses import TableResponse
from rop.domain.table.entities import Table


def to_table_response(table: Table) -> TableResponse:
    return TableResponse(
        tableId=str(table.table_id),
        restaurantId=str(table.restaurant_id),
        status=table.status.value,
        openedAt=table.opened_at,
        closedAt=table.closed_at,
    )
