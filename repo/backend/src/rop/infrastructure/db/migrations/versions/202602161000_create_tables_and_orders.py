"""create tables and orders

Revision ID: 202602161000
Revises: 202602160700
Create Date: 2026-02-16 10:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202602161000"
down_revision = "202602160700"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tables",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("restaurant_id", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tables_restaurant_id", "tables", ["restaurant_id"], unique=False)

    op.create_table(
        "orders",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("restaurant_id", sa.String(length=50), nullable=False),
        sa.Column("table_id", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("total_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_orders_restaurant_created_at_desc",
        "orders",
        [sa.text("restaurant_id"), sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_orders_table_created_at_desc",
        "orders",
        [sa.text("table_id"), sa.text("created_at DESC")],
        unique=False,
    )

    op.create_table(
        "order_lines",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("order_id", sa.String(length=50), nullable=False),
        sa.Column("item_id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("line_total_cents", sa.Integer(), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_lines_order_id", "order_lines", ["order_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_order_lines_order_id", table_name="order_lines")
    op.drop_table("order_lines")
    op.drop_index("ix_orders_table_created_at_desc", table_name="orders")
    op.drop_index("ix_orders_restaurant_created_at_desc", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_tables_restaurant_id", table_name="tables")
    op.drop_table("tables")
