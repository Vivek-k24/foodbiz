import type { LocationRecord } from "./types";

export const venueName = "FoodBiz Grand Kitchen";

const preferredZoneOrder = [
  "Entrance Lane",
  "Main Dining",
  "Window Line",
  "Patio",
  "Bar Counter",
  "Off Premise",
];

export function locationZoneSortValue(zone: string): number {
  const index = preferredZoneOrder.indexOf(zone);
  return index === -1 ? preferredZoneOrder.length : index;
}

export function tableIdFromLocationId(locationId: string): string | null {
  if (!locationId.startsWith("loc_tbl_")) {
    return null;
  }
  return locationId.replace(/^loc_/, "");
}

export function locationLabel(record: LocationRecord): string {
  return record.displayLabel?.trim() || record.name || record.locationId;
}
