from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from rop.domain.commerce.enums import (
    ActorType,
    Channel,
    LocationType,
    OrderStatus,
    RestaurantStatus,
    SessionStatus,
    SourceType,
    TableStatus,
)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RestaurantModel(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "restaurants"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=RestaurantStatus.ACTIVE.value,
        index=True,
    )

    locations: Mapped[list["LocationModel"]] = relationship(back_populates="restaurant")
    categories: Mapped[list["CategoryModel"]] = relationship(back_populates="restaurant")
    menu_items: Mapped[list["MenuItemModel"]] = relationship(back_populates="restaurant")


class LocationModel(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    restaurant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=LocationType.RESTAURANT.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    supports_dine_in: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    supports_pickup: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    supports_delivery: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    address_line_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True, server_default="US")

    restaurant: Mapped[RestaurantModel] = relationship(back_populates="locations")
    tables: Mapped[list["TableModel"]] = relationship(back_populates="location")

    __table_args__ = (
        Index("ix_locations_restaurant_id", "restaurant_id"),
        Index("ix_locations_supports_dine_in", "supports_dine_in"),
        Index("ix_locations_supports_pickup", "supports_pickup"),
        Index("ix_locations_supports_delivery", "supports_delivery"),
    )


class TableModel(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "tables"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    restaurant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
    )
    location_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=TableStatus.AVAILABLE.value,
        index=True,
    )

    location: Mapped[LocationModel | None] = relationship(back_populates="tables")

    __table_args__ = (
        Index("ix_tables_restaurant_id", "restaurant_id"),
        Index("ix_tables_location_id", "location_id"),
        UniqueConstraint("restaurant_id", "label", name="uq_tables_restaurant_label"),
    )


class CategoryModel(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    restaurant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    restaurant: Mapped[RestaurantModel] = relationship(back_populates="categories")
    menu_items: Mapped[list["MenuItemModel"]] = relationship(back_populates="category")

    __table_args__ = (Index("ix_categories_restaurant_id", "restaurant_id"),)


class MenuItemModel(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "menu_items"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    restaurant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    sku: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    restaurant: Mapped[RestaurantModel] = relationship(back_populates="menu_items")
    category: Mapped[CategoryModel | None] = relationship(back_populates="menu_items")

    __table_args__ = (
        Index("ix_menu_items_restaurant_id", "restaurant_id"),
        Index("ix_menu_items_category_id", "category_id"),
        Index("ix_menu_items_sku", "sku"),
    )


class SessionModel(TimestampMixin, Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    restaurant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
    )
    location_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    table_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("tables.id", ondelete="SET NULL"),
        nullable=True,
    )
    external_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_sessions_restaurant_id", "restaurant_id"),
        Index("ix_sessions_location_id", "location_id"),
        Index("ix_sessions_table_id", "table_id"),
        Index("ix_sessions_external_reference", "external_reference"),
        CheckConstraint("channel in ('dine_in','pickup','delivery','third_party')"),
        CheckConstraint(
            "source_type in "
            "('qr','business_website','waiter_entered','counter_entered','uber_eats','doordash')"
        ),
        CheckConstraint("status in ('open','closed','expired')"),
    )


class OrderModel(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    restaurant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
    )
    location_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    table_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("tables.id", ondelete="SET NULL"),
        nullable=True,
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    external_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default="0",
    )
    tax_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, server_default="0")
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    lines: Mapped[list["OrderLineModel"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderLineModel.created_at",
    )

    __table_args__ = (
        Index("ix_orders_restaurant_id", "restaurant_id"),
        Index("ix_orders_location_id", "location_id"),
        Index("ix_orders_session_id", "session_id"),
        Index("ix_orders_table_id", "table_id"),
        Index("ix_orders_external_reference", "external_reference"),
        UniqueConstraint(
            "restaurant_id",
            "idempotency_key",
            name="uq_orders_restaurant_idempotency",
        ),
        CheckConstraint("channel in ('dine_in','pickup','delivery','third_party')"),
        CheckConstraint(
            "source_type in "
            "('qr','business_website','waiter_entered','counter_entered','uber_eats','doordash')"
        ),
        CheckConstraint("status in ('pending','accepted','ready','served','settled','canceled')"),
    )


class OrderLineModel(TimestampMixin, Base):
    __tablename__ = "order_lines"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    menu_item_id: Mapped[str | None] = mapped_column(
        String(50),
        ForeignKey("menu_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    item_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped[OrderModel] = relationship(back_populates="lines")

    __table_args__ = (
        Index("ix_order_lines_order_id", "order_id"),
        Index("ix_order_lines_menu_item_id", "menu_item_id"),
    )


class OrderStatusHistoryModel(Base):
    __tablename__ = "order_status_history"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_order_status_history_order_id", "order_id"),
        CheckConstraint(
            "to_status in ('pending','accepted','ready','served','settled','canceled')"
        ),
        CheckConstraint(
            "actor_type in ('system','staff','kitchen','customer','integration','admin')"
        ),
    )


__all__ = [
    "ActorType",
    "Base",
    "CategoryModel",
    "Channel",
    "LocationModel",
    "LocationType",
    "MenuItemModel",
    "OrderLineModel",
    "OrderModel",
    "OrderStatus",
    "OrderStatusHistoryModel",
    "RestaurantModel",
    "RestaurantStatus",
    "SessionModel",
    "SessionStatus",
    "SourceType",
    "TableModel",
    "TableStatus",
]
