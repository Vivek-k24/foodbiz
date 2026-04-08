import { expect, test } from "@playwright/test";

import {
  createdDeliveryOrder,
  createdDineInOrder,
  createdPickupOrder,
  emptyTableOrdersResponse,
  locationsResponse,
  menuResponse,
  restaurant,
} from "../fixtures/foodbiz";
import { installNoopWebSocket } from "./support/browser";

test.beforeEach(async ({ page }) => {
  await installNoopWebSocket(page);
});

test("restaurant website routes Order Pickup into the pickup ordering flow", async ({ page }) => {
  let latestOrder = createdPickupOrder;

  await page.route("**/v1/restaurants", async (route) => {
    await route.fulfill({ json: { restaurants: [restaurant] } });
  });
  await page.route("**/v1/restaurants/rst_001/menu", async (route) => {
    await route.fulfill({ json: menuResponse });
  });
  await page.route("**/v1/restaurants/rst_001/locations?is_active=true", async (route) => {
    await route.fulfill({ json: locationsResponse });
  });
  await page.route("**/v1/orders", async (route) => {
    const payload = route.request().postDataJSON() as { source: string };
    expect(payload.source).toBe("ONLINE_PICKUP");
    latestOrder =
      payload.source === "ONLINE_DELIVERY" ? createdDeliveryOrder : createdPickupOrder;
    await route.fulfill({ status: 201, json: latestOrder });
  });
  await page.route(/.*\/v1\/restaurants\/rst_001\/tables\/.*\/orders.*/, async (route) => {
    await route.fulfill({ json: emptyTableOrdersResponse });
  });

  await page.goto("http://127.0.0.1:5176");
  await expect(page.getByRole("heading", { name: "Bella Vista Kitchen" })).toBeVisible();
  await page.getByRole("link", { name: "Order Pickup" }).click();

  await expect(page).toHaveURL(/mode=pickup/);
  await expect(page.getByRole("heading", { name: "FoodBiz Ordering" })).toBeVisible();
  await expect(page.locator(".contextCard").getByRole("heading", { name: "Pickup Counter" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Margherita Pizza" })).toBeVisible();

  await page.getByRole("button", { name: "Add to Cart" }).first().click();
  await page.getByRole("button", { name: "Place Pickup Order" }).click();

  await expect(page.getByText("Created order ord_pickup_001 for Pickup Counter")).toBeVisible();
  await expect(page.getByText("ord_pickup_001", { exact: true })).toBeVisible();
});

test("restaurant website routes Order Delivery into the delivery ordering flow", async ({ page }) => {
  await page.route("**/v1/orders", async (route) => {
    const payload = route.request().postDataJSON() as { source: string };
    expect(payload.source).toBe("ONLINE_DELIVERY");
    await route.fulfill({ status: 201, json: createdDeliveryOrder });
  });
  await page.route("**/v1/restaurants", async (route) => {
    await route.fulfill({ json: { restaurants: [restaurant] } });
  });
  await page.route("**/v1/restaurants/rst_001/menu", async (route) => {
    await route.fulfill({ json: menuResponse });
  });
  await page.route("**/v1/restaurants/rst_001/locations?is_active=true", async (route) => {
    await route.fulfill({ json: locationsResponse });
  });

  await page.goto("http://127.0.0.1:5176");
  await page.getByRole("link", { name: "Order Delivery" }).click();

  await expect(page).toHaveURL(/mode=delivery/);
  await expect(page.getByRole("heading", { name: "FoodBiz Ordering" })).toBeVisible();
  await expect(page.locator(".contextCard").getByRole("heading", { name: "Delivery Dispatch" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Place Delivery Order" })).toBeVisible();

  await page.getByRole("button", { name: "Add to Cart" }).first().click();
  await page.getByRole("button", { name: "Place Delivery Order" }).click();

  await expect(page.getByText("Created order ord_delivery_001 for Delivery Dispatch")).toBeVisible();
  await expect(page.getByText("ord_delivery_001", { exact: true })).toBeVisible();
});

test("dine-in ordering honors an open table context", async ({ page }) => {
  let tableOrders = { ...emptyTableOrdersResponse, orders: [createdDineInOrder] };

  await page.route("**/v1/restaurants/rst_001/menu", async (route) => {
    await route.fulfill({ json: menuResponse });
  });
  await page.route("**/v1/restaurants/rst_001/locations?is_active=true", async (route) => {
    await route.fulfill({ json: locationsResponse });
  });
  await page.route("**/v1/orders", async (route) => {
    const payload = route.request().postDataJSON() as { source: string; sessionId: string | null };
    expect(payload.source).toBe("WEB_DINE_IN");
    expect(payload.sessionId).toBe("ses_001");
    tableOrders = { ...emptyTableOrdersResponse, orders: [createdDineInOrder] };
    await route.fulfill({ status: 201, json: createdDineInOrder });
  });
  await page.route(/.*\/v1\/restaurants\/rst_001\/tables\/tbl_001\/orders.*/, async (route) => {
    await route.fulfill({ json: tableOrders });
  });

  await page.goto("http://127.0.0.1:5173/?mode=dine-in&tableId=tbl_001");

  await expect(page.locator(".contextCard").getByRole("heading", { name: "Table 1" })).toBeVisible();
  await expect(page.getByText("Ready to order.")).toBeVisible();

  await page.getByRole("button", { name: "Add to Cart" }).first().click();
  await page.getByRole("button", { name: "Place Dine-In Order" }).click();

  await expect(page.getByText("Created order ord_dine_in_001 for Table 1")).toBeVisible();
  await expect(page.getByText("ord_dine_in_001", { exact: true })).toBeVisible();
});
