from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from rop.infrastructure.db.models import (
    CategoryModel,
    LocationModel,
    MenuItemModel,
    RestaurantModel,
    TableModel,
)
from rop.infrastructure.db.session import get_engine


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _upsert(session: Session, model, record_id: str, **values):
    instance = session.get(model, record_id)
    if instance is None:
        instance = model(id=record_id, **values)
        session.add(instance)
    else:
        for field, value in values.items():
            setattr(instance, field, value)
    return instance


def main() -> None:
    engine = get_engine(timeout_seconds=2.0)
    inspector = inspect(engine)
    required_tables = {
        "restaurants",
        "locations",
        "tables",
        "categories",
        "menu_items",
        "sessions",
        "orders",
        "order_lines",
        "order_status_history",
    }
    if not required_tables.issubset(set(inspector.get_table_names(schema="public"))):
        print("no schema yet")
        return

    now = _utcnow()
    with Session(engine) as session:
        _upsert(
            session,
            RestaurantModel,
            "rst_001",
            slug="foodbiz-main",
            name="FoodBiz Main Street",
            status="active",
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

        _upsert(
            session,
            LocationModel,
            "loc_001",
            restaurant_id="rst_001",
            name="Main Street Dining Room",
            location_type="restaurant",
            is_active=True,
            supports_dine_in=True,
            supports_pickup=True,
            supports_delivery=True,
            address_line_1="100 Main Street",
            address_line_2=None,
            city="Chicago",
            state="IL",
            postal_code="60601",
            country="US",
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        _upsert(
            session,
            LocationModel,
            "loc_002",
            restaurant_id="rst_001",
            name="Pickup Window",
            location_type="pickup_hub",
            is_active=True,
            supports_dine_in=False,
            supports_pickup=True,
            supports_delivery=True,
            address_line_1="100 Main Street",
            address_line_2="Rear Entrance",
            city="Chicago",
            state="IL",
            postal_code="60601",
            country="US",
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

        _upsert(
            session,
            TableModel,
            "tbl_001",
            restaurant_id="rst_001",
            location_id="loc_001",
            label="Table 1",
            capacity=4,
            status="available",
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        _upsert(
            session,
            TableModel,
            "tbl_002",
            restaurant_id="rst_001",
            location_id="loc_001",
            label="Table 2",
            capacity=2,
            status="available",
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

        _upsert(
            session,
            CategoryModel,
            "cat_001",
            restaurant_id="rst_001",
            name="Starters",
            sort_order=1,
            is_active=True,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        _upsert(
            session,
            CategoryModel,
            "cat_002",
            restaurant_id="rst_001",
            name="Mains",
            sort_order=2,
            is_active=True,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

        _upsert(
            session,
            MenuItemModel,
            "itm_001",
            restaurant_id="rst_001",
            category_id="cat_001",
            sku="BURRATA",
            name="Burrata Plate",
            description="Burrata, tomato jam, grilled bread.",
            price=Decimal("12.50"),
            currency="USD",
            is_active=True,
            is_available=True,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        _upsert(
            session,
            MenuItemModel,
            "itm_002",
            restaurant_id="rst_001",
            category_id="cat_002",
            sku="SMASH",
            name="Smash Burger",
            description="Two patties, cheddar, house sauce.",
            price=Decimal("16.00"),
            currency="USD",
            is_active=True,
            is_available=True,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        _upsert(
            session,
            MenuItemModel,
            "itm_003",
            restaurant_id="rst_001",
            category_id="cat_002",
            sku="MARGHERITA",
            name="Margherita Pizza",
            description="Tomato, mozzarella, basil.",
            price=Decimal("15.00"),
            currency="USD",
            is_active=True,
            is_available=True,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )

        session.commit()
        print("seed complete")


if __name__ == "__main__":
    main()
