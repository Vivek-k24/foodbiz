from __future__ import annotations


def test_table_open_close_session_and_kitchen_queue_shape(client) -> None:
    opened = client.post(
        "/v1/tables/tbl_001/open-session",
        json={"source_type": "waiter_entered"},
    )
    assert opened.status_code == 201
    session_id = opened.json()["id"]

    created_order = client.post(
        "/v1/orders",
        json={
            "restaurant_id": "rst_001",
            "session_id": session_id,
            "lines": [{"menu_item_id": "itm_002", "quantity": 1}],
            "notes": "fire fast",
        },
    )
    assert created_order.status_code == 201
    order_id = created_order.json()["id"]

    queue = client.get("/v1/restaurants/rst_001/kitchen/orders")
    assert queue.status_code == 200
    queue_order = next(order for order in queue.json()["orders"] if order["id"] == order_id)
    assert queue_order["channel"] == "dine_in"
    assert queue_order["source_type"] == "waiter_entered"
    assert queue_order["table_label"] == "Table 1"
    assert queue_order["status"] == "pending"
    assert queue_order["notes"] == "fire fast"
    assert isinstance(queue_order["age_seconds"], int)

    closed = client.post("/v1/tables/tbl_001/close-session")
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"


def test_invalid_workflow_transition_is_rejected(client) -> None:
    session_response = client.post(
        "/v1/sessions",
        json={
            "restaurant_id": "rst_001",
            "location_id": "loc_002",
            "channel": "pickup",
            "source_type": "business_website",
        },
    )
    session_id = session_response.json()["id"]
    created_order = client.post(
        "/v1/orders",
        json={
            "restaurant_id": "rst_001",
            "session_id": session_id,
            "lines": [{"menu_item_id": "itm_001", "quantity": 1}],
        },
    )
    order_id = created_order.json()["id"]

    invalid_ready = client.post(f"/v1/orders/{order_id}/ready")
    assert invalid_ready.status_code == 409
    assert invalid_ready.json()["error"]["code"] == "INVALID_ORDER_TRANSITION"
