from __future__ import annotations

from datetime import timezone
from typing import Any, cast

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, joinedload

from rop.application.ports.repositories import MenuRepository
from rop.domain.common.ids import MenuId, MenuItemId, RestaurantId
from rop.domain.common.money import Money
from rop.domain.menu.entities import AllowedModifier, Menu, MenuItem, ModifierKind
from rop.infrastructure.db.models.menu import MenuModel
from rop.infrastructure.db.session import get_engine


class SqlAlchemyMenuRepository(MenuRepository):
    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine or get_engine()

    def get_menu_by_restaurant_id(self, restaurant_id: RestaurantId) -> Menu | None:
        statement = (
            select(MenuModel)
            .options(joinedload(MenuModel.items))
            .where(MenuModel.restaurant_id == str(restaurant_id))
            .order_by(MenuModel.version.desc())
            .limit(1)
        )

        with Session(self._engine) as session:
            menu_model = session.execute(statement).unique().scalar_one_or_none()

        if menu_model is None:
            return None

        updated_at = menu_model.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        items = []
        for item in menu_model.items:
            allowed_modifiers = [
                modifier
                for modifier in (
                    _allowed_modifier_from_payload(payload)
                    for payload in (item.allowed_modifiers_json or [])
                )
                if modifier is not None
            ]
            items.append(
                MenuItem(
                    item_id=MenuItemId(item.id),
                    name=item.name,
                    description=item.description,
                    price_money=Money(amount_cents=item.price_cents, currency=item.currency),
                    is_available=item.is_available,
                    category_id=None,
                    allowed_modifiers=allowed_modifiers,
                )
            )

        return Menu(
            menu_id=MenuId(menu_model.id),
            restaurant_id=RestaurantId(menu_model.restaurant_id),
            version=menu_model.version,
            categories=[],
            items=items,
            updated_at=updated_at,
        )


def _allowed_modifier_from_payload(payload: Any) -> AllowedModifier | None:
    if not isinstance(payload, dict):
        return None

    kind = payload.get("kind")
    if kind not in {"toggle", "choice", "text"}:
        return None

    options_raw = payload.get("options")
    options = (
        [option for option in options_raw if isinstance(option, str)]
        if isinstance(options_raw, list)
        else []
    )
    return AllowedModifier(
        code=str(payload.get("code", "")),
        label=str(payload.get("label", "")),
        kind=cast(ModifierKind, kind),
        options=options,
    )
