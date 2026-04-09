"""channel aware platform reset

Revision ID: 202604091200
Revises: 202604081100
Create Date: 2026-04-09 12:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "202604091200"
down_revision = "202604081100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table_name in [
        "order_status_history",
        "order_lines",
        "orders",
        "sessions",
        "tables",
        "menu_items",
        "categories",
        "menu_categories",
        "menus",
        "locations",
        "roles",
        "restaurants",
    ]:
        op.execute(sa.text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))

    op.create_table(
        "restaurants",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_restaurants_slug"),
    )
    op.create_index("ix_restaurants_slug", "restaurants", ["slug"], unique=False)
    op.create_index("ix_restaurants_status", "restaurants", ["status"], unique=False)

    op.create_table(
        "locations",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("restaurant_id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "location_type", sa.String(length=30), nullable=False, server_default="restaurant"
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("supports_dine_in", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("supports_pickup", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("supports_delivery", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("address_line_1", sa.String(length=255), nullable=True),
        sa.Column("address_line_2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=True, server_default="US"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_locations_restaurant_id", "locations", ["restaurant_id"], unique=False)
    op.create_index(
        "ix_locations_supports_dine_in", "locations", ["supports_dine_in"], unique=False
    )
    op.create_index("ix_locations_supports_pickup", "locations", ["supports_pickup"], unique=False)
    op.create_index(
        "ix_locations_supports_delivery", "locations", ["supports_delivery"], unique=False
    )

    op.create_table(
        "tables",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("restaurant_id", sa.String(length=50), nullable=False),
        sa.Column("location_id", sa.String(length=50), nullable=True),
        sa.Column("label", sa.String(length=50), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="available"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("restaurant_id", "label", name="uq_tables_restaurant_label"),
    )
    op.create_index("ix_tables_restaurant_id", "tables", ["restaurant_id"], unique=False)
    op.create_index("ix_tables_location_id", "tables", ["location_id"], unique=False)
    op.create_index("ix_tables_status", "tables", ["status"], unique=False)

    op.create_table(
        "categories",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("restaurant_id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_categories_restaurant_id", "categories", ["restaurant_id"], unique=False)

    op.create_table(
        "menu_items",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("restaurant_id", sa.String(length=50), nullable=False),
        sa.Column("category_id", sa.String(length=50), nullable=True),
        sa.Column("sku", sa.String(length=50), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_menu_items_restaurant_id", "menu_items", ["restaurant_id"], unique=False)
    op.create_index("ix_menu_items_category_id", "menu_items", ["category_id"], unique=False)
    op.create_index("ix_menu_items_sku", "menu_items", ["sku"], unique=False)

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("restaurant_id", sa.String(length=50), nullable=False),
        sa.Column("location_id", sa.String(length=50), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("table_id", sa.String(length=50), nullable=True),
        sa.Column("external_source", sa.String(length=100), nullable=True),
        sa.Column("external_reference", sa.String(length=100), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("channel in ('dine_in','pickup','delivery','third_party')"),
        sa.CheckConstraint(
            "source_type in "
            "('qr','business_website','waiter_entered','counter_entered','uber_eats','doordash')"
        ),
        sa.CheckConstraint("status in ('open','closed','expired')"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_restaurant_id", "sessions", ["restaurant_id"], unique=False)
    op.create_index("ix_sessions_location_id", "sessions", ["location_id"], unique=False)
    op.create_index("ix_sessions_table_id", "sessions", ["table_id"], unique=False)
    op.create_index("ix_sessions_channel", "sessions", ["channel"], unique=False)
    op.create_index("ix_sessions_source_type", "sessions", ["source_type"], unique=False)
    op.create_index("ix_sessions_status", "sessions", ["status"], unique=False)
    op.create_index(
        "ix_sessions_external_reference", "sessions", ["external_reference"], unique=False
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("restaurant_id", sa.String(length=50), nullable=False),
        sa.Column("location_id", sa.String(length=50), nullable=True),
        sa.Column("session_id", sa.String(length=50), nullable=False),
        sa.Column("table_id", sa.String(length=50), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("external_source", sa.String(length=100), nullable=True),
        sa.Column("external_reference", sa.String(length=100), nullable=True),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False),
        sa.Column("discount_total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("tax_total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("idempotency_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("channel in ('dine_in','pickup','delivery','third_party')"),
        sa.CheckConstraint(
            "source_type in "
            "('qr','business_website','waiter_entered','counter_entered','uber_eats','doordash')"
        ),
        sa.CheckConstraint(
            "status in ('pending','accepted','ready','served','settled','canceled')"
        ),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "restaurant_id", "idempotency_key", name="uq_orders_restaurant_idempotency"
        ),
    )
    op.create_index("ix_orders_restaurant_id", "orders", ["restaurant_id"], unique=False)
    op.create_index("ix_orders_location_id", "orders", ["location_id"], unique=False)
    op.create_index("ix_orders_session_id", "orders", ["session_id"], unique=False)
    op.create_index("ix_orders_table_id", "orders", ["table_id"], unique=False)
    op.create_index("ix_orders_channel", "orders", ["channel"], unique=False)
    op.create_index("ix_orders_source_type", "orders", ["source_type"], unique=False)
    op.create_index("ix_orders_status", "orders", ["status"], unique=False)
    op.create_index("ix_orders_external_reference", "orders", ["external_reference"], unique=False)

    op.create_table(
        "order_lines",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("order_id", sa.String(length=50), nullable=False),
        sa.Column("menu_item_id", sa.String(length=50), nullable=True),
        sa.Column("item_name_snapshot", sa.String(length=255), nullable=False),
        sa.Column("unit_price_snapshot", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("line_total", sa.Numeric(10, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_lines_order_id", "order_lines", ["order_id"], unique=False)
    op.create_index("ix_order_lines_menu_item_id", "order_lines", ["menu_item_id"], unique=False)

    op.create_table(
        "order_status_history",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("order_id", sa.String(length=50), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=False),
        sa.Column("actor_type", sa.String(length=20), nullable=False),
        sa.Column("actor_id", sa.String(length=50), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "to_status in ('pending','accepted','ready','served','settled','canceled')"
        ),
        sa.CheckConstraint(
            "actor_type in ('system','staff','kitchen','customer','integration','admin')"
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_order_status_history_order_id", "order_status_history", ["order_id"], unique=False
    )


def downgrade() -> None:
    raise RuntimeError("ROP-201 reset migration is destructive and has no downgrade path")
