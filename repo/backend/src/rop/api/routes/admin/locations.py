from __future__ import annotations

from fastapi import APIRouter, Depends, status

from rop.api.dependencies import get_commerce_service
from rop.application.commerce.schemas import (
    LocationCreateRequest,
    LocationResponse,
    LocationUpdateRequest,
)
from rop.application.commerce.service import CommerceService

router = APIRouter()


@router.post(
    "/v1/admin/locations", response_model=LocationResponse, status_code=status.HTTP_201_CREATED
)
def create_location(
    request: LocationCreateRequest,
    service: CommerceService = Depends(get_commerce_service),
) -> LocationResponse:
    return service.create_location(request)


@router.get("/v1/admin/locations/{location_id}", response_model=LocationResponse)
def get_location(
    location_id: str,
    service: CommerceService = Depends(get_commerce_service),
) -> LocationResponse:
    return service.get_location(location_id)


@router.patch("/v1/admin/locations/{location_id}", response_model=LocationResponse)
def update_location(
    location_id: str,
    request: LocationUpdateRequest,
    service: CommerceService = Depends(get_commerce_service),
) -> LocationResponse:
    return service.update_location(location_id, request)


@router.delete("/v1/admin/locations/{location_id}", response_model=LocationResponse)
def delete_location(
    location_id: str,
    service: CommerceService = Depends(get_commerce_service),
) -> LocationResponse:
    return service.delete_location(location_id)
