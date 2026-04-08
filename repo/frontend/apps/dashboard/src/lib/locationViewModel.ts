import { locationCatalog, locationZones } from "./locationCatalog";
import { maxTimestamp } from "./formatting";
import type {
  LocationCounts,
  QueueSection,
  StaffLocation,
  StaffMode,
  SummaryStats,
  TableRegistryItem,
  OrderPayload,
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
  if (location.counts.ready > 0) {
    return "ATTENTION";
  }
  if (location.counts.placed > 0 || location.counts.accepted > 0 || location.counts.served > 0) {
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

function buildFallbackLocation(tableId: string): StaffLocation {
  return {
    locationId: tableId,
    label: tableId.toUpperCase(),
    type: "TABLE",
    zone: "Unmapped",
    seatCount: 4,
    sortOrder: 10_000,
    manualOnly: false,
    kioskLinked: false,
    supportsBackendSession: true,
    backendStatus: null,
    sessionOpen: false,
    uiStatus: "AVAILABLE",
    openedAt: null,
    closedAt: null,
    lastOrderAt: null,
    totals: { amountCents: 0, currency: "USD" },
    counts: emptyCounts(),
    activeOrderIds: [],
    assignmentState: "NOT_APPLICABLE",
  };
}

export function buildStaffLocations(
  tableRows: Record<string, TableRegistryItem>,
  ordersById: Record<string, OrderPayload>
): StaffLocation[] {
  const catalogById = new Map(locationCatalog.map((location) => [location.locationId, location]));
  const byLocation = new Map<string, OrderPayload[]>();

  for (const order of Object.values(ordersById)) {
    if (!order.tableId) {
      continue;
    }
    const existing = byLocation.get(order.tableId) ?? [];
    existing.push(order);
    byLocation.set(order.tableId, existing);
  }

  const merged: StaffLocation[] = locationCatalog.map((catalogEntry) => {
    const row = tableRows[catalogEntry.locationId];
    const orders = byLocation.get(catalogEntry.locationId) ?? [];
    const counts: LocationCounts = {
      ordersTotal: row?.counts.ordersTotal ?? 0,
      placed: row?.counts.placed ?? 0,
      accepted: row?.counts.accepted ?? 0,
      ready: row?.counts.ready ?? 0,
      served: orders.filter((order) => order.status === "SERVED").length,
      settled: orders.filter((order) => order.status === "SETTLED").length,
    };
    const sessionOpen = row?.status === "OPEN";
    const lastOrderAt = orders.reduce<string | null>(
      (current, order) => maxTimestamp(current, order.createdAt),
      row?.lastOrderAt ?? null
    );
    const activeOrderIds = orders
      .filter((order) => order.status !== "SETTLED")
      .map((order) => order.orderId);

    const location: StaffLocation = {
      ...catalogEntry,
      backendStatus: row?.status === "OPEN" || row?.status === "CLOSED" ? row.status : null,
      sessionOpen,
      openedAt: row?.openedAt ?? null,
      closedAt: row?.closedAt ?? null,
      lastOrderAt,
      totals: row?.totals ?? { amountCents: 0, currency: "USD" },
      counts,
      activeOrderIds,
      assignmentState: catalogEntry.manualOnly
        ? "MANUAL_ONLY"
        : sessionOpen
          ? "UNASSIGNED"
          : "NOT_APPLICABLE",
      uiStatus: deriveUiStatus({
        manualOnly: catalogEntry.manualOnly,
        sessionOpen,
        backendStatus: row?.status === "OPEN" || row?.status === "CLOSED" ? row.status : null,
        lastOrderAt,
        counts,
      }),
    };

    return location;
  });

  for (const row of Object.values(tableRows)) {
    if (catalogById.has(row.tableId)) {
      continue;
    }
    const fallback = buildFallbackLocation(row.tableId);
    merged.push({
      ...fallback,
      backendStatus: row.status === "OPEN" || row.status === "CLOSED" ? row.status : null,
      sessionOpen: row.status === "OPEN",
      openedAt: row.openedAt,
      closedAt: row.closedAt,
      lastOrderAt: row.lastOrderAt,
      totals: row.totals,
      counts: {
        ordersTotal: row.counts.ordersTotal,
        placed: row.counts.placed,
        accepted: row.counts.accepted,
        ready: row.counts.ready,
        served: 0,
        settled: 0,
      },
      uiStatus: deriveUiStatus({
        manualOnly: false,
        sessionOpen: row.status === "OPEN",
        backendStatus: row.status === "OPEN" || row.status === "CLOSED" ? row.status : null,
        lastOrderAt: row.lastOrderAt,
        counts: {
          ordersTotal: row.counts.ordersTotal,
          placed: row.counts.placed,
          accepted: row.counts.accepted,
          ready: row.counts.ready,
          served: 0,
          settled: 0,
        },
      }),
      assignmentState: row.status === "OPEN" ? "UNASSIGNED" : "NOT_APPLICABLE",
    });
  }

  return merged.sort((left, right) => {
    const zoneDelta = locationZones.indexOf(left.zone as (typeof locationZones)[number]) - locationZones.indexOf(right.zone as (typeof locationZones)[number]);
    if (zoneDelta !== 0) {
      return zoneDelta;
    }
    if (left.sortOrder !== right.sortOrder) {
      return left.sortOrder - right.sortOrder;
    }
    return left.locationId.localeCompare(right.locationId);
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
  const nonManual = locations.filter((location) => !location.manualOnly);
  const manual = locations.filter((location) => location.manualOnly);

  if (mode === "ENTRANCE") {
    return [
      {
        id: "available-now",
        title: "Available now",
        emptyText: "No locations are immediately available.",
        items: nonManual.filter((location) => location.uiStatus === "AVAILABLE"),
      },
      {
        id: "open-sessions",
        title: "Open sessions",
        emptyText: "No live sessions are open right now.",
        items: nonManual.filter((location) => location.sessionOpen),
      },
      {
        id: "turnover-watch",
        title: "Turnover watch",
        emptyText: "No recently closed locations need turnover attention.",
        items: nonManual.filter((location) => location.uiStatus === "TURNOVER"),
      },
      {
        id: "bar-overview",
        title: "Bar counter",
        emptyText: "Bar seats are not configured in the venue catalog.",
        items: manual,
      },
    ];
  }

  return [
    {
      id: "needs-attention",
      title: "Needs attention",
      emptyText: "No sessions currently need ready/serve attention.",
      items: nonManual.filter(
        (location) => location.uiStatus === "ATTENTION" || location.counts.served > 0
      ),
    },
    {
      id: "ordering-active",
      title: "Ordering active",
      emptyText: "No sessions are currently moving through ordering.",
      items: nonManual.filter((location) => location.uiStatus === "ORDERING"),
    },
    {
      id: "open-unassigned",
      title: "Open and unassigned",
      emptyText: "No open sessions are waiting for service ownership.",
      items: nonManual.filter(
        (location) => location.sessionOpen && location.assignmentState === "UNASSIGNED"
      ),
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
  return locationZones
    .map((zone) => ({
      zone,
      items: locations.filter((location) => location.zone === zone),
    }))
    .filter((group) => group.items.length > 0);
}
