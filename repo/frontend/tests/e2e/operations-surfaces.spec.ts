import { expect, test } from "@playwright/test";

import {
  acceptedKitchenOrder,
  emptyTableOrdersResponse,
  locationsResponse,
  placedKitchenOrder,
  readyServiceOrder,
  tableRegistryResponse,
  tableSummaryResponse,
} from "../fixtures/foodbiz";
import { installNoopWebSocket } from "./support/browser";

test.beforeEach(async ({ page }) => {
  await installNoopWebSocket(page);
});

test("staff console keeps kitchen Accept and Ready out of the default workflow", async ({ page }) => {
  await page.route("**/v1/restaurants/rst_001/locations?is_active=true", async (route) => {
    await route.fulfill({ json: locationsResponse });
  });
  await page.route("**/v1/restaurants/rst_001/tables?status=ALL&limit=200", async (route) => {
    await route.fulfill({ json: tableRegistryResponse });
  });
  await page.route(/.*\/v1\/restaurants\/rst_001\/tables\/tbl_001\/orders.*/, async (route) => {
    await route.fulfill({ json: { ...emptyTableOrdersResponse, orders: [readyServiceOrder] } });
  });
  await page.route("**/v1/restaurants/rst_001/tables/tbl_001/summary", async (route) => {
    await route.fulfill({ json: tableSummaryResponse });
  });

  await page.goto("http://127.0.0.1:5174");

  await expect(page.getByRole("heading", { name: "Table 1" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Mark Served" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Accept" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Mark Ready" })).toHaveCount(0);
});

test("staff console can open a table session without exposing kitchen prep controls", async ({ page }) => {
  const summaryByTable: Record<string, typeof tableSummaryResponse> = {
    tbl_001: tableSummaryResponse,
    tbl_002: {
      ...tableSummaryResponse,
      tableId: "tbl_002",
      status: "CLOSED",
      openedAt: null,
      closedAt: "2026-04-08T11:00:00Z",
      totals: { amountCents: 0, currency: "USD" },
      counts: {
        ordersTotal: 0,
        placed: 0,
        accepted: 0,
        ready: 0,
        served: 0,
        settled: 0,
      },
      lastOrderAt: null,
    },
  };

  let registry = structuredClone(tableRegistryResponse);

  await page.route("**/v1/restaurants/rst_001/locations?is_active=true", async (route) => {
    await route.fulfill({ json: locationsResponse });
  });
  await page.route("**/v1/restaurants/rst_001/tables?status=ALL&limit=200", async (route) => {
    await route.fulfill({ json: registry });
  });
  await page.route(/.*\/v1\/restaurants\/rst_001\/tables\/(tbl_001|tbl_002)\/orders.*/, async (route) => {
    const url = route.request().url();
    const payload =
      url.includes("/tbl_001/") ? { ...emptyTableOrdersResponse, orders: [readyServiceOrder] } : emptyTableOrdersResponse;
    await route.fulfill({ json: payload });
  });
  await page.route(/.*\/v1\/restaurants\/rst_001\/tables\/(tbl_001|tbl_002)\/summary.*/, async (route) => {
    const url = route.request().url();
    const tableId = url.includes("/tbl_002/") ? "tbl_002" : "tbl_001";
    await route.fulfill({ json: summaryByTable[tableId] });
  });
  await page.route("**/v1/restaurants/rst_001/tables/tbl_002/open", async (route) => {
    registry = {
      ...registry,
      tables: registry.tables.map((table) =>
        table.tableId === "tbl_002"
          ? {
              ...table,
              status: "OPEN",
              openedAt: "2026-04-08T12:40:00Z",
              closedAt: null,
            }
          : table
      ),
    };
    summaryByTable.tbl_002 = {
      ...summaryByTable.tbl_002,
      status: "OPEN",
      openedAt: "2026-04-08T12:40:00Z",
      closedAt: null,
    };
    await route.fulfill({ status: 200, json: {} });
  });

  await page.goto("http://127.0.0.1:5174");

  await page.getByRole("button", { name: /Table 2/ }).first().click();
  await expect(page.getByRole("button", { name: "Open Session" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Accept" })).toHaveCount(0);
  await page.getByRole("button", { name: "Open Session" }).click();

  await expect(page.getByText("Opened session for Table 2.")).toBeVisible();
});

test("kitchen display exposes Accept and Mark Ready for prep progression", async ({ page }) => {
  const ordersByStatus: Record<string, typeof placedKitchenOrder[]> = {
    PLACED: [placedKitchenOrder],
    ACCEPTED: [acceptedKitchenOrder],
    READY: [],
  };

  await page.route(/.*\/v1\/restaurants\/rst_001\/kitchen\/orders\?status=.*/, async (route) => {
    const url = new URL(route.request().url());
    const status = url.searchParams.get("status") ?? "PLACED";
    await route.fulfill({ json: { orders: ordersByStatus[status] ?? [], nextCursor: null } });
  });
  await page.route("**/v1/orders/ord_kitchen_placed_001/accept", async (route) => {
    ordersByStatus.PLACED = [];
    ordersByStatus.ACCEPTED = [acceptedKitchenOrder, { ...placedKitchenOrder, status: "ACCEPTED" }];
    await route.fulfill({
      json: { ...placedKitchenOrder, status: "ACCEPTED", updatedAt: "2026-04-08T12:31:00Z" },
    });
  });
  await page.route("**/v1/orders/ord_kitchen_accepted_001/ready", async (route) => {
    ordersByStatus.ACCEPTED = [];
    ordersByStatus.READY = [{ ...acceptedKitchenOrder, status: "READY" }];
    await route.fulfill({
      json: { ...acceptedKitchenOrder, status: "READY", updatedAt: "2026-04-08T12:32:00Z" },
    });
  });

  await page.goto("http://127.0.0.1:5175");

  await expect(page.getByRole("heading", { name: "Kitchen Flow Board" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Accept" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Mark Ready" })).toBeVisible();
});
