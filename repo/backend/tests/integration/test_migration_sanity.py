from __future__ import annotations

from sqlalchemy import inspect

from rop.infrastructure.db.session import get_engine


def test_schema_contains_channel_aware_reset_tables() -> None:
    inspector = inspect(get_engine())
    table_names = set(inspector.get_table_names())
    assert {
        "restaurants",
        "locations",
        "tables",
        "categories",
        "menu_items",
        "sessions",
        "orders",
        "order_lines",
        "order_status_history",
    }.issubset(table_names)
