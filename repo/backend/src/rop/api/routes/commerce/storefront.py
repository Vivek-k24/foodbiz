from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from rop.api.dependencies import get_commerce_service
from rop.application.commerce.schemas import (
    LocationListResponse,
    LocationResponse,
    RestaurantListResponse,
    RestaurantResponse,
)
from rop.application.commerce.service import CommerceService
from rop.domain.commerce.enums import Channel

router = APIRouter()


@router.get("/v1/restaurants", response_model=RestaurantListResponse)
def list_restaurants(
    service: CommerceService = Depends(get_commerce_service),
) -> RestaurantListResponse:
    return service.list_restaurants()


@router.get("/v1/restaurants/{restaurant_id}", response_model=RestaurantResponse)
def get_restaurant(
    restaurant_id: str,
    service: CommerceService = Depends(get_commerce_service),
) -> RestaurantResponse:
    return service.get_restaurant(restaurant_id)


@router.get("/v1/restaurants/{restaurant_id}/locations", response_model=LocationListResponse)
def list_locations(
    restaurant_id: str,
    channel: Channel | None = Query(default=None),
    service: CommerceService = Depends(get_commerce_service),
) -> LocationListResponse:
    return service.list_locations(restaurant_id, channel)


@router.get("/v1/locations/{location_id}", response_model=LocationResponse)
def get_location(
    location_id: str,
    service: CommerceService = Depends(get_commerce_service),
) -> LocationResponse:
    return service.get_location(location_id)
