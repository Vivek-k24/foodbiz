import { normalizeOrder } from "./formatting";
import type {
  ApiError,
  ApiErrorResponse,
  KitchenQueueResponse,
  OrderAction,
  OrderPayload,
  TableOrdersResponse,
  TableRegistryResponse,
  TableSummaryResponse,
} from "./types";

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";
export const restaurantId = "rst_001";

async function readApiError(response: Response): Promise<ApiError> {
  try {
    const payload = (await response.json()) as ApiErrorResponse;
    if (payload.error?.message) {
      return {
        code: payload.error.code ?? null,
        message: payload.error.message,
        requestId: payload.requestId ?? null,
      };
    }
  } catch {
    // Ignore malformed error payloads.
  }
  return {
    code: null,
    message: `request failed (${response.status})`,
    requestId: null,
  };
}

export function formatApiError(error: ApiError): string {
  return error.code ? `${error.code}: ${error.message}` : error.message;
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    throw new Error(formatApiError(await readApiError(response)));
  }
  return (await response.json()) as T;
}

export async function fetchTableRegistry(): Promise<TableRegistryResponse> {
  const url = `${apiBaseUrl}/v1/restaurants/${restaurantId}/tables?status=ALL&limit=200`;
  return fetchJson<TableRegistryResponse>(url);
}

export async function fetchKitchenOrders(): Promise<OrderPayload[]> {
  const statuses = ["PLACED", "ACCEPTED", "READY", "SERVED"] as const;
  const payloads = await Promise.all(
    statuses.map((status) =>
      fetchJson<KitchenQueueResponse>(
        `${apiBaseUrl}/v1/restaurants/${restaurantId}/kitchen/orders?status=${status}&limit=50`
      )
    )
  );
  return payloads.flatMap((payload) => payload.orders.map(normalizeOrder));
}

export async function fetchLocationOrders(tableId: string): Promise<OrderPayload[]> {
  const payload = await fetchJson<TableOrdersResponse>(
    `${apiBaseUrl}/v1/restaurants/${restaurantId}/tables/${encodeURIComponent(
      tableId
    )}/orders?status=ALL&limit=50`
  );
  return payload.orders.map(normalizeOrder);
}

export async function fetchLocationSummary(tableId: string): Promise<TableSummaryResponse> {
  return fetchJson<TableSummaryResponse>(
    `${apiBaseUrl}/v1/restaurants/${restaurantId}/tables/${encodeURIComponent(tableId)}/summary`
  );
}

export async function openLocation(tableId: string): Promise<void> {
  await fetchJson(
    `${apiBaseUrl}/v1/restaurants/${restaurantId}/tables/${encodeURIComponent(tableId)}/open`,
    { method: "POST" }
  );
}

export async function closeLocation(tableId: string): Promise<void> {
  await fetchJson(
    `${apiBaseUrl}/v1/restaurants/${restaurantId}/tables/${encodeURIComponent(tableId)}/close`,
    { method: "POST" }
  );
}

export async function advanceOrder(orderId: string, action: OrderAction): Promise<OrderPayload> {
  return normalizeOrder(
    await fetchJson<OrderPayload>(`${apiBaseUrl}/v1/orders/${encodeURIComponent(orderId)}/${action}`, {
      method: "POST",
    })
  );
}

export function buildStaffConsoleWsUrl(): string {
  const url = new URL("/ws", wsBaseUrl);
  url.searchParams.set("restaurant_id", restaurantId);
  url.searchParams.set("role", "STAFF_CONSOLE");
  return url.toString();
}
