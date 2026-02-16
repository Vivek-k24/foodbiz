from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Iterator

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rop.infrastructure.cache import redis_client
from rop.infrastructure.db import session as db_session

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session", autouse=True)
def integration_environment() -> Iterator[None]:
    database_url = "postgresql+psycopg://postgres:postgres@localhost:5432/rop"
    redis_url = "redis://localhost:6379/0"

    os.environ["DATABASE_URL"] = database_url
    os.environ["REDIS_URL"] = redis_url
    os.environ.setdefault("OTEL_SERVICE_NAME", "rop-backend-test")
    os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "")

    db_session._build_engine.cache_clear()
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
    subprocess.run(
        [sys.executable, "-m", "rop.tools.seed"],
        cwd=BACKEND_DIR,
        env=env,
        check=True,
    )

    redis = redis_client.get_redis_client()
    redis.flushdb()
    yield
    redis.flushdb()


@pytest.fixture(autouse=True)
def clear_redis() -> Iterator[None]:
    redis = redis_client.get_redis_client()
    redis.flushdb()
    yield
    redis.flushdb()
