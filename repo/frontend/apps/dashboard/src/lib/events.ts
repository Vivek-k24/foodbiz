import { normalizeOrder } from "./formatting";
import type { EventEnvelope, OrderPayload } from "./types";

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function getString(record: Record<string, unknown>, key: string): string | null {
  const value = record[key];
  return typeof value === "string" ? value : null;
}

export function parseEnvelope(raw: string): EventEnvelope | null {
  try {
    return JSON.parse(raw) as EventEnvelope;
  } catch {
    return null;
  }
}

export function buildOrderFromEvent(payload: unknown): OrderPayload | null {
  if (!isRecord(payload)) {
    return null;
  }
  const orderId = getString(payload, "orderId");
  if (!orderId) {
    return null;
  }
  return normalizeOrder({
    orderId,
    restaurantId: getString(payload, "restaurantId") ?? undefined,
    locationId: getString(payload, "locationId") ?? undefined,
    tableId: getString(payload, "tableId") ?? undefined,
    sessionId: getString(payload, "sessionId") ?? undefined,
    source: getString(payload, "source") ?? undefined,
    status: getString(payload, "status") ?? "",
    totalMoney: isRecord(payload.totalMoney)
      ? {
          amountCents:
            typeof payload.totalMoney.amountCents === "number"
              ? payload.totalMoney.amountCents
              : null,
          currency:
            typeof payload.totalMoney.currency === "string" ? payload.totalMoney.currency : null,
        }
      : null,
    total: isRecord(payload.total)
      ? {
          amountCents: typeof payload.total.amountCents === "number" ? payload.total.amountCents : null,
          currency: typeof payload.total.currency === "string" ? payload.total.currency : null,
        }
      : null,
    createdAt: getString(payload, "createdAt") ?? "",
    updatedAt: getString(payload, "updatedAt") ?? undefined,
    lines: Array.isArray(payload.lines) ? (payload.lines as OrderPayload["lines"]) : [],
  });
}

export function getTableEventPayload(payload: unknown): {
  tableId: string;
  openedAt?: string;
  closedAt?: string;
  status?: string;
} | null {
  if (!isRecord(payload)) {
    return null;
  }
  const tableId = getString(payload, "tableId");
  if (!tableId) {
    return null;
  }
  const next: {
    tableId: string;
    openedAt?: string;
    closedAt?: string;
    status?: string;
  } = { tableId };
  const openedAt = getString(payload, "openedAt");
  const closedAt = getString(payload, "closedAt");
  const status = getString(payload, "status");
  if (openedAt) {
    next.openedAt = openedAt;
  }
  if (closedAt) {
    next.closedAt = closedAt;
  }
  if (status) {
    next.status = status;
  }
  return next;
}
