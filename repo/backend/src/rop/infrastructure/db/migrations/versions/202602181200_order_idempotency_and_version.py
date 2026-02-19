"""order idempotency and version

Revision ID: 202602181200
Revises: 202602161000
Create Date: 2026-02-18 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "202602181200"
down_revision = "202602161000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "orders",
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("idempotency_hash", sa.String(length=64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_orders_restaurant_table_idempotency_key",
        "orders",
        ["restaurant_id", "table_id", "idempotency_key"],
    )
    op.create_index(
        "ix_orders_restaurant_status_created_at",
        "orders",
        ["restaurant_id", "status", "created_at"],
        unique=False,
    )
    op.alter_column("orders", "version", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_orders_restaurant_status_created_at", table_name="orders")
    op.drop_constraint("uq_orders_restaurant_table_idempotency_key", "orders", type_="unique")
    op.drop_column("orders", "idempotency_hash")
    op.drop_column("orders", "idempotency_key")
    op.drop_column("orders", "version")
