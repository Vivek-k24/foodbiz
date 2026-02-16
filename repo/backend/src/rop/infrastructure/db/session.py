from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url


@lru_cache(maxsize=8)
def _build_engine(database_url: str, connect_timeout: int) -> Engine:
    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": connect_timeout},
    )


def get_engine(timeout_seconds: float = 1.0) -> Engine:
    connect_timeout = max(1, int(timeout_seconds))
    return _build_engine(_database_url(), connect_timeout)


def ping_database(timeout_seconds: float = 1.0) -> bool:
    try:
        with get_engine(timeout_seconds).connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
