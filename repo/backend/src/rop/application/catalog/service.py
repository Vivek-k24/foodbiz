from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from rop.application.catalog.schemas import (
    CatalogResponse,
    CategoryCreateRequest,
    CategoryResponse,
    CategoryUpdateRequest,
    MenuItemCreateRequest,
    MenuItemResponse,
    MenuItemUpdateRequest,
    PublicCategoryResponse,
    PublicMenuItemResponse,
)
from rop.domain.errors import NotFoundError
from rop.infrastructure.db.models import CategoryModel, MenuItemModel, RestaurantModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


class CatalogService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _require_restaurant(self, restaurant_id: str) -> RestaurantModel:
        restaurant = self._db.get(RestaurantModel, restaurant_id)
        if restaurant is None or restaurant.deleted_at is not None:
            raise NotFoundError("restaurant not found", code="RESTAURANT_NOT_FOUND")
        return restaurant

    def _require_category(self, category_id: str) -> CategoryModel:
        category = self._db.get(CategoryModel, category_id)
        if category is None:
            raise NotFoundError("category not found", code="CATEGORY_NOT_FOUND")
        return category

    def _require_menu_item(self, item_id: str) -> MenuItemModel:
        item = self._db.get(MenuItemModel, item_id)
        if item is None:
            raise NotFoundError("menu item not found", code="MENU_ITEM_NOT_FOUND")
        return item

    def _serialize_category(self, category: CategoryModel) -> CategoryResponse:
        return CategoryResponse(
            id=category.id,
            restaurant_id=category.restaurant_id,
            name=category.name,
            sort_order=category.sort_order,
            is_active=category.is_active,
            created_at=category.created_at,
            updated_at=category.updated_at,
            deleted_at=category.deleted_at,
        )

    def _serialize_item(self, item: MenuItemModel) -> MenuItemResponse:
        return MenuItemResponse(
            id=item.id,
            restaurant_id=item.restaurant_id,
            category_id=item.category_id,
            sku=item.sku,
            name=item.name,
            description=item.description,
            price=_money(item.price),
            currency=item.currency,
            is_active=item.is_active,
            is_available=item.is_available,
            created_at=item.created_at,
            updated_at=item.updated_at,
            deleted_at=item.deleted_at,
        )

    def create_category(self, request: CategoryCreateRequest) -> CategoryResponse:
        self._require_restaurant(request.restaurant_id)
        category = CategoryModel(
            id=f"cat_{uuid4().hex[:12]}",
            restaurant_id=request.restaurant_id,
            name=request.name.strip(),
            sort_order=request.sort_order,
            is_active=request.is_active,
        )
        self._db.add(category)
        self._db.commit()
        self._db.refresh(category)
        return self._serialize_category(category)

    def get_category(self, category_id: str) -> CategoryResponse:
        return self._serialize_category(self._require_category(category_id))

    def update_category(self, category_id: str, request: CategoryUpdateRequest) -> CategoryResponse:
        category = self._require_category(category_id)
        if request.name is not None:
            category.name = request.name.strip()
        if request.sort_order is not None:
            category.sort_order = request.sort_order
        if request.is_active is not None:
            category.is_active = request.is_active
        category.updated_at = _utcnow()
        self._db.commit()
        self._db.refresh(category)
        return self._serialize_category(category)

    def delete_category(self, category_id: str) -> CategoryResponse:
        category = self._require_category(category_id)
        category.is_active = False
        category.deleted_at = _utcnow()
        category.updated_at = category.deleted_at
        self._db.commit()
        self._db.refresh(category)
        return self._serialize_category(category)

    def create_menu_item(self, request: MenuItemCreateRequest) -> MenuItemResponse:
        self._require_restaurant(request.restaurant_id)
        if request.category_id:
            category = self._require_category(request.category_id)
            if category.restaurant_id != request.restaurant_id:
                raise NotFoundError("category not found for restaurant", code="CATEGORY_NOT_FOUND")

        item = MenuItemModel(
            id=f"itm_{uuid4().hex[:12]}",
            restaurant_id=request.restaurant_id,
            category_id=request.category_id,
            sku=request.sku.strip() if request.sku else None,
            name=request.name.strip(),
            description=request.description,
            price=request.price,
            currency=request.currency.upper(),
            is_active=request.is_active,
            is_available=request.is_available,
        )
        self._db.add(item)
        self._db.commit()
        self._db.refresh(item)
        return self._serialize_item(item)

    def get_menu_item(self, item_id: str) -> MenuItemResponse:
        return self._serialize_item(self._require_menu_item(item_id))

    def update_menu_item(self, item_id: str, request: MenuItemUpdateRequest) -> MenuItemResponse:
        item = self._require_menu_item(item_id)
        if request.category_id is not None:
            if request.category_id:
                category = self._require_category(request.category_id)
                if category.restaurant_id != item.restaurant_id:
                    raise NotFoundError(
                        "category not found for restaurant",
                        code="CATEGORY_NOT_FOUND",
                    )
            item.category_id = request.category_id
        if request.sku is not None:
            item.sku = request.sku.strip() if request.sku else None
        if request.name is not None:
            item.name = request.name.strip()
        if request.description is not None:
            item.description = request.description
        if request.price is not None:
            item.price = request.price
        if request.currency is not None:
            item.currency = request.currency.upper()
        if request.is_active is not None:
            item.is_active = request.is_active
        if request.is_available is not None:
            item.is_available = request.is_available
        item.updated_at = _utcnow()
        self._db.commit()
        self._db.refresh(item)
        return self._serialize_item(item)

    def delete_menu_item(self, item_id: str) -> MenuItemResponse:
        item = self._require_menu_item(item_id)
        item.is_active = False
        item.is_available = False
        item.deleted_at = _utcnow()
        item.updated_at = item.deleted_at
        self._db.commit()
        self._db.refresh(item)
        return self._serialize_item(item)

    def get_public_catalog(self, restaurant_id: str) -> CatalogResponse:
        self._require_restaurant(restaurant_id)
        categories = self._db.scalars(
            select(CategoryModel)
            .where(
                CategoryModel.restaurant_id == restaurant_id,
                CategoryModel.deleted_at.is_(None),
                CategoryModel.is_active.is_(True),
            )
            .order_by(CategoryModel.sort_order.asc(), CategoryModel.name.asc())
        ).all()
        items = self._db.scalars(
            select(MenuItemModel)
            .where(
                MenuItemModel.restaurant_id == restaurant_id,
                MenuItemModel.deleted_at.is_(None),
                MenuItemModel.is_active.is_(True),
                MenuItemModel.is_available.is_(True),
            )
            .order_by(MenuItemModel.name.asc())
        ).all()

        grouped_items: dict[str | None, list[PublicMenuItemResponse]] = defaultdict(list)
        for item in items:
            grouped_items[item.category_id].append(
                PublicMenuItemResponse(
                    id=item.id,
                    category_id=item.category_id,
                    sku=item.sku,
                    name=item.name,
                    description=item.description,
                    price=_money(item.price),
                    currency=item.currency,
                    is_available=item.is_available,
                )
            )

        payload_categories = [
            PublicCategoryResponse(
                id=category.id,
                name=category.name,
                sort_order=category.sort_order,
                items=grouped_items.get(category.id, []),
            )
            for category in categories
        ]
        return CatalogResponse(restaurant_id=restaurant_id, categories=payload_categories)
