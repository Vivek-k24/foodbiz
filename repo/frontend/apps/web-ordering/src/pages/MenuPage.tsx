import { useEffect, useMemo, useState } from "react";

type Money = {
  amountCents: number;
  currency: string;
};

type MenuItem = {
  itemId: string;
  name: string;
  description?: string | null;
  priceMoney: Money;
  isAvailable: boolean;
  categoryId?: string | null;
};

type MenuResponse = {
  menuId: string;
  restaurantId: string;
  menuVersion: number;
  items: MenuItem[];
};

type OrderMoney = {
  amountCents?: number | null;
  currency?: string | null;
};

type OrderLine = {
  lineId: string;
  itemId: string;
  name: string;
  quantity: number;
};

type TableOrder = {
  orderId: string;
  tableId: string;
  status: string;
  total?: OrderMoney | null;
  totalMoney?: OrderMoney | null;
  createdAt: string;
  lines: OrderLine[];
};

type TableOrdersResponse = {
  orders: TableOrder[];
  nextCursor: string | null;
};

type EventEnvelope = {
  event_type: string;
  payload?: Record<string, unknown>;
};

type ApiErrorResponse = {
  error?: {
    code?: string;
    message?: string;
  };
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";
const selectedTableStorageKey = "rop.selectedTableId";

function readInitialTableId(): string {
  if (typeof window === "undefined") {
    return "tbl_001";
  }
  return window.localStorage.getItem(selectedTableStorageKey) || "tbl_001";
}

function buildIdempotencyKey(tableId: string): string {
  const now = new Date();
  const pad = (value: number) => String(value).padStart(2, "0");
  const stamp = [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate()),
    pad(now.getHours()),
    pad(now.getMinutes()),
    pad(now.getSeconds()),
  ].join("");
  const random = Math.random().toString(36).slice(2, 8).padEnd(6, "0");
  return `rop8-${tableId}-${stamp}-${random}`;
}

function formatMenuMoney(money: Money): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: money.currency,
  }).format(money.amountCents / 100);
}

function formatOrderTotal(total: OrderMoney | null | undefined): string {
  if (!total || typeof total.amountCents !== "number" || typeof total.currency !== "string") {
    return "-";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: total.currency,
  }).format(total.amountCents / 100);
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function normalizeOrder(order: TableOrder): TableOrder {
  return {
    ...order,
    totalMoney: order.totalMoney ?? order.total ?? null,
    lines: Array.isArray(order.lines) ? order.lines : [],
  };
}

function getOrderMoney(order: TableOrder): OrderMoney | null | undefined {
  return order.totalMoney ?? order.total;
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as ApiErrorResponse;
    if (payload.error?.message) {
      return payload.error.code
        ? `${payload.error.code}: ${payload.error.message}`
        : payload.error.message;
    }
  } catch {
    // Ignore malformed error payloads.
  }
  return `request failed (${response.status})`;
}

export function MenuPage() {
  const [menu, setMenu] = useState<MenuResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [placingOrder, setPlacingOrder] = useState(false);
  const [orderResult, setOrderResult] = useState<string | null>(null);
  const [tableOrders, setTableOrders] = useState<Record<string, TableOrder>>({});
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [ordersError, setOrdersError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState("Connecting");
  const [tableId, setTableId] = useState(readInitialTableId);

  const menuEndpoint = useMemo(() => `${apiBaseUrl}/v1/restaurants/rst_001/menu`, []);
  const tableOrdersEndpoint = useMemo(
    () =>
      `${apiBaseUrl}/v1/restaurants/rst_001/tables/${encodeURIComponent(tableId)}/orders?status=ALL&limit=50`,
    [tableId]
  );
  const placeOrderEndpoint = useMemo(
    () =>
      `${apiBaseUrl}/v1/restaurants/rst_001/tables/${encodeURIComponent(tableId)}/orders`,
    [tableId]
  );
  const wsUrl = useMemo(() => {
    const url = new URL("/ws", wsBaseUrl);
    url.searchParams.set("restaurant_id", "rst_001");
    url.searchParams.set("role", "TABLET");
    return url.toString();
  }, []);

  function mergeOrders(incoming: TableOrder[]): void {
    setTableOrders((current) => {
      const next = { ...current };
      for (const incomingOrder of incoming) {
        if (!incomingOrder.orderId || incomingOrder.tableId !== tableId) {
          continue;
        }
        next[incomingOrder.orderId] = normalizeOrder(incomingOrder);
      }
      return next;
    });
  }

  async function loadTableOrders(): Promise<void> {
    setOrdersLoading(true);
    setOrdersError(null);
    try {
      const response = await fetch(tableOrdersEndpoint);
      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }
      const payload = (await response.json()) as TableOrdersResponse;
      mergeOrders(payload.orders);
    } catch (loadError) {
      setOrdersError(loadError instanceof Error ? loadError.message : "failed to load table orders");
    } finally {
      setOrdersLoading(false);
    }
  }

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(selectedTableStorageKey, tableId);
    }
  }, [tableId]);

  useEffect(() => {
    let active = true;

    async function loadMenu(): Promise<void> {
      setLoading(true);
      try {
        const response = await fetch(menuEndpoint);
        if (!response.ok) {
          throw new Error(await readErrorMessage(response));
        }
        const payload = (await response.json()) as MenuResponse;
        if (active) {
          setMenu(payload);
          setError(null);
        }
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "unknown error");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadMenu();
    return () => {
      active = false;
    };
  }, [menuEndpoint]);

  useEffect(() => {
    setTableOrders({});
    setOrderResult(null);
    void loadTableOrders();
  }, [tableOrdersEndpoint]);

  useEffect(() => {
    const socket = new WebSocket(wsUrl);
    socket.onopen = () => setConnectionStatus("Connected");
    socket.onclose = () => setConnectionStatus("Disconnected");
    socket.onerror = () => setConnectionStatus("Disconnected");
    socket.onmessage = (event) => {
      try {
        const envelope = JSON.parse(event.data) as EventEnvelope;
        const payload = envelope.payload;
        if (!payload || typeof payload.orderId !== "string") {
          return;
        }
        if (String(payload.tableId ?? "") !== tableId) {
          return;
        }
        mergeOrders([
          {
            orderId: payload.orderId,
            tableId: String(payload.tableId ?? ""),
            status: String(payload.status ?? ""),
            totalMoney: payload.totalMoney as OrderMoney | null | undefined,
            createdAt: String(payload.createdAt ?? ""),
            lines: Array.isArray(payload.lines) ? (payload.lines as OrderLine[]) : [],
          },
        ]);
      } catch {
        // Ignore malformed event payloads.
      }
    };
    return () => socket.close();
  }, [tableId, wsUrl]);

  async function placeTestOrder(): Promise<void> {
    setPlacingOrder(true);
    setOrderResult(null);
    try {
      const response = await fetch(placeOrderEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": buildIdempotencyKey(tableId),
        },
        body: JSON.stringify({ lines: [{ itemId: "itm_001", quantity: 1 }] }),
      });
      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }
      const payload = normalizeOrder((await response.json()) as TableOrder);
      mergeOrders([payload]);
      setOrderResult(`Created order ${payload.orderId} for ${tableId}`);
      await loadTableOrders();
    } catch (placeError) {
      setOrderResult(placeError instanceof Error ? placeError.message : "order failed");
    } finally {
      setPlacingOrder(false);
    }
  }

  const orderedTableOrders = useMemo(
    () =>
      Object.values(tableOrders)
        .filter((order) => order.tableId === tableId)
        .sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime()),
    [tableId, tableOrders]
  );

  if (loading) {
    return (
      <main>
        <p>Loading menu...</p>
      </main>
    );
  }

  if (error) {
    return (
      <main>
        <p>Failed to load menu: {error}</p>
      </main>
    );
  }

  if (!menu) {
    return (
      <main>
        <p>No menu available.</p>
      </main>
    );
  }

  return (
    <main>
      <h1>Restaurant Menu</h1>
      <p>Restaurant: {menu.restaurantId}</p>
      <p>Version: {menu.menuVersion}</p>
      <p>Table updates: {connectionStatus}</p>

      <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 12, flexWrap: "wrap" }}>
        <label htmlFor="table-id-input">Table ID</label>
        <input
          id="table-id-input"
          type="text"
          value={tableId}
          onChange={(event) => setTableId(event.target.value.trim() || "tbl_001")}
        />
        <button type="button" onClick={() => void placeTestOrder()} disabled={placingOrder}>
          {placingOrder ? "Placing..." : "Place test order"}
        </button>
      </div>

      {orderResult ? <p>{orderResult}</p> : null}

      <ul>
        {menu.items.map((item) => (
          <li key={item.itemId}>
            <strong>{item.name}</strong>{" "}
            <span>{formatMenuMoney(item.priceMoney)}</span>
            {!item.isAvailable ? <em> (unavailable)</em> : null}
          </li>
        ))}
      </ul>

      <section>
        <h2>My Table Orders ({tableId})</h2>
        {ordersLoading ? <p>Loading orders...</p> : null}
        {ordersError ? <p>Orders error: {ordersError}</p> : null}
        {!ordersLoading && orderedTableOrders.length === 0 ? <p>No orders yet.</p> : null}
        <ul>
          {orderedTableOrders.map((order) => (
            <li key={order.orderId}>
              <strong>{order.orderId}</strong>{" "}
              <span>{order.status}</span>{" "}
              <span>{formatOrderTotal(getOrderMoney(order))}</span>{" "}
              <span>{formatTimestamp(order.createdAt)}</span>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
