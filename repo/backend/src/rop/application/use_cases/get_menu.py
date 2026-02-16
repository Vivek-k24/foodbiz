from __future__ import annotations

from pydantic import ValidationError

from rop.application.dto.responses import MenuResponse
from rop.application.mappers.menu_mapper import to_menu_response
from rop.application.ports.cache import CacheStore
from rop.application.ports.repositories import MenuRepository
from rop.domain.common.ids import RestaurantId


class MenuNotFoundError(Exception):
    pass


def menu_version_cache_key(restaurant_id: RestaurantId) -> str:
    return f"menu:{restaurant_id}:version"


def menu_payload_cache_key(restaurant_id: RestaurantId, version: int) -> str:
    return f"menu:{restaurant_id}:v{version}"


class GetMenu:
    def __init__(
        self,
        repository: MenuRepository,
        cache: CacheStore,
        ttl_seconds: int = 300,
    ) -> None:
        self._repository = repository
        self._cache = cache
        self._ttl_seconds = ttl_seconds

    def _cache_get(self, key: str) -> str | None:
        try:
            return self._cache.get(key)
        except Exception:
            return None

    def _cache_set(self, key: str, value: str) -> None:
        try:
            self._cache.set(key, value, ttl_seconds=self._ttl_seconds)
        except Exception:
            return

    def execute(self, restaurant_id: RestaurantId) -> MenuResponse:
        version_key = menu_version_cache_key(restaurant_id)
        cached_version = self._cache_get(version_key)

        if cached_version is not None:
            try:
                version = int(cached_version)
            except ValueError:
                version = None

            if version is not None:
                payload_key = menu_payload_cache_key(restaurant_id, version)
                payload = self._cache_get(payload_key)
                if payload:
                    try:
                        return MenuResponse.model_validate_json(payload)
                    except ValidationError:
                        pass

        menu = self._repository.get_menu_by_restaurant_id(restaurant_id)
        if menu is None:
            raise MenuNotFoundError(f"menu not found for restaurant_id={restaurant_id}")

        response = to_menu_response(menu)
        self._cache_set(version_key, str(response.menuVersion))
        self._cache_set(
            menu_payload_cache_key(restaurant_id, response.menuVersion),
            response.model_dump_json(),
        )
        return response
