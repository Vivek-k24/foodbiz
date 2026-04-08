from __future__ import annotations

from fastapi import APIRouter, Query

from rop.application.dto.responses import OrderEventResponse
from rop.application.use_cases.order_events import ListOrderEvents
from rop.domain.common.ids import OrderId, RestaurantId
from rop.infrastructure.db.repositories.order_repo import SqlAlchemyOrderRepository

router = APIRouter()


def _list_order_events_use_case() -> ListOrderEvents:
    return ListOrderEvents(repository=SqlAlchemyOrderRepository())


@router.get("/v1/order-events", response_model=list[OrderEventResponse])
def list_order_events(
    restaurant_id: str = Query(..., alias="restaurantId"),
    order_id: str | None = Query(default=None, alias="orderId"),
) -> list[OrderEventResponse]:
    return _list_order_events_use_case().execute(
        restaurant_id=RestaurantId(restaurant_id),
        order_id=OrderId(order_id) if order_id else None,
    )
