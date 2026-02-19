import { useEffect, useMemo, useState } from "react";

type MoneyPayload = {
  amountCents?: number;
  currency?: string;
};

type OrderLinePayload = {
  lineId: string;
  itemId: string;
  name: string;
  quantity: number;
};

type OrderPayload = {
  orderId: string;
  tableId: string;
  status: string;
  totalMoney?: MoneyPayload | null;
  createdAt: string;
  lines: OrderLinePayload[];
};

type EventEnvelope = {
  event_type: string;
  payload?: Record<string, unknown>;
};

type KitchenQueueResponse = {
  orders: OrderPayload[];
  nextCursor: string | null;
};

type TableOrdersResponse = {
  orders: OrderPayload[];
  nextCursor: string | null;
};

type TableSummaryResponse = {
  tableId: string;
  restaurantId: string;
  status: string;
  openedAt: string | null;
  closedAt: string | null;
  totals: {
    amountCents: number;
    currency: string;
  };
  counts: {
    ordersTotal: number;
    placed: number;
    accepted: number;
    ready: number;
  };
  lastOrderAt: string | null;
};

type StatusTab = "PLACED" | "ACCEPTED" | "READY";

const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function formatMoney(amountCents: number, currency: string): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(amountCents / 100);
}

function formatTime(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleTimeString();
}

function formatOrderTotal(total: MoneyPayload | null | undefined): string {
  if (!total || typeof total.amountCents !== "number" || !total.currency) {
    return "-";
  }
  return formatMoney(total.amountCents, total.currency);
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { error?: { message?: string } };
    if (payload.error?.message) {
      return payload.error.message;
    }
  } catch {
    // ignore parsing errors
  }
  return `request failed (${response.status})`;
}

function App() {
  const [orders, setOrders] = useState<Record<string, OrderPayload>>({});
  const [connectionStatus, setConnectionStatus] = useState("Connecting");
  const [activeStatus, setActiveStatus] = useState<StatusTab>("PLACED");
  const [loadingQueue, setLoadingQueue] = useState(false);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [tableId, setTableId] = useState("tbl_001");
  const [tableOrdersLoading, setTableOrdersLoading] = useState(false);
  const [tableOrdersError, setTableOrdersError] = useState<string | null>(null);
  const [tableSummary, setTableSummary] = useState<TableSummaryResponse | null>(null);
  const [tableActionMessage, setTableActionMessage] = useState<string | null>(null);

  const kitchenQueueEndpoint = useMemo(
    () => `${apiBaseUrl}/v1/restaurants/rst_001/kitchen/orders`,
    []
  );

  const tableOrdersEndpoint = useMemo(
    () =>
      `${apiBaseUrl}/v1/restaurants/rst_001/tables/${encodeURIComponent(tableId)}/orders`,
    [tableId]
  );

  const tableSummaryEndpoint = useMemo(
    () =>
      `${apiBaseUrl}/v1/restaurants/rst_001/tables/${encodeURIComponent(tableId)}/summary`,
    [tableId]
  );

  const tableCloseEndpoint = useMemo(
    () => `${apiBaseUrl}/v1/restaurants/rst_001/tables/${encodeURIComponent(tableId)}/close`,
    [tableId]
  );

  const wsUrl = useMemo(() => {
    const url = new URL("/ws", wsBaseUrl);
    url.searchParams.set("restaurant_id", "rst_001");
    url.searchParams.set("role", "KITCHEN");
    return url.toString();
  }, []);

  function mergeOrders(incoming: OrderPayload[]): void {
    setOrders((current) => {
      const next = { ...current };
      for (const order of incoming) {
        if (!order.orderId) {
          continue;
        }
        next[order.orderId] = order;
      }
      return next;
    });
  }

  async function loadKitchenQueue(status: StatusTab): Promise<void> {
    setLoadingQueue(true);
    setQueueError(null);
    try {
      const response = await fetch(`${kitchenQueueEndpoint}?status=${status}&limit=50`);
      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }
      const payload = (await response.json()) as KitchenQueueResponse;
      mergeOrders(payload.orders);
    } catch (err) {
      setQueueError(err instanceof Error ? err.message : "failed to load kitchen queue");
    } finally {
      setLoadingQueue(false);
    }
  }

  async function loadTableOrders(): Promise<void> {
    setTableOrdersLoading(true);
    setTableOrdersError(null);
    try {
      const response = await fetch(`${tableOrdersEndpoint}?status=ALL&limit=50`);
      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }
      const payload = (await response.json()) as TableOrdersResponse;
      mergeOrders(payload.orders);
    } catch (err) {
      setTableOrdersError(err instanceof Error ? err.message : "failed to load table orders");
    } finally {
      setTableOrdersLoading(false);
    }
  }

  async function loadTableSummary(): Promise<void> {
    try {
      const response = await fetch(tableSummaryEndpoint);
      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }
      const payload = (await response.json()) as TableSummaryResponse;
      setTableSummary(payload);
    } catch (err) {
      setTableSummary(null);
      setTableActionMessage(err instanceof Error ? err.message : "failed to load table summary");
    }
  }

  async function closeTable(): Promise<void> {
    setTableActionMessage(null);
    const response = await fetch(tableCloseEndpoint, { method: "POST" });
    if (!response.ok) {
      setTableActionMessage(await readErrorMessage(response));
      return;
    }
    setTableActionMessage(`Closed table ${tableId}`);
    await loadTableSummary();
  }

  const kitchenQueue = useMemo(
    () =>
      Object.values(orders)
        .filter((order) => order.status === activeStatus)
        .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()),
    [activeStatus, orders]
  );

  const selectedTableOrders = useMemo(
    () =>
      Object.values(orders)
        .filter((order) => order.tableId === tableId)
        .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()),
    [orders, tableId]
  );

  useEffect(() => {
    void loadKitchenQueue(activeStatus);
  }, [activeStatus, kitchenQueueEndpoint]);

  useEffect(() => {
    setTableActionMessage(null);
    void loadTableOrders();
    void loadTableSummary();
  }, [tableId, tableOrdersEndpoint, tableSummaryEndpoint]);

  useEffect(() => {
    const socket = new WebSocket(wsUrl);
    socket.onopen = () => setConnectionStatus("Connected");
    socket.onclose = () => setConnectionStatus("Disconnected");
    socket.onerror = () => setConnectionStatus("Disconnected");
    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as EventEnvelope;
        const payload = parsed.payload as Record<string, unknown> | undefined;
        if (payload && typeof payload.orderId === "string") {
          mergeOrders([
            {
              orderId: payload.orderId,
              tableId: String(payload.tableId ?? ""),
              status: String(payload.status ?? ""),
              totalMoney: payload.totalMoney as MoneyPayload | null | undefined,
              createdAt: String(payload.createdAt ?? ""),
              lines: Array.isArray(payload.lines) ? (payload.lines as OrderLinePayload[]) : []
            }
          ]);
          return;
        }
        if (
          parsed.event_type === "table.closed" &&
          payload &&
          String(payload.tableId ?? "") === tableId
        ) {
          setTableActionMessage(`Table ${tableId} closed`);
          void loadTableSummary();
        }
      } catch {
        // Ignore malformed or unsupported events.
      }
    };
    return () => socket.close();
  }, [wsUrl, tableId]);

  return (
    <main style={{ fontFamily: "sans-serif", padding: 16 }}>
      <h1>Kitchen Dashboard</h1>
      <p>Connection: {connectionStatus}</p>

      <section style={{ marginBottom: 24 }}>
        <h2>Kitchen Queue</h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          {(["PLACED", "ACCEPTED", "READY"] as const).map((status) => (
            <button
              key={status}
              type="button"
              onClick={() => setActiveStatus(status)}
              style={{
                background: activeStatus === status ? "#111827" : "#f3f4f6",
                color: activeStatus === status ? "#ffffff" : "#111827",
                border: "1px solid #d1d5db",
                padding: "6px 10px",
                cursor: "pointer"
              }}
            >
              {status}
            </button>
          ))}
        </div>
        <p>{activeStatus} orders: {kitchenQueue.length}</p>
        {loadingQueue ? <p>Loading queue...</p> : null}
        {queueError ? <p>Queue error: {queueError}</p> : null}
        <ul>
          {kitchenQueue.map((order) => (
            <li key={order.orderId} style={{ marginBottom: 12 }}>
              <div>
                <strong>{order.orderId}</strong> | table {order.tableId}
              </div>
              <div>Status: {order.status}</div>
              <div>{formatOrderTotal(order.totalMoney)}</div>
              <div>{order.lines.map((line) => `${line.quantity}x ${line.name}`).join(", ")}</div>
              <div>Created: {formatTime(order.createdAt)}</div>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2>Table Debug View</h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <input
            type="text"
            value={tableId}
            onChange={(event) => setTableId(event.target.value.trim() || "tbl_001")}
            placeholder="Table ID"
          />
          <button type="button" onClick={() => void loadTableOrders()}>
            Load Table Orders
          </button>
          <button type="button" onClick={() => void closeTable()}>
            Close Table
          </button>
        </div>
        {tableActionMessage ? <p>{tableActionMessage}</p> : null}
        {tableOrdersLoading ? <p>Loading table orders...</p> : null}
        {tableOrdersError ? <p>Table orders error: {tableOrdersError}</p> : null}

        <h3>Table Summary</h3>
        {tableSummary ? (
          <div>
            <p>Status: {tableSummary.status}</p>
            <p>
              Total: {formatMoney(tableSummary.totals.amountCents, tableSummary.totals.currency)}
            </p>
            <p>
              Counts: total={tableSummary.counts.ordersTotal}, placed={tableSummary.counts.placed},
              accepted={tableSummary.counts.accepted}, ready={tableSummary.counts.ready}
            </p>
            <p>Opened: {formatTime(tableSummary.openedAt)}</p>
            <p>Closed: {formatTime(tableSummary.closedAt)}</p>
            <p>Last order: {formatTime(tableSummary.lastOrderAt)}</p>
          </div>
        ) : (
          <p>No table summary available.</p>
        )}

        <h3>Table Orders ({selectedTableOrders.length})</h3>
        <ul>
          {selectedTableOrders.map((order) => (
            <li key={order.orderId} style={{ marginBottom: 10 }}>
              <div>
                <strong>{order.orderId}</strong>
              </div>
              <div>Status: {order.status}</div>
              <div>Total: {formatOrderTotal(order.totalMoney)}</div>
              <div>Created: {formatTime(order.createdAt)}</div>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}

export default App;
