from __future__ import annotations

from fastapi import APIRouter, Query

from rop.application.dto.responses import LocationsResponse
from rop.application.use_cases.locations import ListLocations
from rop.domain.common.ids import RestaurantId
from rop.infrastructure.db.repositories.location_repo import SqlAlchemyLocationRepository

router = APIRouter()


def _list_locations_use_case() -> ListLocations:
    return ListLocations(repository=SqlAlchemyLocationRepository())


@router.get("/v1/restaurants/{restaurant_id}/locations", response_model=LocationsResponse)
def list_locations(
    restaurant_id: str,
    type: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    session_status: str | None = Query(default=None),
) -> LocationsResponse:
    return _list_locations_use_case().execute(
        restaurant_id=RestaurantId(restaurant_id),
        location_type=type,
        is_active=is_active,
        session_status=session_status,
    )
