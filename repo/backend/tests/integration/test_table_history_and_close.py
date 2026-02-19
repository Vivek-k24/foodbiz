from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rop.api.main import app


def test_table_orders_and_close_workflow() -> None:
    table_id = f"tbl_hist_{uuid4().hex[:8]}"
    with TestClient(app) as client:
        open_response = client.post(f"/v1/restaurants/rst_001/tables/{table_id}/open")
        assert open_response.status_code == 200
        assert open_response.json()["status"] == "OPEN"

        place_response = client.post(
            f"/v1/restaurants/rst_001/tables/{table_id}/orders",
            json={"lines": [{"itemId": "itm_001", "quantity": 1}]},
        )
        assert place_response.status_code == 201
        order_id_one = place_response.json()["orderId"]

        second_place_response = client.post(
            f"/v1/restaurants/rst_001/tables/{table_id}/orders",
            json={"lines": [{"itemId": "itm_001", "quantity": 1}]},
        )
        assert second_place_response.status_code == 201
        order_id_two = second_place_response.json()["orderId"]

        list_response = client.get(
            f"/v1/restaurants/rst_001/tables/{table_id}/orders?status=ALL&limit=1"
        )
        assert list_response.status_code == 200
        listed = list_response.json()
        assert len(listed["orders"]) == 1
        assert listed["nextCursor"] is not None

        paged_response = client.get(
            f"/v1/restaurants/rst_001/tables/{table_id}/orders?status=ALL&limit=1&cursor={listed['nextCursor']}"
        )
        assert paged_response.status_code == 200
        paged = paged_response.json()
        assert len(paged["orders"]) == 1

        listed_ids = {listed["orders"][0]["orderId"], paged["orders"][0]["orderId"]}
        assert order_id_one in listed_ids
        assert order_id_two in listed_ids

        blocked_close = client.post(f"/v1/restaurants/rst_001/tables/{table_id}/close")
        assert blocked_close.status_code == 409
        assert blocked_close.json()["error"]["code"] == "TABLE_CLOSE_BLOCKED"

        for order_id in [order_id_one, order_id_two]:
            accept_response = client.post(f"/v1/orders/{order_id}/accept")
            assert accept_response.status_code == 200
            ready_response = client.post(f"/v1/orders/{order_id}/ready")
            assert ready_response.status_code == 200

        close_response = client.post(f"/v1/restaurants/rst_001/tables/{table_id}/close")
        assert close_response.status_code == 200
        assert close_response.json()["status"] == "CLOSED"

        summary_response = client.get(f"/v1/restaurants/rst_001/tables/{table_id}/summary")
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["tableId"] == table_id
        assert summary["status"] == "CLOSED"
        assert summary["totals"]["amountCents"] == 2900
        assert summary["counts"]["ordersTotal"] == 2
        assert summary["counts"]["placed"] == 0
        assert summary["counts"]["accepted"] == 0
        assert summary["counts"]["ready"] == 2
        assert summary["lastOrderAt"] is not None
