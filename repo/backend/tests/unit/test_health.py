from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import rop.api.routes.health as health_route
from rop.api.main import app


def test_live_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_health_endpoint_healthy_with_mocks(monkeypatch) -> None:
    monkeypatch.setattr(health_route, "ping_database", lambda timeout_seconds=1.0: True)
    monkeypatch.setattr(health_route, "ping_redis", lambda timeout_seconds=1.0: True)

    client = TestClient(app)
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
