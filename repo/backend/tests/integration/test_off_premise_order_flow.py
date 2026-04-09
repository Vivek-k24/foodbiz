from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rop.api.main import app


def test_pickup_and_delivery_orders_flow_through_hidden_sessions_and_status_events() -> None:
    with TestClient(app) as client:
        created_orders: list[tuple[str, str, str, str]] = []
        for location_id, source in [
            ("loc_online_pickup", "ONLINE_PICKUP"),
            ("loc_online_delivery", "ONLINE_DELIVERY"),
        ]:
            create_response = client.post(
                "/v1/orders",
                json={
                    "restaurantId": "rst_001",
                    "locationId": location_id,
                    "source": source,
                    "lines": [{"itemId": "itm_010", "quantity": 1}],
                },
            )
            assert create_response.status_code == 201
            order_payload = create_response.json()
            assert order_payload["locationId"] == location_id
            assert order_payload["source"] == source
            assert order_payload["tableId"] is None
            assert order_payload["sessionId"] is not None
            created_orders.append(
                (
                    order_payload["orderId"],
                    location_id,
                    source,
                    order_payload["sessionId"],
                )
            )

        for order_id, location_id, source, session_id in created_orders:
            location_orders_response = client.get(
                f"/v1/restaurants/rst_001/locations/{location_id}/orders?status=ALL&limit=20"
            )
            assert location_orders_response.status_code == 200
            location_orders = location_orders_response.json()["orders"]
            assert any(order["orderId"] == order_id for order in location_orders)

            kitchen_response = client.get(
                "/v1/restaurants/rst_001/kitchen/orders?status=PLACED&limit=100"
            )
            assert kitchen_response.status_code == 200
            kitchen_orders = kitchen_response.json()["orders"]
            assert any(order["orderId"] == order_id for order in kitchen_orders)

            assert client.post(f"/v1/orders/{order_id}/accept").status_code == 200
            assert client.post(f"/v1/orders/{order_id}/ready").status_code == 200
            assert client.post(f"/v1/orders/{order_id}/served").status_code == 200
            settled_response = client.post(f"/v1/orders/{order_id}/settled")
            assert settled_response.status_code == 200
            settled_payload = settled_response.json()
            assert settled_payload["status"] == "SETTLED"
            assert settled_payload["source"] == source

            order_events_response = client.get(
                f"/v1/order-events?restaurantId=rst_001&orderId={order_id}"
            )
            assert order_events_response.status_code == 200
            event_types = [event["eventType"] for event in order_events_response.json()]
            assert event_types == [
                "ORDER_PLACED",
                "ORDER_ACCEPTED",
                "ORDER_READY",
                "ORDER_SERVED",
                "ORDER_SETTLED",
            ]

            session_response = client.get(
                f"/v1/restaurants/rst_001/sessions?location_id={location_id}&status=CLOSED"
            )
            assert session_response.status_code == 200
            closed_sessions = session_response.json()["sessions"]
            assert any(session["sessionId"] == session_id for session in closed_sessions)
