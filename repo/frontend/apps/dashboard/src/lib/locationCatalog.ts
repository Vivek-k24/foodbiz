import type { LocationCatalogEntry } from "./types";

function table(
  locationId: string,
  label: string,
  zone: string,
  sortOrder: number,
  seatCount: number
): LocationCatalogEntry {
  return {
    locationId,
    label,
    type: "TABLE",
    zone,
    seatCount,
    sortOrder,
    manualOnly: false,
    kioskLinked: false,
    supportsBackendSession: true,
  };
}

function kioskTable(
  locationId: string,
  label: string,
  zone: string,
  sortOrder: number,
  seatCount: number
): LocationCatalogEntry {
  return {
    locationId,
    label,
    type: "KIOSK_TABLE",
    zone,
    seatCount,
    sortOrder,
    manualOnly: false,
    kioskLinked: true,
    supportsBackendSession: true,
  };
}

function barSeat(index: number): LocationCatalogEntry {
  const seatId = String(index).padStart(3, "0");
  return {
    locationId: `bar_${seatId}`,
    label: `Bar ${index}`,
    type: "BAR_SEAT",
    zone: "Bar Counter",
    seatCount: 1,
    sortOrder: 200 + index,
    manualOnly: true,
    kioskLinked: false,
    supportsBackendSession: false,
  };
}

export const venueName = "FoodBiz Osteria";

export const locationZones = [
  "Entrance Lane",
  "Main Dining",
  "Window Line",
  "Patio",
  "Bar Counter",
  "Unmapped",
] as const;

export const locationCatalog: LocationCatalogEntry[] = [
  table("tbl_001", "T1", "Entrance Lane", 10, 4),
  table("tbl_002", "T2", "Entrance Lane", 11, 2),
  table("tbl_003", "T3", "Entrance Lane", 12, 4),
  table("tbl_004", "T4", "Main Dining", 20, 4),
  table("tbl_005", "T5", "Main Dining", 21, 4),
  kioskTable("tbl_006", "K6", "Main Dining", 22, 4),
  table("tbl_007", "T7", "Main Dining", 23, 6),
  table("tbl_008", "T8", "Window Line", 30, 2),
  kioskTable("tbl_009", "K9", "Window Line", 31, 2),
  table("tbl_010", "T10", "Window Line", 32, 4),
  table("tbl_011", "T11", "Patio", 40, 4),
  kioskTable("tbl_012", "K12", "Patio", 41, 4),
  ...Array.from({ length: 20 }, (_, index) => barSeat(index + 1)),
];

export const locationCatalogById = new Map(
  locationCatalog.map((location) => [location.locationId, location])
);

export function supportsBackendLocation(locationId: string): boolean {
  const entry = locationCatalogById.get(locationId);
  if (entry) {
    return entry.supportsBackendSession;
  }
  return !locationId.startsWith("bar_");
}
