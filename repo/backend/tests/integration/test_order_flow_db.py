from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rop.api.main import app


def test_order_flow_is_persisted() -> None:
    with TestClient(app) as client:
        place_response = client.post(
            "/v1/restaurants/rst_001/tables/tbl_001/orders",
            json={"lines": [{"itemId": "itm_001", "quantity": 1}]},
        )
        assert place_response.status_code == 201
        order_id = place_response.json()["orderId"]

        invalid_ready_response = client.post(f"/v1/orders/{order_id}/ready")
        assert invalid_ready_response.status_code == 409
        assert invalid_ready_response.json()["error"]["code"] == "INVALID_ORDER_TRANSITION"

        accept_response = client.post(f"/v1/orders/{order_id}/accept")
        assert accept_response.status_code == 200
        assert accept_response.json()["status"] == "ACCEPTED"

        accept_retry_response = client.post(f"/v1/orders/{order_id}/accept")
        assert accept_retry_response.status_code == 200
        assert accept_retry_response.json()["status"] == "ACCEPTED"

        ready_response = client.post(f"/v1/orders/{order_id}/ready")
        assert ready_response.status_code == 200
        assert ready_response.json()["status"] == "READY"

        invalid_settled_response = client.post(f"/v1/orders/{order_id}/settled")
        assert invalid_settled_response.status_code == 409
        assert invalid_settled_response.json()["error"]["code"] == "INVALID_ORDER_TRANSITION"

        ready_retry_response = client.post(f"/v1/orders/{order_id}/ready")
        assert ready_retry_response.status_code == 200
        assert ready_retry_response.json()["status"] == "READY"

        served_response = client.post(f"/v1/orders/{order_id}/served")
        assert served_response.status_code == 200
        assert served_response.json()["status"] == "SERVED"

        served_retry_response = client.post(f"/v1/orders/{order_id}/served")
        assert served_retry_response.status_code == 200
        assert served_retry_response.json()["status"] == "SERVED"

        settled_response = client.post(f"/v1/orders/{order_id}/settled")
        assert settled_response.status_code == 200
        assert settled_response.json()["status"] == "SETTLED"

        settled_retry_response = client.post(f"/v1/orders/{order_id}/settled")
        assert settled_retry_response.status_code == 200
        assert settled_retry_response.json()["status"] == "SETTLED"

        get_response = client.get(f"/v1/orders/{order_id}")
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "SETTLED"
