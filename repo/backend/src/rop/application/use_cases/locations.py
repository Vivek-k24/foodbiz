from __future__ import annotations

from rop.application.dto.responses import LocationsResponse
from rop.application.mappers.foundation_mapper import to_location_response
from rop.application.ports.repositories import LocationRepository
from rop.domain.common.ids import RestaurantId
from rop.domain.location.entities import LocationType
from rop.domain.session.entities import SessionStatus


class InvalidLocationFilterError(Exception):
    pass


class ListLocations:
    def __init__(self, repository: LocationRepository) -> None:
        self._repository = repository

    def execute(
        self,
        restaurant_id: RestaurantId,
        *,
        location_type: str | None,
        is_active: bool | None,
        session_status: str | None,
    ) -> LocationsResponse:
        normalized_type = _parse_location_type(location_type)
        normalized_session_status = _parse_session_status(session_status)
        rows = self._repository.list_for_restaurant(
            restaurant_id=restaurant_id,
            location_type=normalized_type,
            is_active=is_active,
            session_status=normalized_session_status,
        )
        return LocationsResponse(locations=[to_location_response(row) for row in rows])


def _parse_location_type(raw_value: str | None) -> LocationType | None:
    if raw_value is None or raw_value == "ALL":
        return None
    try:
        return LocationType(raw_value)
    except ValueError as exc:
        raise InvalidLocationFilterError(f"invalid location type: {raw_value}") from exc


def _parse_session_status(raw_value: str | None) -> SessionStatus | None:
    if raw_value is None or raw_value == "ALL":
        return None
    try:
        return SessionStatus(raw_value)
    except ValueError as exc:
        raise InvalidLocationFilterError(f"invalid session status: {raw_value}") from exc
