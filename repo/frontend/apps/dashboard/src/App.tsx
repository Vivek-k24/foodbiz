import { useEffect, useMemo, useState } from "react";

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
  totalMoney: {
    amountCents: number;
    currency: string;
  };
  createdAt: string;
  lines: OrderLinePayload[];
};

type EventEnvelope = {
  event_type: string;
  payload: OrderPayload;
};

type KitchenQueueResponse = {
  orders: OrderPayload[];
  nextCursor: string | null;
};

type StatusTab = "PLACED" | "ACCEPTED" | "READY";

const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function formatMoney(amountCents: number, currency: string): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(amountCents / 100);
}

function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleTimeString();
}

function App() {
  const [orders, setOrders] = useState<Record<string, OrderPayload>>({});
  const [connectionStatus, setConnectionStatus] = useState("Connecting");
  const [activeStatus, setActiveStatus] = useState<StatusTab>("PLACED");
  const [loadingQueue, setLoadingQueue] = useState(false);
  const [queueError, setQueueError] = useState<string | null>(null);

  const queueEndpoint = useMemo(
    () => `${apiBaseUrl}/v1/restaurants/rst_001/kitchen/orders`,
    []
  );

  const wsUrl = useMemo(
    () => `${wsBaseUrl}/ws?restaurant_id=rst_001&role=KITCHEN`,
    []
  );

  const queue = useMemo(
    () =>
      Object.values(orders)
        .filter((order) => order.status === activeStatus)
        .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()),
    [activeStatus, orders]
  );

  useEffect(() => {
    let active = true;
    async function hydrateQueue() {
      setLoadingQueue(true);
      setQueueError(null);
      try {
        const response = await fetch(`${queueEndpoint}?status=${activeStatus}&limit=50`);
        if (!response.ok) {
          throw new Error(`queue request failed (${response.status})`);
        }
        const payload = (await response.json()) as KitchenQueueResponse;
        if (!active) {
          return;
        }
        setOrders((current) => {
          const next = { ...current };
          for (const order of payload.orders) {
            next[order.orderId] = order;
          }
          return next;
        });
      } catch (err) {
        if (active) {
          setQueueError(err instanceof Error ? err.message : "failed to load queue");
        }
      } finally {
        if (active) {
          setLoadingQueue(false);
        }
      }
    }
    void hydrateQueue();
    return () => {
      active = false;
    };
  }, [activeStatus, queueEndpoint]);

  useEffect(() => {
    const socket = new WebSocket(wsUrl);
    socket.onopen = () => setConnectionStatus("Connected");
    socket.onclose = () => setConnectionStatus("Disconnected");
    socket.onerror = () => setConnectionStatus("Disconnected");
    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as EventEnvelope;
        if (!parsed.payload?.orderId) {
          return;
        }
        setOrders((current) => ({
          ...current,
          [parsed.payload.orderId]: parsed.payload,
        }));
      } catch {
        // Ignore malformed events from non-order channels.
      }
    };
    return () => socket.close();
  }, [wsUrl]);

  return (
    <main style={{ fontFamily: "sans-serif", padding: 16 }}>
      <h1>Kitchen Dashboard</h1>
      <p>Connection: {connectionStatus}</p>
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
      <p>{activeStatus} orders: {queue.length}</p>
      {loadingQueue ? <p>Loading queue...</p> : null}
      {queueError ? <p>Queue error: {queueError}</p> : null}
      <ul>
        {queue.map((order) => (
          <li key={order.orderId} style={{ marginBottom: 12 }}>
            <div>
              <strong>{order.orderId}</strong> | table {order.tableId}
            </div>
            <div>Status: {order.status}</div>
            <div>{formatMoney(order.totalMoney.amountCents, order.totalMoney.currency)}</div>
            <div>{order.lines.map((line) => `${line.quantity}x ${line.name}`).join(", ")}</div>
            <div>Created: {formatTime(order.createdAt)}</div>
          </li>
        ))}
      </ul>
    </main>
  );
}

export default App;
