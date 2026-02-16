from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rop.api.main import app
from rop.infrastructure.db.repositories import menu_repo as menu_repo_module


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
