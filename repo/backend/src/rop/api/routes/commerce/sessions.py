from __future__ import annotations

from fastapi import APIRouter, Depends, status

from rop.api.dependencies import get_commerce_service
from rop.application.commerce.schemas import (
    SessionCreateRequest,
    SessionResponse,
    SessionUpdateRequest,
)
from rop.application.commerce.service import CommerceService

router = APIRouter()


@router.post("/v1/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    request: SessionCreateRequest,
    service: CommerceService = Depends(get_commerce_service),
) -> SessionResponse:
    return service.create_session(request)


@router.get("/v1/sessions/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    service: CommerceService = Depends(get_commerce_service),
) -> SessionResponse:
    return service.get_session(session_id)


@router.patch("/v1/sessions/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: str,
    request: SessionUpdateRequest,
    service: CommerceService = Depends(get_commerce_service),
) -> SessionResponse:
    return service.update_session(session_id, request)


@router.delete("/v1/sessions/{session_id}", response_model=SessionResponse)
def delete_session(
    session_id: str,
    service: CommerceService = Depends(get_commerce_service),
) -> SessionResponse:
    return service.delete_session(session_id)
