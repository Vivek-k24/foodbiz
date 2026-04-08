from __future__ import annotations

from rop.application.dto.responses import RestaurantsResponse
from rop.application.mappers.foundation_mapper import to_restaurant_response
from rop.application.ports.repositories import RestaurantRepository


class ListRestaurants:
    def __init__(self, repository: RestaurantRepository) -> None:
        self._repository = repository

    def execute(self) -> RestaurantsResponse:
        return RestaurantsResponse(
            restaurants=[
                to_restaurant_response(restaurant)
                for restaurant in self._repository.list_restaurants()
            ]
        )
