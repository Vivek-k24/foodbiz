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

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";

function formatMoney(money: Money): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: money.currency
  }).format(money.amountCents / 100);
}

function formatOrderTotal(total: OrderMoney | null | undefined): string {
  if (!total || typeof total.amountCents !== "number" || typeof total.currency !== "string") {
    return "-";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: total.currency
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

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { error?: { message?: string } };
    if (payload.error?.message) {
      return payload.error.message;
    }
  } catch {
    // ignore parsing issues
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
  const tableId = "tbl_001";

  const menuEndpoint = useMemo(
    () => `${apiBaseUrl}/v1/restaurants/rst_001/menu`,
    []
  );
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
      for (const order of incoming) {
        if (!order.orderId || order.tableId !== tableId) {
          continue;
        }
        next[order.orderId] = order;
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
    } catch (err) {
      setOrdersError(err instanceof Error ? err.message : "failed to load table orders");
    } finally {
      setOrdersLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    async function loadMenu() {
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
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "unknown error");
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
        const payload = envelope.payload as Record<string, unknown> | undefined;
        if (!payload || typeof payload.orderId !== "string") {
          return;
        }
        mergeOrders([
          {
            orderId: payload.orderId,
            tableId: String(payload.tableId ?? ""),
            status: String(payload.status ?? ""),
            totalMoney: payload.totalMoney as OrderMoney | null | undefined,
            createdAt: String(payload.createdAt ?? ""),
            lines: Array.isArray(payload.lines) ? (payload.lines as OrderLine[]) : []
          }
        ]);
      } catch {
        // Ignore malformed event payloads.
      }
    };
    return () => socket.close();
  }, [wsUrl, tableId]);

  async function placeTestOrder(): Promise<void> {
    setPlacingOrder(true);
    setOrderResult(null);
    try {
      const response = await fetch(placeOrderEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lines: [{ itemId: "itm_001", quantity: 1 }] })
      });
      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }
      const payload = (await response.json()) as { orderId?: string };
      setOrderResult(`Created order ${payload.orderId}`);
      await loadTableOrders();
    } catch (err) {
      setOrderResult(err instanceof Error ? err.message : "order failed");
    } finally {
      setPlacingOrder(false);
    }
  }

  const orderedTableOrders = useMemo(
    () =>
      Object.values(tableOrders)
        .filter((order) => order.tableId === tableId)
        .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()),
    [tableOrders, tableId]
  );

  if (loading) {
    return <main><p>Loading menu...</p></main>;
  }
  if (error) {
    return <main><p>Failed to load menu: {error}</p></main>;
  }
  if (!menu) {
    return <main><p>No menu available.</p></main>;
  }

  return (
    <main>
      <h1>Restaurant Menu</h1>
      <p>Restaurant: {menu.restaurantId}</p>
      <p>Version: {menu.menuVersion}</p>
      <p>Table updates: {connectionStatus}</p>
      <button type="button" onClick={() => void placeTestOrder()} disabled={placingOrder}>
        {placingOrder ? "Placing..." : "Place test order"}
      </button>
      {orderResult ? <p>{orderResult}</p> : null}
      <ul>
        {menu.items.map((item) => (
          <li key={item.itemId}>
            <strong>{item.name}</strong>{" "}
            <span>{formatMoney(item.priceMoney)}</span>
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
              <span>{formatOrderTotal(order.totalMoney)}</span>{" "}
              <span>{formatTimestamp(order.createdAt)}</span>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
