from __future__ import annotations

from fastapi import APIRouter, Query

from rop.application.dto.responses import LocationOrdersResponse
from rop.application.use_cases.location_orders import LocationOrders
from rop.domain.common.ids import LocationId, RestaurantId
from rop.infrastructure.db.repositories.location_repo import SqlAlchemyLocationRepository
from rop.infrastructure.db.repositories.order_repo import SqlAlchemyOrderRepository

router = APIRouter()


def _location_orders_use_case() -> LocationOrders:
    return LocationOrders(
        order_repository=SqlAlchemyOrderRepository(),
        location_repository=SqlAlchemyLocationRepository(),
    )


@router.get(
    "/v1/restaurants/{restaurant_id}/locations/{location_id}/orders",
    response_model=LocationOrdersResponse,
)
def list_location_orders(
    restaurant_id: str,
    location_id: str,
    status: str = Query(default="ALL"),
    limit: int = Query(default=50),
    cursor: str | None = Query(default=None),
) -> LocationOrdersResponse:
    return _location_orders_use_case().execute(
        restaurant_id=RestaurantId(restaurant_id),
        location_id=LocationId(location_id),
        status=status,
        limit=limit,
        cursor=cursor,
    )
