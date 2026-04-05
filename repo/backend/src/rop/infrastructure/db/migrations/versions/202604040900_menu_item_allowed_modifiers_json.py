"""menu item allowed modifiers json

Revision ID: 202604040900
Revises: 202602181200
Create Date: 2026-04-04 09:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "202604040900"
down_revision = "202602181200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "menu_items",
        sa.Column(
            "allowed_modifiers_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("menu_items", "allowed_modifiers_json")
