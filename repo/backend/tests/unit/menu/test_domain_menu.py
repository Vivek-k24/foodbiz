from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from rop.domain.common.ids import MenuId, MenuItemId, RestaurantId
from rop.domain.common.money import Money
from rop.domain.menu.entities import Menu, MenuItem


def test_money_invariants() -> None:
    with pytest.raises(ValueError):
        Money(amount_cents=-1, currency="USD")
    with pytest.raises(ValueError):
        Money(amount_cents=100, currency="usd")
    with pytest.raises(ValueError):
        Money(amount_cents=100, currency="US")


def test_menu_item_name_must_be_non_empty() -> None:
    with pytest.raises(ValueError):
        MenuItem(
            item_id=MenuItemId("itm_001"),
            name="   ",
            description=None,
            price_money=Money(amount_cents=100, currency="USD"),
            is_available=True,
        )


def test_menu_version_must_be_gte_one() -> None:
    with pytest.raises(ValueError):
        Menu(
            menu_id=MenuId("men_001"),
            restaurant_id=RestaurantId("rst_001"),
            version=0,
            categories=[],
            items=[],
            updated_at=datetime.now(timezone.utc),
        )
