from __future__ import annotations

from fastapi import APIRouter, Depends

from rop.api.dependencies import get_catalog_service
from rop.application.catalog.schemas import CatalogResponse
from rop.application.catalog.service import CatalogService

router = APIRouter()


@router.get("/v1/restaurants/{restaurant_id}/catalog", response_model=CatalogResponse)
def get_public_catalog(
    restaurant_id: str,
    service: CatalogService = Depends(get_catalog_service),
) -> CatalogResponse:
    return service.get_public_catalog(restaurant_id)
