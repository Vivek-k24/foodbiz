from __future__ import annotations

from fastapi import APIRouter, Query

from rop.application.dto.responses import TableOrdersResponse
from rop.application.use_cases.table_orders import TableOrders
from rop.domain.common.ids import RestaurantId, TableId
from rop.infrastructure.db.repositories.order_repo import SqlAlchemyOrderRepository
from rop.infrastructure.db.repositories.table_repo import SqlAlchemyTableRepository

router = APIRouter()


def _table_orders_use_case() -> TableOrders:
    return TableOrders(
        order_repository=SqlAlchemyOrderRepository(),
        table_repository=SqlAlchemyTableRepository(),
    )


@router.get(
    "/v1/restaurants/{restaurant_id}/tables/{table_id}/orders",
    response_model=TableOrdersResponse,
)
def list_table_orders(
    restaurant_id: str,
    table_id: str,
    status: str = Query(default="ALL"),
    limit: int = Query(default=50),
    cursor: str | None = Query(default=None),
) -> TableOrdersResponse:
    return _table_orders_use_case().execute(
        restaurant_id=RestaurantId(restaurant_id),
        table_id=TableId(table_id),
        status=status,
        limit=limit,
        cursor=cursor,
    )
