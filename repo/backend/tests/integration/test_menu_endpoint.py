from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rop.api.main import app
from rop.infrastructure.cache import redis_client
from rop.infrastructure.db import session as db_session
from rop.infrastructure.db.repositories import menu_repo as menu_repo_module

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module", autouse=True)
def setup_integration_environment() -> Iterator[None]:
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


def test_menu_endpoint_uses_cache_after_first_read(monkeypatch) -> None:
    client = TestClient(app)

    first_response = client.get("/v1/restaurants/rst_001/menu")
    assert first_response.status_code == 200
    assert first_response.headers["etag"] == '"menu-v1"'

    payload = first_response.json()
    assert payload["restaurantId"] == "rst_001"
    assert payload["menuVersion"] == 1
    assert len(payload["items"]) >= 3

    def _raise_if_called(*args, **kwargs):
        raise RuntimeError("database should not be called on warm cache")

    monkeypatch.setattr(
        menu_repo_module.SqlAlchemyMenuRepository,
        "get_menu_by_restaurant_id",
        _raise_if_called,
    )

    second_response = client.get("/v1/restaurants/rst_001/menu")
    assert second_response.status_code == 200
    assert second_response.json()["menuVersion"] == 1

    not_modified_response = client.get(
        "/v1/restaurants/rst_001/menu",
        headers={"If-None-Match": '"menu-v1"'},
    )
    assert not_modified_response.status_code == 304
