from __future__ import annotations

from fastapi import APIRouter, Query

from rop.application.dto.responses import TableRegistryResponse
from rop.application.use_cases.list_tables import ListTables
from rop.domain.common.ids import RestaurantId
from rop.infrastructure.db.repositories.table_repo import SqlAlchemyTableRepository

router = APIRouter()


def _list_tables_use_case() -> ListTables:
    return ListTables(table_repository=SqlAlchemyTableRepository())


@router.get("/v1/restaurants/{restaurant_id}/tables", response_model=TableRegistryResponse)
def list_tables(
    restaurant_id: str,
    status: str = Query(default="ALL"),
    limit: int = Query(default=50),
    cursor: str | None = Query(default=None),
) -> TableRegistryResponse:
    return _list_tables_use_case().execute(
        restaurant_id=RestaurantId(restaurant_id),
        status=status,
        limit=limit,
        cursor=cursor,
    )
