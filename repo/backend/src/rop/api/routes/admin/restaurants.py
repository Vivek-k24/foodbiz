from __future__ import annotations

from fastapi import APIRouter, Depends, status

from rop.api.dependencies import get_commerce_service
from rop.application.commerce.schemas import (
    RestaurantCreateRequest,
    RestaurantResponse,
    RestaurantUpdateRequest,
)
from rop.application.commerce.service import CommerceService

router = APIRouter()


@router.post(
    "/v1/admin/restaurants",
    response_model=RestaurantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_restaurant(
    request: RestaurantCreateRequest,
    service: CommerceService = Depends(get_commerce_service),
) -> RestaurantResponse:
    return service.create_restaurant(request)


@router.patch("/v1/admin/restaurants/{restaurant_id}", response_model=RestaurantResponse)
def update_restaurant(
    restaurant_id: str,
    request: RestaurantUpdateRequest,
    service: CommerceService = Depends(get_commerce_service),
) -> RestaurantResponse:
    return service.update_restaurant(restaurant_id, request)


@router.delete("/v1/admin/restaurants/{restaurant_id}", response_model=RestaurantResponse)
def delete_restaurant(
    restaurant_id: str,
    service: CommerceService = Depends(get_commerce_service),
) -> RestaurantResponse:
    return service.delete_restaurant(restaurant_id)
