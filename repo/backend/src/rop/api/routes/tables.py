from __future__ import annotations

from fastapi import APIRouter, HTTPException

from rop.application.dto.responses import TableResponse
from rop.application.use_cases.open_table import GetTable, OpenTable, TableNotFoundError
from rop.domain.common.ids import RestaurantId, TableId
from rop.infrastructure.db.repositories.table_repo import SqlAlchemyTableRepository

router = APIRouter()


def _open_table_use_case() -> OpenTable:
    return OpenTable(table_repository=SqlAlchemyTableRepository())


def _get_table_use_case() -> GetTable:
    return GetTable(table_repository=SqlAlchemyTableRepository())


@router.post("/v1/restaurants/{restaurant_id}/tables/{table_id}/open", response_model=TableResponse)
def open_table(restaurant_id: str, table_id: str) -> TableResponse:
    payload = _open_table_use_case().execute(
        restaurant_id=RestaurantId(restaurant_id),
        table_id=TableId(table_id),
    )
    return payload


@router.get("/v1/restaurants/{restaurant_id}/tables/{table_id}", response_model=TableResponse)
def get_table(restaurant_id: str, table_id: str) -> TableResponse:
    try:
        return _get_table_use_case().execute(
            restaurant_id=RestaurantId(restaurant_id),
            table_id=TableId(table_id),
        )
    except TableNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
