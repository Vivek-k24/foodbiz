import { locationLabel, locationZoneSortValue, tableIdFromLocationId } from "./locationCatalog";
import type {
  LocationCounts,
  LocationRecord,
  OrderPayload,
  QueueSection,
  StaffLocation,
  StaffMode,
  SummaryStats,
  TableRegistryItem,
} from "./types";

function emptyCounts(): LocationCounts {
  return {
    ordersTotal: 0,
    placed: 0,
    accepted: 0,
    ready: 0,
    served: 0,
    settled: 0,
  };
}

function summarizeLocationOrders(
  locationId: string,
  ordersById: Record<string, OrderPayload>
): {
  counts: LocationCounts;
  amountCents: number;
  currency: string;
  lastOrderAt: string | null;
} {
  const counts = emptyCounts();
  let amountCents = 0;
  let currency = "USD";
  let lastOrderAt: string | null = null;

  for (const order of Object.values(ordersById)) {
    if (order.locationId !== locationId) {
      continue;
    }

    counts.ordersTotal += 1;
    if (order.status === "PLACED") {
      counts.placed += 1;
    }
    if (order.status === "ACCEPTED") {
      counts.accepted += 1;
    }
    if (order.status === "READY") {
      counts.ready += 1;
    }
    if (order.status === "SERVED") {
      counts.served += 1;
    }
    if (order.status === "SETTLED") {
      counts.settled += 1;
    }

    const totalMoney = order.totalMoney ?? order.total;
    if (typeof totalMoney?.amountCents === "number") {
      amountCents += totalMoney.amountCents;
    }
    if (typeof totalMoney?.currency === "string" && totalMoney.currency.trim()) {
      currency = totalMoney.currency;
    }
    if (!lastOrderAt || new Date(order.createdAt).getTime() > new Date(lastOrderAt).getTime()) {
      lastOrderAt = order.createdAt;
    }
  }

  return {
    counts,
    amountCents,
    currency,
    lastOrderAt,
  };
}

function deriveUiStatus(location: {
  manualOnly: boolean;
  sessionOpen: boolean;
  backendStatus: "OPEN" | "CLOSED" | null;
  lastOrderAt: string | null;
  counts: LocationCounts;
}): StaffLocation["uiStatus"] {
  if (location.manualOnly) {
    return "MANUAL";
  }
  if (location.counts.ready > 0 || location.counts.served > 0) {
    return "ATTENTION";
  }
  if (location.counts.placed > 0 || location.counts.accepted > 0) {
    return "ORDERING";
  }
  if (location.sessionOpen) {
    return "OCCUPIED";
  }
  if (location.backendStatus === "CLOSED" && location.lastOrderAt) {
    return "TURNOVER";
  }
  return "AVAILABLE";
}

export function buildStaffLocations(
  locationRows: LocationRecord[],
  tableRows: Record<string, TableRegistryItem>,
  ordersById: Record<string, OrderPayload>
): StaffLocation[] {
  return [...locationRows]
    .map((location, index) => {
      const backendTableId = location.type === "TABLE" ? tableIdFromLocationId(location.locationId) : null;
      const tableRow = backendTableId ? tableRows[backendTableId] : undefined;
      const offPremiseSummary =
        location.type === "ONLINE_PICKUP" || location.type === "ONLINE_DELIVERY"
          ? summarizeLocationOrders(location.locationId, ordersById)
          : null;
      const counts: LocationCounts = tableRow?.counts ?? offPremiseSummary?.counts ?? emptyCounts();
      const manualOnly = location.type === "BAR_SEAT";
      const sessionOpen = location.sessionStatus === "OPEN" || tableRow?.status === "OPEN";
      const lastOrderAt = tableRow?.lastOrderAt ?? offPremiseSummary?.lastOrderAt ?? null;
      const backendStatus = tableRow?.status === "OPEN" || tableRow?.status === "CLOSED" ? tableRow.status : location.sessionStatus;

      return {
        locationId: location.locationId,
        restaurantId: location.restaurantId,
        label: locationLabel(location),
        type: location.type,
        zone: location.zone ?? "Unmapped",
        seatCount: location.capacity ?? 0,
        sortOrder: locationZoneSortValue(location.zone ?? "Unmapped") * 100 + index,
        manualOnly,
        scanEnabled: location.type === "TABLE",
        supportsBackendSession: location.type === "TABLE",
        backendTableId,
        activeSessionId: location.activeSessionId,
        backendStatus,
        sessionOpen,
        openedAt: location.lastSessionOpenedAt ?? tableRow?.openedAt ?? null,
        closedAt: tableRow?.closedAt ?? null,
        lastOrderAt,
        totals: tableRow?.totals ?? {
          amountCents: offPremiseSummary?.amountCents ?? 0,
          currency: offPremiseSummary?.currency ?? "USD",
        },
        counts,
        activeOrderIds: [],
        assignmentState: manualOnly
          ? "MANUAL_ONLY"
          : sessionOpen && location.type === "TABLE"
            ? "UNASSIGNED"
            : "NOT_APPLICABLE",
        uiStatus: deriveUiStatus({
          manualOnly,
          sessionOpen,
          backendStatus,
          lastOrderAt,
          counts,
        }),
      } satisfies StaffLocation;
    })
    .sort((left, right) => {
      if (left.sortOrder !== right.sortOrder) {
        return left.sortOrder - right.sortOrder;
      }
      return left.label.localeCompare(right.label);
    });
}

export function filterLocations(
  locations: StaffLocation[],
  search: string,
  typeFilter: StaffLocation["type"] | "ALL",
  statusFilter: StaffLocation["uiStatus"] | "ALL"
): StaffLocation[] {
  const query = search.trim().toLowerCase();
  return locations.filter((location) => {
    if (typeFilter !== "ALL" && location.type !== typeFilter) {
      return false;
    }
    if (statusFilter !== "ALL" && location.uiStatus !== statusFilter) {
      return false;
    }
    if (!query) {
      return true;
    }
    const haystack = [location.locationId, location.label, location.zone, location.type]
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  });
}

export function buildQueueSections(mode: StaffMode, locations: StaffLocation[]): QueueSection[] {
  const tables = locations.filter((location) => location.type === "TABLE");
  const manual = locations.filter((location) => location.manualOnly);
  const offPremise = locations.filter(
    (location) => location.type === "ONLINE_PICKUP" || location.type === "ONLINE_DELIVERY"
  );

  if (mode === "ENTRANCE") {
    return [
      {
        id: "available-now",
        title: "Available now",
        emptyText: "No dining tables are immediately available.",
        items: tables.filter((location) => location.uiStatus === "AVAILABLE"),
      },
      {
        id: "open-sessions",
        title: "Open sessions",
        emptyText: "No live table sessions are open right now.",
        items: tables.filter((location) => location.sessionOpen),
      },
      {
        id: "turnover-watch",
        title: "Turnover watch",
        emptyText: "No recently closed tables need turnover attention.",
        items: tables.filter((location) => location.uiStatus === "TURNOVER"),
      },
      {
        id: "bar-overview",
        title: "Bar awareness",
        emptyText: "Bar seats are not configured in the venue catalog.",
        items: manual,
      },
    ];
  }

  return [
    {
      id: "needs-follow-through",
      title: "Needs follow-through",
      emptyText: "No active tables currently need service follow-through.",
      items: tables.filter(
        (location) => location.counts.ready > 0 || location.counts.served > 0
      ),
    },
    {
      id: "ordering-active",
      title: "Ordering active",
      emptyText: "No table sessions are currently moving through kitchen prep.",
      items: tables.filter(
        (location) => location.counts.placed > 0 || location.counts.accepted > 0
      ),
    },
    {
      id: "open-unassigned",
      title: "Open and unassigned",
      emptyText: "No open table sessions are waiting for service follow-through.",
      items: tables.filter(
        (location) => location.sessionOpen && location.assignmentState === "UNASSIGNED"
      ),
    },
    {
      id: "off-premise",
      title: "Off-premise lanes",
      emptyText: "No pickup or delivery locations are configured.",
      items: offPremise,
    },
  ];
}

export function buildSummaryStats(locations: StaffLocation[]): SummaryStats {
  return locations.reduce<SummaryStats>(
    (current, location) => {
      if (location.uiStatus === "AVAILABLE") {
        current.available += 1;
      }
      if (location.sessionOpen) {
        current.openSessions += 1;
      }
      if (location.uiStatus === "ATTENTION") {
        current.attention += 1;
      }
      if (location.uiStatus === "ORDERING") {
        current.ordering += 1;
      }
      if (location.manualOnly) {
        current.manual += 1;
      }
      return current;
    },
    {
      available: 0,
      openSessions: 0,
      attention: 0,
      ordering: 0,
      manual: 0,
    }
  );
}

export function groupLocationsByZone(locations: StaffLocation[]): Array<{
  zone: string;
  items: StaffLocation[];
}> {
  const groups = new Map<string, StaffLocation[]>();
  for (const location of locations) {
    const bucket = groups.get(location.zone) ?? [];
    bucket.push(location);
    groups.set(location.zone, bucket);
  }

  return [...groups.entries()]
    .map(([zone, items]) => ({ zone, items }))
    .sort((left, right) => locationZoneSortValue(left.zone) - locationZoneSortValue(right.zone));
}
