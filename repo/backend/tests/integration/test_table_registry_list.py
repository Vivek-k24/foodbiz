from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rop.api.main import app


def test_table_registry_list_updates_with_order_activity_and_close() -> None:
    table_id = f"tbl_reg_{uuid4().hex[:8]}"
    with TestClient(app) as client:
        open_response = client.post(f"/v1/restaurants/rst_001/tables/{table_id}/open")
        assert open_response.status_code == 200

        open_list_response = client.get("/v1/restaurants/rst_001/tables?status=OPEN&limit=50")
        assert open_list_response.status_code == 200
        open_rows = open_list_response.json()["tables"]
        opened_row = next((row for row in open_rows if row["tableId"] == table_id), None)
        assert opened_row is not None
        assert opened_row["status"] == "OPEN"
        assert opened_row["lastOrderAt"] is None

        place_response = client.post(
            f"/v1/restaurants/rst_001/tables/{table_id}/orders",
            json={"lines": [{"itemId": "itm_001", "quantity": 1}]},
        )
        assert place_response.status_code == 201
        order_id = place_response.json()["orderId"]

        open_list_with_order = client.get("/v1/restaurants/rst_001/tables?status=OPEN&limit=50")
        assert open_list_with_order.status_code == 200
        open_with_order_rows = open_list_with_order.json()["tables"]
        active_row = next((row for row in open_with_order_rows if row["tableId"] == table_id), None)
        assert active_row is not None
        assert active_row["lastOrderAt"] is not None
        assert active_row["counts"]["ordersTotal"] == 1

        accept_response = client.post(f"/v1/orders/{order_id}/accept")
        assert accept_response.status_code == 200
        ready_response = client.post(f"/v1/orders/{order_id}/ready")
        assert ready_response.status_code == 200
        close_response = client.post(f"/v1/restaurants/rst_001/tables/{table_id}/close")
        assert close_response.status_code == 200

        closed_list_response = client.get("/v1/restaurants/rst_001/tables?status=CLOSED&limit=50")
        assert closed_list_response.status_code == 200
        closed_rows = closed_list_response.json()["tables"]
        closed_row = next((row for row in closed_rows if row["tableId"] == table_id), None)
        assert closed_row is not None
        assert closed_row["status"] == "CLOSED"
        assert closed_row["counts"]["ready"] == 1


def test_table_registry_list_cursor_pagination() -> None:
    first_table_id = f"tbl_reg_{uuid4().hex[:8]}"
    second_table_id = f"tbl_reg_{uuid4().hex[:8]}"

    with TestClient(app) as client:
        assert (
            client.post(f"/v1/restaurants/rst_001/tables/{first_table_id}/open").status_code == 200
        )
        assert (
            client.post(f"/v1/restaurants/rst_001/tables/{second_table_id}/open").status_code == 200
        )

        first_page_response = client.get("/v1/restaurants/rst_001/tables?status=OPEN&limit=1")
        assert first_page_response.status_code == 200
        first_page = first_page_response.json()
        assert len(first_page["tables"]) == 1
        assert first_page["nextCursor"] is not None

        second_page_response = client.get(
            f"/v1/restaurants/rst_001/tables?status=OPEN&limit=1&cursor={first_page['nextCursor']}"
        )
        assert second_page_response.status_code == 200
        second_page = second_page_response.json()
        assert len(second_page["tables"]) == 1

        listed_ids = {first_page["tables"][0]["tableId"], second_page["tables"][0]["tableId"]}
        assert first_table_id in listed_ids
        assert second_table_id in listed_ids
