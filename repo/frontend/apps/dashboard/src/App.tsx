import { useEffect, useMemo, useState } from "react";

type OrderLinePayload = {
  lineId: string;
  itemId: string;
  name: string;
  quantity: number;
};

type OrderPlacedPayload = {
  orderId: string;
  tableId: string;
  totalMoney: {
    amountCents: number;
    currency: string;
  };
  createdAt: string;
  lines: OrderLinePayload[];
};

type EventEnvelope = {
  event_type: string;
  payload: OrderPlacedPayload;
};

const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";

function formatMoney(amountCents: number, currency: string): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(amountCents / 100);
}

function App() {
  const [orders, setOrders] = useState<OrderPlacedPayload[]>([]);
  const [status, setStatus] = useState("connecting");

  const wsUrl = useMemo(
    () => `${wsBaseUrl}/ws?restaurant_id=rst_001&role=KITCHEN`,
    []
  );

  useEffect(() => {
    const socket = new WebSocket(wsUrl);
    socket.onopen = () => setStatus("connected");
    socket.onclose = () => setStatus("disconnected");
    socket.onerror = () => setStatus("error");
    socket.onmessage = (event) => {
      const parsed = JSON.parse(event.data) as EventEnvelope;
      if (parsed.event_type === "order.placed") {
        setOrders((prev) => [parsed.payload, ...prev]);
      }
    };
    return () => socket.close();
  }, [wsUrl]);

  return (
    <main style={{ fontFamily: "sans-serif", padding: 16 }}>
      <h1>Kitchen Dashboard</h1>
      <p>WebSocket status: {status}</p>
      <ul>
        {orders.map((order) => (
          <li key={order.orderId} style={{ marginBottom: 12 }}>
            <div><strong>{order.orderId}</strong> | table {order.tableId}</div>
            <div>{formatMoney(order.totalMoney.amountCents, order.totalMoney.currency)}</div>
            <div>{order.lines.map((line) => `${line.quantity}x ${line.name}`).join(", ")}</div>
          </li>
        ))}
      </ul>
    </main>
  );
}

export default App;
