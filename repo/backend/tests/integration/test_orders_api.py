from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rop.infrastructure.db.models import OrderModel
from rop.infrastructure.db.session import get_engine


def _create_pickup_session(client) -> str:
    response = client.post(
        "/v1/sessions",
        json={
            "restaurant_id": "rst_001",
            "location_id": "loc_002",
            "channel": "pickup",
            "source_type": "business_website",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_order_creation_is_idempotent(client) -> None:
    session_id = _create_pickup_session(client)

    first = client.post(
        "/v1/orders",
        headers={"Idempotency-Key": " idem-001 "},
        json={
            "restaurant_id": "rst_001",
            "session_id": session_id,
            "lines": [{"menu_item_id": "itm_001", "quantity": 1}],
        },
    )
    second = client.post(
        "/v1/orders",
        headers={"Idempotency-Key": "idem-001"},
        json={
            "restaurant_id": "rst_001",
            "session_id": session_id,
            "lines": [{"menu_item_id": "itm_001", "quantity": 1}],
        },
    )

    assert first.status_code == 201
    assert second.status_code == 200 or second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    with Session(get_engine()) as session:
        count = session.scalar(
            select(func.count())
            .select_from(OrderModel)
            .where(
                OrderModel.restaurant_id == "rst_001",
                OrderModel.idempotency_key == "idem-001",
            )
        )
    assert count == 1


def test_closed_session_rejects_new_order(client) -> None:
    session_id = _create_pickup_session(client)
    close_response = client.delete(f"/v1/sessions/{session_id}")
    assert close_response.status_code == 200

    order_response = client.post(
        "/v1/orders",
        json={
            "restaurant_id": "rst_001",
            "session_id": session_id,
            "lines": [{"menu_item_id": "itm_001", "quantity": 1}],
        },
    )
    assert order_response.status_code == 409
    assert order_response.json()["error"]["code"] == "SESSION_CLOSED"


def test_invalid_channel_table_combinations_are_rejected(client) -> None:
    session_id = _create_pickup_session(client)
    order_response = client.post(
        "/v1/orders",
        json={
            "restaurant_id": "rst_001",
            "session_id": session_id,
            "table_id": "tbl_001",
            "lines": [{"menu_item_id": "itm_001", "quantity": 1}],
        },
    )
    assert order_response.status_code == 400
    assert order_response.json()["error"]["code"] == "TABLE_SESSION_MISMATCH"


def test_order_patch_and_delete_rules(client) -> None:
    session_id = _create_pickup_session(client)
    created = client.post(
        "/v1/orders",
        json={
            "restaurant_id": "rst_001",
            "session_id": session_id,
            "lines": [{"menu_item_id": "itm_002", "quantity": 1}],
        },
    )
    assert created.status_code == 201
    order_id = created.json()["id"]

    patched = client.patch(f"/v1/orders/{order_id}", json={"notes": "extra napkins"})
    assert patched.status_code == 200
    assert patched.json()["notes"] == "extra napkins"

    deleted = client.delete(f"/v1/orders/{order_id}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "canceled"
    assert deleted.json()["deleted_at"] is not None


def test_unsafe_order_delete_is_rejected_after_kitchen_progress(client) -> None:
    session_id = _create_pickup_session(client)
    created = client.post(
        "/v1/orders",
        json={
            "restaurant_id": "rst_001",
            "session_id": session_id,
            "lines": [{"menu_item_id": "itm_003", "quantity": 1}],
        },
    )
    order_id = created.json()["id"]

    accepted = client.post(f"/v1/orders/{order_id}/accept")
    assert accepted.status_code == 200

    deleted = client.delete(f"/v1/orders/{order_id}")
    assert deleted.status_code == 409
    assert deleted.json()["error"]["code"] == "ORDER_DELETE_NOT_ALLOWED"
