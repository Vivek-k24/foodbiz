export type EntryMode = "DINE_IN" | "ONLINE_PICKUP" | "ONLINE_DELIVERY";

export type BackendOrderSource = "WEB_DINE_IN" | "ONLINE_PICKUP" | "ONLINE_DELIVERY";

export type OrderingUrlState = {
  mode: EntryMode | null;
  tableId: string | null;
  locationId: string | null;
};

export type OrderingLocationRecord = {
  locationId: string;
  type: "TABLE" | "BAR_SEAT" | "ONLINE_PICKUP" | "ONLINE_DELIVERY";
  displayLabel: string;
  sessionStatus: "OPEN" | "CLOSED" | null;
  activeSessionId: string | null;
};

export type ActiveOrderingContext = {
  mode: EntryMode;
  locationId: string | null;
  tableId: string | null;
  sessionId: string | null;
  label: string;
  subtitle: string;
  scanSource: boolean;
  orderable: boolean;
  orderableMessage: string;
};

export type MenuCategoryRecord = {
  categoryId: string;
  name: string;
  categoryKind: "FOOD" | "DRINK";
  cuisineOrFamily: string;
};

export type MenuItemRecord = {
  itemId: string;
  categoryId?: string | null;
};

export type MenuRecord = {
  categories: MenuCategoryRecord[];
  items: MenuItemRecord[];
};

export type MenuSection = {
  category: MenuCategoryRecord;
  items: MenuItemRecord[];
};

export function orderSourceForMode(mode: EntryMode): BackendOrderSource {
  if (mode === "DINE_IN") {
    return "WEB_DINE_IN";
  }
  return mode;
}

export function readUrlStateFromHref(href: string): OrderingUrlState {
  const params = new URL(href).searchParams;
  const rawMode = params.get("mode")?.toLowerCase();
  const mode =
    rawMode === "pickup"
      ? "ONLINE_PICKUP"
      : rawMode === "delivery"
        ? "ONLINE_DELIVERY"
        : rawMode === "dine-in"
          ? "DINE_IN"
          : null;

  return {
    mode,
    tableId: params.get("tableId")?.trim() || null,
    locationId: params.get("locationId")?.trim() || null,
  };
}

export function buildUrlForState(href: string, state: OrderingUrlState): string {
  const url = new URL(href);
  url.searchParams.delete("mode");
  url.searchParams.delete("tableId");
  url.searchParams.delete("locationId");

  if (state.mode === "ONLINE_PICKUP") {
    url.searchParams.set("mode", "pickup");
  }
  if (state.mode === "ONLINE_DELIVERY") {
    url.searchParams.set("mode", "delivery");
  }
  if (state.mode === "DINE_IN") {
    url.searchParams.set("mode", "dine-in");
  }
  if (state.tableId) {
    url.searchParams.set("tableId", state.tableId);
  }
  if (state.locationId) {
    url.searchParams.set("locationId", state.locationId);
  }

  return url.toString();
}

export function normalizeTableId(value: string | null): string | null {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.startsWith("loc_tbl_")) {
    return trimmed.replace(/^loc_/, "");
  }
  return trimmed;
}

export function locationIdFromTableId(tableId: string | null): string | null {
  if (!tableId) {
    return null;
  }
  const trimmed = tableId.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.startsWith("loc_tbl_")) {
    return trimmed;
  }
  return `loc_${trimmed}`;
}

export function resolveActiveContext(
  urlState: OrderingUrlState,
  locations: OrderingLocationRecord[]
): ActiveOrderingContext {
  const resolvedTableId = normalizeTableId(urlState.tableId);
  const resolvedLocationId = urlState.locationId ?? locationIdFromTableId(resolvedTableId);
  const scanLocation =
    resolvedLocationId
      ? locations.find((location) => location.locationId === resolvedLocationId) ?? null
      : null;
  const pickupLocation =
    locations.find((location) => location.locationId === "loc_online_pickup") ?? null;
  const deliveryLocation =
    locations.find((location) => location.locationId === "loc_online_delivery") ?? null;
  const hasDineInIntent = urlState.mode === "DINE_IN" || (!urlState.mode && scanLocation !== null);

  if (hasDineInIntent) {
    if (!scanLocation || scanLocation.type !== "TABLE") {
      return {
        mode: "DINE_IN",
        locationId: resolvedLocationId,
        tableId: resolvedTableId,
        sessionId: null,
        label: "Dine-In Table",
        subtitle:
          "Scan a valid table QR code or use a supported table link to start dine-in ordering.",
        scanSource: resolvedLocationId !== null || resolvedTableId !== null,
        orderable: false,
        orderableMessage: "This table context is missing or invalid.",
      };
    }

    const tableId = resolvedTableId ?? scanLocation.locationId.replace(/^loc_/, "");
    const orderable = scanLocation.sessionStatus === "OPEN" && !!scanLocation.activeSessionId;
    return {
      mode: "DINE_IN",
      locationId: scanLocation.locationId,
      tableId,
      sessionId: scanLocation.activeSessionId,
      label: scanLocation.displayLabel,
      subtitle: orderable
        ? `Dine-in ordering is attached to the open session for ${scanLocation.displayLabel}.`
        : `This scan-aware table exists, but staff has not opened the dining session yet.`,
      scanSource: true,
      orderable,
      orderableMessage: orderable
        ? "Ready to order."
        : "Ask staff to open the table session before ordering.",
    };
  }

  if (urlState.mode === "ONLINE_DELIVERY") {
    return {
      mode: "ONLINE_DELIVERY",
      locationId: deliveryLocation?.locationId ?? null,
      tableId: null,
      sessionId: null,
      label: "Delivery Order",
      subtitle: `Delivery ordering routes through ${
        deliveryLocation?.displayLabel ?? "the delivery dispatch lane"
      } instead of a dining-room session.`,
      scanSource: false,
      orderable: deliveryLocation !== null,
      orderableMessage: deliveryLocation
        ? "Delivery orders are enabled."
        : "Delivery location is unavailable.",
    };
  }

  return {
    mode: "ONLINE_PICKUP",
    locationId: pickupLocation?.locationId ?? null,
    tableId: null,
    sessionId: null,
    label: "Pickup Order",
    subtitle: `Pickup ordering routes through ${
      pickupLocation?.displayLabel ?? "the pickup counter"
    } and stays separate from internal staff workflows.`,
    scanSource: false,
    orderable: pickupLocation !== null,
    orderableMessage: pickupLocation
      ? "Pickup orders are enabled."
      : "Pickup location is unavailable.",
  };
}

export function buildMenuSections(
  menu: MenuRecord | null,
  categoryKind: "FOOD" | "DRINK"
): MenuSection[] {
  if (!menu) {
    return [];
  }

  return menu.categories
    .filter((category) => category.categoryKind === categoryKind)
    .map((category) => ({
      category,
      items: menu.items.filter((item) => item.categoryId === category.categoryId),
    }))
    .filter((section) => section.items.length > 0);
}
