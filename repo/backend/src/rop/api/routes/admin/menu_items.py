from __future__ import annotations

from fastapi import APIRouter, Depends, status

from rop.api.dependencies import get_catalog_service
from rop.application.catalog.schemas import (
    MenuItemCreateRequest,
    MenuItemResponse,
    MenuItemUpdateRequest,
)
from rop.application.catalog.service import CatalogService

router = APIRouter()


@router.post(
    "/v1/admin/menu-items", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED
)
def create_menu_item(
    request: MenuItemCreateRequest,
    service: CatalogService = Depends(get_catalog_service),
) -> MenuItemResponse:
    return service.create_menu_item(request)


@router.get("/v1/admin/menu-items/{item_id}", response_model=MenuItemResponse)
def get_menu_item(
    item_id: str,
    service: CatalogService = Depends(get_catalog_service),
) -> MenuItemResponse:
    return service.get_menu_item(item_id)


@router.patch("/v1/admin/menu-items/{item_id}", response_model=MenuItemResponse)
def update_menu_item(
    item_id: str,
    request: MenuItemUpdateRequest,
    service: CatalogService = Depends(get_catalog_service),
) -> MenuItemResponse:
    return service.update_menu_item(item_id, request)


@router.delete("/v1/admin/menu-items/{item_id}", response_model=MenuItemResponse)
def delete_menu_item(
    item_id: str,
    service: CatalogService = Depends(get_catalog_service),
) -> MenuItemResponse:
    return service.delete_menu_item(item_id)
