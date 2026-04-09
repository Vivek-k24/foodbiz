from __future__ import annotations

from fastapi import APIRouter, Depends, status

from rop.api.dependencies import get_commerce_service
from rop.application.commerce.schemas import (
    SessionResponse,
    TableCreateRequest,
    TableResponse,
    TableSessionOpenRequest,
    TableUpdateRequest,
)
from rop.application.commerce.service import CommerceService

router = APIRouter()


@router.post("/v1/tables", response_model=TableResponse, status_code=status.HTTP_201_CREATED)
def create_table(
    request: TableCreateRequest,
    service: CommerceService = Depends(get_commerce_service),
) -> TableResponse:
    return service.create_table(request)


@router.get("/v1/tables/{table_id}", response_model=TableResponse)
def get_table(
    table_id: str,
    service: CommerceService = Depends(get_commerce_service),
) -> TableResponse:
    return service.get_table(table_id)


@router.patch("/v1/tables/{table_id}", response_model=TableResponse)
def update_table(
    table_id: str,
    request: TableUpdateRequest,
    service: CommerceService = Depends(get_commerce_service),
) -> TableResponse:
    return service.update_table(table_id, request)


@router.delete("/v1/tables/{table_id}", response_model=TableResponse)
def delete_table(
    table_id: str,
    service: CommerceService = Depends(get_commerce_service),
) -> TableResponse:
    return service.delete_table(table_id)


@router.post(
    "/v1/tables/{table_id}/open-session",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def open_table_session(
    table_id: str,
    request: TableSessionOpenRequest,
    service: CommerceService = Depends(get_commerce_service),
) -> SessionResponse:
    return service.open_table_session(table_id, request)


@router.post("/v1/tables/{table_id}/close-session", response_model=SessionResponse)
def close_table_session(
    table_id: str,
    service: CommerceService = Depends(get_commerce_service),
) -> SessionResponse:
    return service.close_table_session(table_id)
