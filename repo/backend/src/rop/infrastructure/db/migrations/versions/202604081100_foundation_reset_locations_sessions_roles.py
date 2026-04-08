"""foundation reset: locations sessions roles categories order events

Revision ID: 202604081100
Revises: 202604040901
Create Date: 2026-04-08 11:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202604081100"
down_revision = "202604040901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "restaurants",
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
    )
    op.add_column(
        "restaurants",
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
    )
    op.add_column(
        "restaurants",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.alter_column("restaurants", "timezone", server_default=None)
    op.alter_column("restaurants", "currency", server_default=None)
    op.alter_column("restaurants", "created_at", server_default=None)

    op.create_table(
        "roles",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("role_group", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_roles_code", "roles", ["code"], unique=False)
    op.create_index("ix_roles_role_group", "roles", ["role_group"], unique=False)

    op.create_table(
        "locations",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("restaurant_id", sa.String(length=50), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("display_label", sa.String(length=255), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("zone", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_locations_restaurant_id", "locations", ["restaurant_id"], unique=False)
    op.create_index("ix_locations_type", "locations", ["type"], unique=False)

    op.execute(
        """
        INSERT INTO locations (
            id, restaurant_id, type, name, display_label, capacity, zone, is_active, created_at
        )
        SELECT
            'loc_' || t.id,
            t.restaurant_id,
            'TABLE',
            t.id,
            upper(t.id),
            4,
            'Dining Room',
            true,
            COALESCE(t.opened_at, timezone('utc', now()))
        FROM tables AS t
        ON CONFLICT (id) DO NOTHING
        """
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("restaurant_id", sa.String(length=50), nullable=False),
        sa.Column("location_id", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "opened_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_by_role_id", sa.String(length=50), nullable=True),
        sa.Column("opened_by_source", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opened_by_role_id"], ["roles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_restaurant_id", "sessions", ["restaurant_id"], unique=False)
    op.create_index("ix_sessions_location_id", "sessions", ["location_id"], unique=False)
    op.create_index("ix_sessions_status", "sessions", ["status"], unique=False)

    op.execute(
        """
        INSERT INTO sessions (
            id, restaurant_id, location_id, status, opened_at, closed_at, opened_by_source, notes
        )
        SELECT
            'ses_migr_' || t.id,
            t.restaurant_id,
            'loc_' || t.id,
            CASE WHEN t.status = 'OPEN' THEN 'OPEN' ELSE 'CLOSED' END,
            COALESCE(t.opened_at, timezone('utc', now())),
            t.closed_at,
            'SYSTEM',
            'Migrated from legacy table state'
        FROM tables AS t
        ON CONFLICT (id) DO NOTHING
        """
    )

    op.create_table(
        "menu_categories",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("restaurant_id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category_kind", sa.String(length=20), nullable=False),
        sa.Column("cuisine_or_family", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_menu_categories_restaurant_id", "menu_categories", ["restaurant_id"], unique=False
    )

    op.add_column(
        "menu_items",
        sa.Column("restaurant_id", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "menu_items",
        sa.Column("category_id", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "menu_items",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.execute(
        """
        UPDATE menu_items AS mi
        SET restaurant_id = m.restaurant_id
        FROM menus AS m
        WHERE mi.menu_id = m.id
        """
    )
    op.alter_column("menu_items", "restaurant_id", nullable=False)
    op.create_foreign_key(
        "fk_menu_items_restaurant_id_restaurants",
        "menu_items",
        "restaurants",
        ["restaurant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_menu_items_category_id_menu_categories",
        "menu_items",
        "menu_categories",
        ["category_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_menu_items_restaurant_id", "menu_items", ["restaurant_id"], unique=False)
    op.create_index("ix_menu_items_category_id", "menu_items", ["category_id"], unique=False)
    op.alter_column("menu_items", "created_at", server_default=None)

    op.add_column("orders", sa.Column("location_id", sa.String(length=50), nullable=True))
    op.add_column("orders", sa.Column("session_id", sa.String(length=50), nullable=True))
    op.add_column(
        "orders",
        sa.Column("source", sa.String(length=30), nullable=False, server_default="WEB_DINE_IN"),
    )
    op.add_column(
        "orders",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.execute(
        """
        UPDATE orders
        SET location_id = 'loc_' || table_id,
            updated_at = created_at
        """
    )
    op.alter_column("orders", "table_id", nullable=True)
    op.alter_column("orders", "location_id", nullable=False)
    op.create_foreign_key(
        "fk_orders_location_id_locations",
        "orders",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_orders_session_id_sessions",
        "orders",
        "sessions",
        ["session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_orders_location_created_at_desc",
        "orders",
        ["location_id", "created_at"],
        unique=False,
    )
    op.alter_column("orders", "source", server_default=None)
    op.alter_column("orders", "updated_at", server_default=None)

    op.add_column(
        "order_lines",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.alter_column("order_lines", "created_at", server_default=None)

    op.create_table(
        "order_events",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("order_id", sa.String(length=50), nullable=False),
        sa.Column("restaurant_id", sa.String(length=50), nullable=False),
        sa.Column("location_id", sa.String(length=50), nullable=False),
        sa.Column("session_id", sa.String(length=50), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("order_status_after", sa.String(length=20), nullable=False),
        sa.Column("triggered_by_source", sa.String(length=30), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_events_order_id", "order_events", ["order_id"], unique=False)
    op.create_index(
        "ix_order_events_restaurant_id", "order_events", ["restaurant_id"], unique=False
    )
    op.create_index("ix_order_events_location_id", "order_events", ["location_id"], unique=False)
    op.create_index("ix_order_events_session_id", "order_events", ["session_id"], unique=False)
    op.create_index("ix_order_events_event_type", "order_events", ["event_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_order_events_event_type", table_name="order_events")
    op.drop_index("ix_order_events_session_id", table_name="order_events")
    op.drop_index("ix_order_events_location_id", table_name="order_events")
    op.drop_index("ix_order_events_restaurant_id", table_name="order_events")
    op.drop_index("ix_order_events_order_id", table_name="order_events")
    op.drop_table("order_events")

    op.drop_column("order_lines", "created_at")

    op.drop_index("ix_orders_location_created_at_desc", table_name="orders")
    op.drop_constraint("fk_orders_session_id_sessions", "orders", type_="foreignkey")
    op.drop_constraint("fk_orders_location_id_locations", "orders", type_="foreignkey")
    op.drop_column("orders", "updated_at")
    op.drop_column("orders", "source")
    op.drop_column("orders", "session_id")
    op.drop_column("orders", "location_id")
    op.alter_column("orders", "table_id", nullable=False)

    op.drop_index("ix_menu_items_category_id", table_name="menu_items")
    op.drop_index("ix_menu_items_restaurant_id", table_name="menu_items")
    op.drop_constraint(
        "fk_menu_items_category_id_menu_categories", "menu_items", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_menu_items_restaurant_id_restaurants",
        "menu_items",
        type_="foreignkey",
    )
    op.drop_column("menu_items", "created_at")
    op.drop_column("menu_items", "category_id")
    op.drop_column("menu_items", "restaurant_id")

    op.drop_index("ix_menu_categories_restaurant_id", table_name="menu_categories")
    op.drop_table("menu_categories")

    op.drop_index("ix_sessions_status", table_name="sessions")
    op.drop_index("ix_sessions_location_id", table_name="sessions")
    op.drop_index("ix_sessions_restaurant_id", table_name="sessions")
    op.drop_table("sessions")

    op.drop_index("ix_locations_type", table_name="locations")
    op.drop_index("ix_locations_restaurant_id", table_name="locations")
    op.drop_table("locations")

    op.drop_index("ix_roles_role_group", table_name="roles")
    op.drop_index("ix_roles_code", table_name="roles")
    op.drop_table("roles")

    op.drop_column("restaurants", "created_at")
    op.drop_column("restaurants", "currency")
    op.drop_column("restaurants", "timezone")
