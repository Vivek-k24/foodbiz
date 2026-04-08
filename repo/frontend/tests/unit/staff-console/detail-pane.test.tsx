import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DetailPane } from "../../../apps/dashboard/src/components/DetailPane";
import type { OrderPayload, StaffLocation, TableSummaryResponse } from "../../../apps/dashboard/src/lib/types";

function buildLocation(): StaffLocation {
  return {
    locationId: "loc_tbl_001",
    label: "Table 1",
    type: "TABLE",
    zone: "Main Dining",
    seatCount: 4,
    uiStatus: "READY",
    backendTableId: "tbl_001",
    sessionOpen: true,
    activeSessionId: "ses_001",
    openedAt: "2026-04-08T12:00:00Z",
    lastOrderAt: "2026-04-08T12:25:00Z",
    totals: { amountCents: 1450, currency: "USD" },
    counts: {
      ordersTotal: 1,
      placed: 0,
      accepted: 0,
      ready: 1,
      served: 0,
      settled: 0,
    },
    manualOnly: false,
    scanEnabled: true,
    supportsBackendSession: true,
    assignmentState: "ACTIVE",
  };
}

function buildSummary(): TableSummaryResponse {
  return {
    tableId: "tbl_001",
    restaurantId: "rst_001",
    status: "OPEN",
    openedAt: "2026-04-08T12:00:00Z",
    closedAt: null,
    totals: { amountCents: 1450, currency: "USD" },
    counts: {
      ordersTotal: 1,
      placed: 0,
      accepted: 0,
      ready: 1,
      served: 0,
      settled: 0,
    },
    lastOrderAt: "2026-04-08T12:25:00Z",
  };
}

function buildOrder(status: string): OrderPayload {
  return {
    orderId: "ord_001",
    restaurantId: "rst_001",
    locationId: "loc_tbl_001",
    tableId: "tbl_001",
    sessionId: "ses_001",
    source: "WEB_DINE_IN",
    status,
    lines: [
      {
        lineId: "line_001",
        itemId: "itm_001",
        name: "Margherita Pizza",
        quantity: 1,
        notes: null,
        modifiers: [],
      },
    ],
    total: { amountCents: 1450, currency: "USD" },
    totalMoney: { amountCents: 1450, currency: "USD" },
    createdAt: "2026-04-08T12:25:00Z",
    updatedAt: "2026-04-08T12:25:00Z",
  };
}

describe("staff console detail pane", () => {
  it("shows service-side actions without exposing kitchen accept/ready controls", () => {
    render(
      <DetailPane
        mode="SERVICE"
        location={buildLocation()}
        summary={buildSummary()}
        orders={[buildOrder("READY")]}
        loading={false}
        error={null}
        message={null}
        locationActionPending={null}
        orderActionPending={{}}
        orderActionError={{}}
        onOpenLocation={vi.fn()}
        onCloseLocation={vi.fn()}
        onOrderAction={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: "Mark Served" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Accept" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Mark Ready" })).not.toBeInTheDocument();
  });

  it("surfaces settlement follow-through for served orders", () => {
    render(
      <DetailPane
        mode="SERVICE"
        location={buildLocation()}
        summary={buildSummary()}
        orders={[buildOrder("SERVED")]}
        loading={false}
        error={null}
        message={null}
        locationActionPending={null}
        orderActionPending={{}}
        orderActionError={{}}
        onOpenLocation={vi.fn()}
        onCloseLocation={vi.fn()}
        onOrderAction={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: "Mark Settled" })).toBeInTheDocument();
  });
});
