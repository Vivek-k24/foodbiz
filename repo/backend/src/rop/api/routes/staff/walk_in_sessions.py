from __future__ import annotations

from fastapi import APIRouter, Depends, status

from rop.api.dependencies import get_staff_service
from rop.application.commerce.schemas import SessionResponse
from rop.application.staff.schemas import WalkInSessionRequest
from rop.application.staff.service import StaffService

router = APIRouter()


@router.post(
    "/v1/staff/walk-in-sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_walk_in_session(
    request: WalkInSessionRequest,
    service: StaffService = Depends(get_staff_service),
) -> SessionResponse:
    return service.create_walk_in_session(request)
