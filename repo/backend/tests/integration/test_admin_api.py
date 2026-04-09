from __future__ import annotations


def test_admin_patch_and_soft_delete_flows(client) -> None:
    created_location = client.post(
        "/v1/admin/locations",
        json={
            "restaurant_id": "rst_001",
            "name": "Delivery Annex",
            "location_type": "pickup_hub",
            "supports_dine_in": False,
            "supports_pickup": True,
            "supports_delivery": True,
        },
    )
    assert created_location.status_code == 201
    location_id = created_location.json()["id"]

    patched_location = client.patch(
        f"/v1/admin/locations/{location_id}",
        json={"name": "Updated Delivery Annex", "supports_pickup": False},
    )
    assert patched_location.status_code == 200
    assert patched_location.json()["name"] == "Updated Delivery Annex"
    assert patched_location.json()["supports_pickup"] is False

    created_category = client.post(
        "/v1/admin/categories",
        json={"restaurant_id": "rst_001", "name": "Desserts", "sort_order": 3},
    )
    assert created_category.status_code == 201
    category_id = created_category.json()["id"]

    patched_category = client.patch(
        f"/v1/admin/categories/{category_id}",
        json={"name": "After Dinner", "sort_order": 9},
    )
    assert patched_category.status_code == 200
    assert patched_category.json()["name"] == "After Dinner"
    assert patched_category.json()["sort_order"] == 9

    created_item = client.post(
        "/v1/admin/menu-items",
        json={
            "restaurant_id": "rst_001",
            "category_id": category_id,
            "name": "Chocolate Tart",
            "price": "8.50",
            "currency": "USD",
        },
    )
    assert created_item.status_code == 201
    item_id = created_item.json()["id"]

    patched_item = client.patch(
        f"/v1/admin/menu-items/{item_id}",
        json={"price": "9.25", "is_available": False},
    )
    assert patched_item.status_code == 200
    assert patched_item.json()["price"] == 9.25
    assert patched_item.json()["is_available"] is False

    deleted_category = client.delete(f"/v1/admin/categories/{category_id}")
    assert deleted_category.status_code == 200
    assert deleted_category.json()["deleted_at"] is not None

    deleted_location = client.delete(f"/v1/admin/locations/{location_id}")
    assert deleted_location.status_code == 200
    assert deleted_location.json()["deleted_at"] is not None
