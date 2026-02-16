from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from rop.application.use_cases.get_menu import (
    GetMenu,
    MenuNotFoundError,
    menu_payload_cache_key,
    menu_version_cache_key,
)
from rop.domain.common.ids import MenuId, MenuItemId, RestaurantId
from rop.domain.common.money import Money
from rop.domain.menu.entities import Menu, MenuItem


class FakeMenuRepository:
    def __init__(self, menu: Menu | None):
        self._menu = menu
        self.calls = 0

    def get_menu_by_restaurant_id(self, restaurant_id: RestaurantId) -> Menu | None:
        self.calls += 1
        return self._menu


class FakeCacheStore:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self.values[key] = value


def _sample_menu() -> Menu:
    return Menu(
        menu_id=MenuId("men_001"),
        restaurant_id=RestaurantId("rst_001"),
        version=1,
        categories=[],
        items=[
            MenuItem(
                item_id=MenuItemId("itm_001"),
                name="Margherita Pizza",
                description="Classic",
                price_money=Money(amount_cents=1400, currency="USD"),
                is_available=True,
            )
        ],
        updated_at=datetime.now(timezone.utc),
    )


def test_get_menu_uses_cache_when_warm() -> None:
    restaurant_id = RestaurantId("rst_001")
    menu = _sample_menu()
    repo = FakeMenuRepository(menu=menu)
    cache = FakeCacheStore()

    warm_payload = GetMenu(repository=repo, cache=cache).execute(restaurant_id)
    cache.values[menu_version_cache_key(restaurant_id)] = str(warm_payload.menuVersion)
    cache.values[menu_payload_cache_key(restaurant_id, warm_payload.menuVersion)] = (
        warm_payload.model_dump_json()
    )
    repo.calls = 0

    response = GetMenu(repository=repo, cache=cache).execute(restaurant_id)

    assert repo.calls == 0
    assert response.menuVersion == 1
    assert response.items[0].name == "Margherita Pizza"


def test_get_menu_populates_cache_on_miss() -> None:
    restaurant_id = RestaurantId("rst_001")
    repo = FakeMenuRepository(menu=_sample_menu())
    cache = FakeCacheStore()

    response = GetMenu(repository=repo, cache=cache).execute(restaurant_id)

    assert repo.calls == 1
    assert cache.values[menu_version_cache_key(restaurant_id)] == "1"
    assert menu_payload_cache_key(restaurant_id, 1) in cache.values
    assert response.restaurantId == "rst_001"


def test_get_menu_raises_when_not_found() -> None:
    restaurant_id = RestaurantId("rst_404")
    repo = FakeMenuRepository(menu=None)
    cache = FakeCacheStore()

    with pytest.raises(MenuNotFoundError):
        GetMenu(repository=repo, cache=cache).execute(restaurant_id)
