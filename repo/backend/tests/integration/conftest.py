from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rop.api.main import app
from rop.infrastructure.cache import redis_client
from rop.infrastructure.db import session as db_session
from rop.tools import seed

BACKEND_DIR = Path(__file__).resolve().parents[2]
RESET_TABLES = [
    "order_status_history",
    "order_lines",
    "orders",
    "sessions",
    "tables",
    "menu_items",
    "categories",
    "locations",
    "restaurants",
]


@pytest.fixture(scope="session", autouse=True)
def integration_environment() -> Iterator[None]:
    database_url = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/rop"
    redis_url = "redis://127.0.0.1:6379/0"

    os.environ["APP_ENV"] = "test"
    os.environ["DATABASE_URL"] = database_url
    os.environ["REDIS_URL"] = redis_url
    os.environ.setdefault("OTEL_SERVICE_NAME", "foodbiz-backend-test")
    os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "")

    db_session._build_engine.cache_clear()
    db_session._build_session_factory.cache_clear()
    redis_client._build_client.cache_clear()

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{BACKEND_DIR / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(
        os.pathsep
    )

    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        check=True,
    )
    seed.main()

    redis = redis_client.get_redis_client()
    redis.flushdb()
    yield
    redis.flushdb()


def _reset_database() -> None:
    truncate_sql = "TRUNCATE TABLE " + ", ".join(RESET_TABLES) + " CASCADE"
    with db_session.get_engine().begin() as connection:
        connection.execute(text(truncate_sql))


@pytest.fixture(autouse=True)
def reset_state() -> Iterator[None]:
    _reset_database()
    seed.main()
    redis = redis_client.get_redis_client()
    redis.flushdb()
    yield
    redis.flushdb()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
