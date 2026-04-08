from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rop.api.main import app


def test_foundation_endpoints_expose_seeded_foundation_and_session_order_flow() -> None:
    location_id = f"loc_tbl_{uuid4().hex[:6]}"
    legacy_table_id = location_id.removeprefix("loc_")

    with TestClient(app) as client:
        restaurants_response = client.get("/v1/restaurants")
        assert restaurants_response.status_code == 200
        restaurants = restaurants_response.json()["restaurants"]
        assert any(restaurant["restaurantId"] == "rst_001" for restaurant in restaurants)

        roles_response = client.get("/v1/roles")
        assert roles_response.status_code == 200
        roles = roles_response.json()["roles"]
        assert len(roles) == 27
        assert any(role["code"] == "SERVER" for role in roles)

        inventory_response = client.get("/v1/inventory/status")
        assert inventory_response.status_code == 200
        inventory_payload = inventory_response.json()
        assert inventory_payload["implemented"] is False
        assert inventory_payload["status"] == "NOT_IMPLEMENTED"

        open_table_response = client.post(f"/v1/restaurants/rst_001/tables/{legacy_table_id}/open")
        assert open_table_response.status_code == 200

        locations_response = client.get(
            "/v1/restaurants/rst_001/locations?type=TABLE&session_status=OPEN"
        )
        assert locations_response.status_code == 200
        locations = locations_response.json()["locations"]
        opened_location = next(
            location for location in locations if location["locationId"] == location_id
        )
        assert opened_location["type"] == "TABLE"
        assert opened_location["sessionStatus"] == "OPEN"
        assert opened_location["activeSessionId"] is not None

        sessions_response = client.get(
            f"/v1/restaurants/rst_001/sessions?location_id={location_id}&status=OPEN"
        )
        assert sessions_response.status_code == 200
        session_payload = sessions_response.json()["sessions"]
        assert len(session_payload) == 1
        session_id = session_payload[0]["sessionId"]

        create_order_response = client.post(
            "/v1/orders",
            json={
                "restaurantId": "rst_001",
                "locationId": location_id,
                "sessionId": session_id,
                "tableId": legacy_table_id,
                "source": "STAFF_CONSOLE",
                "lines": [{"itemId": "itm_010", "quantity": 1}],
            },
        )
        assert create_order_response.status_code == 201
        order_payload = create_order_response.json()
        assert order_payload["locationId"] == location_id
        assert order_payload["sessionId"] == session_id
        assert order_payload["source"] == "STAFF_CONSOLE"

        order_events_response = client.get(
            f"/v1/order-events?restaurantId=rst_001&orderId={order_payload['orderId']}"
        )
        assert order_events_response.status_code == 200
        order_events = order_events_response.json()
        assert len(order_events) == 1
        assert order_events[0]["eventType"] == "ORDER_PLACED"
        assert order_events[0]["locationId"] == location_id
        assert order_events[0]["sessionId"] == session_id

        close_session_response = client.post(f"/v1/sessions/{session_id}/close")
        assert close_session_response.status_code == 200
        assert close_session_response.json()["status"] == "CLOSED"
