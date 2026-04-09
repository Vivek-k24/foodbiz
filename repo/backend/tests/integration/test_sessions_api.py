from __future__ import annotations


def test_session_creation_by_channel_rules(client) -> None:
    dine_in = client.post(
        "/v1/sessions",
        json={
            "restaurant_id": "rst_001",
            "location_id": "loc_001",
            "channel": "dine_in",
            "source_type": "qr",
            "table_id": "tbl_001",
        },
    )
    assert dine_in.status_code == 201
    assert dine_in.json()["channel"] == "dine_in"
    assert dine_in.json()["table_id"] == "tbl_001"

    pickup = client.post(
        "/v1/sessions",
        json={
            "restaurant_id": "rst_001",
            "location_id": "loc_002",
            "channel": "pickup",
            "source_type": "business_website",
        },
    )
    assert pickup.status_code == 201
    assert pickup.json()["table_id"] is None

    delivery = client.post(
        "/v1/sessions",
        json={
            "restaurant_id": "rst_001",
            "location_id": "loc_002",
            "channel": "delivery",
            "source_type": "business_website",
        },
    )
    assert delivery.status_code == 201
    assert delivery.json()["channel"] == "delivery"

    invalid_dine_in = client.post(
        "/v1/sessions",
        json={
            "restaurant_id": "rst_001",
            "location_id": "loc_001",
            "channel": "dine_in",
            "source_type": "qr",
        },
    )
    assert invalid_dine_in.status_code == 400
    assert invalid_dine_in.json()["error"]["code"] == "TABLE_REQUIRED"

    invalid_third_party = client.post(
        "/v1/sessions",
        json={
            "restaurant_id": "rst_001",
            "location_id": "loc_002",
            "channel": "third_party",
            "source_type": "uber_eats",
        },
    )
    assert invalid_third_party.status_code == 400
    assert invalid_third_party.json()["error"]["code"] == "EXTERNAL_REFERENCE_REQUIRED"


def test_session_patch_and_delete_behaviour(client) -> None:
    created = client.post(
        "/v1/sessions",
        json={
            "restaurant_id": "rst_001",
            "location_id": "loc_002",
            "channel": "pickup",
            "source_type": "business_website",
        },
    )
    session_id = created.json()["id"]

    patched = client.patch(
        f"/v1/sessions/{session_id}",
        json={"metadata": {"pickup_name": "Ada"}, "external_reference": "pickup-001"},
    )
    assert patched.status_code == 200
    assert patched.json()["metadata"] == {"pickup_name": "Ada"}
    assert patched.json()["external_reference"] == "pickup-001"

    deleted = client.delete(f"/v1/sessions/{session_id}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "closed"
