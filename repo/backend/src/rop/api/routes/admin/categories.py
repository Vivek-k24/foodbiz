from __future__ import annotations

from fastapi import APIRouter, Depends, status

from rop.api.dependencies import get_catalog_service
from rop.application.catalog.schemas import (
    CategoryCreateRequest,
    CategoryResponse,
    CategoryUpdateRequest,
)
from rop.application.catalog.service import CatalogService

router = APIRouter()


@router.post(
    "/v1/admin/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED
)
def create_category(
    request: CategoryCreateRequest,
    service: CatalogService = Depends(get_catalog_service),
) -> CategoryResponse:
    return service.create_category(request)


@router.get("/v1/admin/categories/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: str,
    service: CatalogService = Depends(get_catalog_service),
) -> CategoryResponse:
    return service.get_category(category_id)


@router.patch("/v1/admin/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: str,
    request: CategoryUpdateRequest,
    service: CatalogService = Depends(get_catalog_service),
) -> CategoryResponse:
    return service.update_category(category_id, request)


@router.delete("/v1/admin/categories/{category_id}", response_model=CategoryResponse)
def delete_category(
    category_id: str,
    service: CatalogService = Depends(get_catalog_service),
) -> CategoryResponse:
    return service.delete_category(category_id)
