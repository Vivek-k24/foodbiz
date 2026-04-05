"""order line modifiers json

Revision ID: 202604040901
Revises: 202604040900
Create Date: 2026-04-04 09:01:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202604040901"
down_revision = "202604040900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "order_lines",
        sa.Column(
            "modifiers_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("order_lines", "modifiers_json")
