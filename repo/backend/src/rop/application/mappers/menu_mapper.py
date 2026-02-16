from __future__ import annotations

from rop.application.dto.responses import MenuItemResponse, MenuResponse, MoneyResponse
from rop.domain.menu.entities import Menu


def to_menu_response(menu: Menu) -> MenuResponse:
    items = [
        MenuItemResponse(
            itemId=str(item.item_id),
            name=item.name,
            description=item.description,
            priceMoney=MoneyResponse(
                amountCents=item.price_money.amount_cents,
                currency=item.price_money.currency,
            ),
            isAvailable=item.is_available,
            categoryId=item.category_id,
        )
        for item in menu.items
    ]
    return MenuResponse(
        menuId=str(menu.menu_id),
        restaurantId=str(menu.restaurant_id),
        menuVersion=menu.version,
        categories=menu.categories,
        items=items,
        updatedAt=menu.updated_at,
    )
