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

const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";

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

  const wsUrl = useMemo(
    () => `${wsBaseUrl}/ws?restaurant_id=rst_001&role=KITCHEN`,
    []
  );

  const queue = useMemo(
    () =>
      Object.values(orders).sort(
        (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      ),
    [orders]
  );

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
