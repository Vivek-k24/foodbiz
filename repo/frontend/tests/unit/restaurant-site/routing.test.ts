import { describe, expect, it } from "vitest";

import { buildOrderingHref } from "../../../apps/restaurant-site/src/lib/routing";

describe("restaurant site CTA routing", () => {
  it("builds pickup and delivery links into the ordering surface", () => {
    expect(buildOrderingHref("http://127.0.0.1:5173", "pickup")).toBe(
      "http://127.0.0.1:5173/?mode=pickup"
    );
    expect(buildOrderingHref("http://127.0.0.1:5173", "delivery")).toBe(
      "http://127.0.0.1:5173/?mode=delivery"
    );
  });
});
