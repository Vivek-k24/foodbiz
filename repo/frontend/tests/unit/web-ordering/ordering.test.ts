import { describe, expect, it } from "vitest";

import {
  buildMenuSections,
  buildUrlForState,
  locationIdFromTableId,
  normalizeTableId,
  orderSourceForMode,
  readUrlStateFromHref,
  resolveActiveContext,
} from "../../../apps/web-ordering/src/lib/ordering";
import { locationsResponse, menuResponse } from "../../fixtures/foodbiz";

describe("web ordering URL and context helpers", () => {
  it("parses pickup and delivery URL state", () => {
    expect(readUrlStateFromHref("http://127.0.0.1:5173/?mode=pickup")).toEqual({
      mode: "ONLINE_PICKUP",
      tableId: null,
      locationId: null,
    });

    expect(
      readUrlStateFromHref(
        "http://127.0.0.1:5173/?mode=delivery&tableId=tbl_001&locationId=loc_tbl_001"
      )
    ).toEqual({
      mode: "ONLINE_DELIVERY",
      tableId: "tbl_001",
      locationId: "loc_tbl_001",
    });
  });

  it("normalizes table ids and location ids consistently", () => {
    expect(normalizeTableId("loc_tbl_001")).toBe("tbl_001");
    expect(normalizeTableId("tbl_001")).toBe("tbl_001");
    expect(locationIdFromTableId("tbl_001")).toBe("loc_tbl_001");
    expect(locationIdFromTableId("loc_tbl_001")).toBe("loc_tbl_001");
  });

  it("keeps invalid dine-in intent blocked instead of silently falling back to pickup", () => {
    const context = resolveActiveContext(
      { mode: "DINE_IN", tableId: "tbl_999", locationId: "loc_tbl_999" },
      locationsResponse.locations
    );

    expect(context.mode).toBe("DINE_IN");
    expect(context.orderable).toBe(false);
    expect(context.orderableMessage).toContain("missing or invalid");
  });

  it("resolves an open table context for dine-in ordering", () => {
    const context = resolveActiveContext(
      { mode: "DINE_IN", tableId: "tbl_001", locationId: "loc_tbl_001" },
      locationsResponse.locations
    );

    expect(context.mode).toBe("DINE_IN");
    expect(context.tableId).toBe("tbl_001");
    expect(context.locationId).toBe("loc_tbl_001");
    expect(context.sessionId).toBe("ses_001");
    expect(context.orderable).toBe(true);
  });

  it("builds category sections from backend menu metadata", () => {
    const foodSections = buildMenuSections(menuResponse, "FOOD");
    const drinkSections = buildMenuSections(menuResponse, "DRINK");

    expect(foodSections).toHaveLength(1);
    expect(foodSections[0]?.category.name).toBe("Italian");
    expect(foodSections[0]?.items.map((item) => item.name)).toEqual(["Margherita Pizza"]);

    expect(drinkSections).toHaveLength(1);
    expect(drinkSections[0]?.category.name).toBe("Non-Alcoholic");
    expect(drinkSections[0]?.items.map((item) => item.name)).toEqual(["Lemonade"]);
  });

  it("writes URL state back into the browser location shape cleanly", () => {
    const next = buildUrlForState("http://127.0.0.1:5173/?mode=pickup", {
      mode: "DINE_IN",
      tableId: "tbl_001",
      locationId: "loc_tbl_001",
    });

    expect(next).toBe(
      "http://127.0.0.1:5173/?mode=dine-in&tableId=tbl_001&locationId=loc_tbl_001"
    );
  });

  it("maps browser entry modes to backend order sources explicitly", () => {
    expect(orderSourceForMode("DINE_IN")).toBe("WEB_DINE_IN");
    expect(orderSourceForMode("ONLINE_PICKUP")).toBe("ONLINE_PICKUP");
    expect(orderSourceForMode("ONLINE_DELIVERY")).toBe("ONLINE_DELIVERY");
  });
});
