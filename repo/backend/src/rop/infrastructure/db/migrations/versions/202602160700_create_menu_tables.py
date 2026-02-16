"""create menu tables

Revision ID: 202602160700
Revises:
Create Date: 2026-02-16 07:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202602160700"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "restaurants",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "menus",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("restaurant_id", sa.String(length=50), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("restaurant_id", "version", name="uq_menus_restaurant_version"),
    )
    op.create_index("ix_menus_restaurant_id", "menus", ["restaurant_id"], unique=False)

    op.create_table(
        "menu_items",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("menu_id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("is_available", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(["menu_id"], ["menus.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_menu_items_menu_id", "menu_items", ["menu_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_menu_items_menu_id", table_name="menu_items")
    op.drop_table("menu_items")
    op.drop_index("ix_menus_restaurant_id", table_name="menus")
    op.drop_table("menus")
    op.drop_table("restaurants")
