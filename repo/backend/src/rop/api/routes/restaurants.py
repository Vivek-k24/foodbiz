from __future__ import annotations

from fastapi import APIRouter

from rop.application.dto.responses import RestaurantsResponse
from rop.application.use_cases.restaurants import ListRestaurants
from rop.infrastructure.db.repositories.restaurant_repo import SqlAlchemyRestaurantRepository

router = APIRouter()


def _list_restaurants_use_case() -> ListRestaurants:
    return ListRestaurants(repository=SqlAlchemyRestaurantRepository())


@router.get("/v1/restaurants", response_model=RestaurantsResponse)
def list_restaurants() -> RestaurantsResponse:
    return _list_restaurants_use_case().execute()
