import type { LocationType, LocationUiStatus } from "../lib/types";

export function orderStatusClass(status: string): string {
  switch (status) {
    case "PLACED":
      return "badge badgeOrderPlaced";
    case "ACCEPTED":
      return "badge badgeOrderAccepted";
    case "READY":
      return "badge badgeOrderReady";
    case "SERVED":
      return "badge badgeOrderServed";
    case "SETTLED":
      return "badge badgeOrderSettled";
    default:
      return "badge";
  }
}

export function locationStatusClass(status: LocationUiStatus): string {
  switch (status) {
    case "AVAILABLE":
      return "badge badgeLocationAvailable";
    case "OCCUPIED":
      return "badge badgeLocationOccupied";
    case "ORDERING":
      return "badge badgeLocationOrdering";
    case "ATTENTION":
      return "badge badgeLocationAttention";
    case "TURNOVER":
      return "badge badgeLocationTurnover";
    case "MANUAL":
      return "badge badgeLocationManual";
    default:
      return "badge";
  }
}

export function locationTypeClass(type: LocationType): string {
  switch (type) {
    case "TABLE":
      return "badge badgeTypeTable";
    case "BAR_SEAT":
      return "badge badgeTypeBar";
    case "ONLINE_PICKUP":
      return "badge badgeTypePickup";
    case "ONLINE_DELIVERY":
      return "badge badgeTypeDelivery";
    default:
      return "badge";
  }
}
