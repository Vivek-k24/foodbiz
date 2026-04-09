from __future__ import annotations

import os
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url


def _connect_args(database_url: str, connect_timeout: int) -> dict[str, object]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {"connect_timeout": connect_timeout}


@lru_cache(maxsize=8)
def _build_engine(database_url: str, connect_timeout: int) -> Engine:
    return create_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
        connect_args=_connect_args(database_url, connect_timeout),
    )


def get_engine(timeout_seconds: float = 1.0) -> Engine:
    connect_timeout = max(1, int(timeout_seconds))
    return _build_engine(_database_url(), connect_timeout)


@lru_cache(maxsize=8)
def _build_session_factory(database_url: str, connect_timeout: int) -> sessionmaker[Session]:
    engine = _build_engine(database_url, connect_timeout)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_session_factory(timeout_seconds: float = 1.0) -> sessionmaker[Session]:
    connect_timeout = max(1, int(timeout_seconds))
    return _build_session_factory(_database_url(), connect_timeout)


@contextmanager
def session_scope(timeout_seconds: float = 1.0):
    session = get_session_factory(timeout_seconds)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ping_database(timeout_seconds: float = 1.0) -> bool:
    try:
        with get_engine(timeout_seconds).connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
