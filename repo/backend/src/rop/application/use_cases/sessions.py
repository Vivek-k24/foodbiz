from __future__ import annotations

from datetime import datetime, timezone

from rop.application.dto.responses import SessionResponse, SessionsResponse
from rop.application.mappers.foundation_mapper import to_session_response
from rop.application.ports.repositories import (
    LocationRepository,
    SessionRepository,
    TableRepository,
)
from rop.domain.common.ids import LocationId, RestaurantId, RoleId, SessionId
from rop.domain.common.location_keys import table_id_from_location
from rop.domain.session.entities import SessionStatus
from rop.domain.table.entities import Table, TableStatus


class SessionNotFoundError(Exception):
    pass


class LocationNotFoundError(Exception):
    pass


class InvalidSessionFilterError(Exception):
    pass


class OpenSession:
    def __init__(
        self,
        session_repository: SessionRepository,
        location_repository: LocationRepository,
        table_repository: TableRepository,
    ) -> None:
        self._session_repository = session_repository
        self._location_repository = location_repository
        self._table_repository = table_repository

    def execute(
        self,
        *,
        restaurant_id: RestaurantId,
        location_id: LocationId,
        opened_by_role_id: RoleId | None,
        opened_by_source: str | None,
        notes: str | None,
    ) -> SessionResponse:
        location = self._location_repository.get_location(restaurant_id, location_id)
        if location is None:
            raise LocationNotFoundError(f"location {location_id} not found")
        session = self._session_repository.open_session(
            restaurant_id=restaurant_id,
            location_id=location_id,
            opened_by_role_id=opened_by_role_id,
            opened_by_source=opened_by_source,
            notes=notes,
        )
        table_id = table_id_from_location(location_id)
        if table_id is not None:
            self._table_repository.upsert(
                Table(
                    table_id=table_id,
                    restaurant_id=restaurant_id,
                    status=TableStatus.OPEN,
                    opened_at=session.opened_at,
                    closed_at=None,
                )
            )
        return to_session_response(session)


class CloseSession:
    def __init__(
        self,
        session_repository: SessionRepository,
        table_repository: TableRepository,
    ) -> None:
        self._session_repository = session_repository
        self._table_repository = table_repository

    def execute(self, session_id: SessionId) -> SessionResponse:
        session = self._session_repository.close_session(session_id)
        if session is None:
            raise SessionNotFoundError(f"session {session_id} not found")
        table_id = table_id_from_location(session.location_id)
        if table_id is not None:
            self._table_repository.upsert(
                Table(
                    table_id=table_id,
                    restaurant_id=session.restaurant_id,
                    status=TableStatus.CLOSED,
                    opened_at=session.opened_at,
                    closed_at=session.closed_at or datetime.now(timezone.utc),
                )
            )
        return to_session_response(session)


class ListSessions:
    def __init__(self, session_repository: SessionRepository) -> None:
        self._session_repository = session_repository

    def execute(
        self,
        *,
        restaurant_id: RestaurantId,
        location_id: LocationId | None,
        status: str | None,
    ) -> SessionsResponse:
        normalized_status = _parse_status(status)
        sessions = self._session_repository.list_sessions(
            restaurant_id=restaurant_id,
            location_id=location_id,
            status=normalized_status,
        )
        return SessionsResponse(sessions=[to_session_response(session) for session in sessions])


def _parse_status(raw_value: str | None) -> SessionStatus | None:
    if raw_value is None or raw_value == "ALL":
        return None
    try:
        return SessionStatus(raw_value)
    except ValueError as exc:
        raise InvalidSessionFilterError(f"invalid session status: {raw_value}") from exc
