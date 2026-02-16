from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Response

from rop.application.dto.responses import MenuResponse
from rop.application.use_cases.get_menu import GetMenu, MenuNotFoundError
from rop.domain.common.ids import RestaurantId
from rop.infrastructure.cache.cache_store import RedisCacheStore
from rop.infrastructure.db.repositories.menu_repo import SqlAlchemyMenuRepository

router = APIRouter()


def _get_menu_use_case() -> GetMenu:
    return GetMenu(
        repository=SqlAlchemyMenuRepository(),
        cache=RedisCacheStore(),
        ttl_seconds=300,
    )


@router.get("/v1/restaurants/{restaurant_id}/menu", response_model=MenuResponse)
def get_menu(
    restaurant_id: str,
    response: Response,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
) -> MenuResponse | Response:
    use_case = _get_menu_use_case()
    try:
        payload = use_case.execute(RestaurantId(restaurant_id))
    except MenuNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    etag = f'"menu-v{payload.menuVersion}"'
    if if_none_match == etag:
        return Response(status_code=304, headers={"ETag": etag})

    response.headers["ETag"] = etag
    return payload
