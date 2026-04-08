from __future__ import annotations

from fastapi import APIRouter, Query

from rop.application.dto.requests import OpenSessionRequest
from rop.application.dto.responses import SessionResponse, SessionsResponse
from rop.application.use_cases.sessions import CloseSession, ListSessions, OpenSession
from rop.domain.common.ids import LocationId, RestaurantId, RoleId, SessionId
from rop.infrastructure.db.repositories.location_repo import SqlAlchemyLocationRepository
from rop.infrastructure.db.repositories.session_repo import SqlAlchemySessionRepository
from rop.infrastructure.db.repositories.table_repo import SqlAlchemyTableRepository

router = APIRouter()


def _open_session_use_case() -> OpenSession:
    return OpenSession(
        session_repository=SqlAlchemySessionRepository(),
        location_repository=SqlAlchemyLocationRepository(),
        table_repository=SqlAlchemyTableRepository(),
    )


def _close_session_use_case() -> CloseSession:
    return CloseSession(
        session_repository=SqlAlchemySessionRepository(),
        table_repository=SqlAlchemyTableRepository(),
    )


def _list_sessions_use_case() -> ListSessions:
    return ListSessions(session_repository=SqlAlchemySessionRepository())


@router.post(
    "/v1/restaurants/{restaurant_id}/locations/{location_id}/sessions/open",
    response_model=SessionResponse,
)
def open_session(
    restaurant_id: str,
    location_id: str,
    request_dto: OpenSessionRequest,
) -> SessionResponse:
    return _open_session_use_case().execute(
        restaurant_id=RestaurantId(restaurant_id),
        location_id=LocationId(location_id),
        opened_by_role_id=RoleId(request_dto.opened_by_role_id)
        if request_dto.opened_by_role_id
        else None,
        opened_by_source=request_dto.opened_by_source,
        notes=request_dto.notes,
    )


@router.post("/v1/sessions/{session_id}/close", response_model=SessionResponse)
def close_session(session_id: str) -> SessionResponse:
    return _close_session_use_case().execute(SessionId(session_id))


@router.get("/v1/restaurants/{restaurant_id}/sessions", response_model=SessionsResponse)
def list_sessions(
    restaurant_id: str,
    location_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> SessionsResponse:
    return _list_sessions_use_case().execute(
        restaurant_id=RestaurantId(restaurant_id),
        location_id=LocationId(location_id) if location_id else None,
        status=status,
    )
