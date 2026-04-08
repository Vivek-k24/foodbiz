import { useEffect, useMemo, useRef, useState } from "react";

type Money = {
  amountCents?: number | null;
  currency?: string | null;
};

type OrderLineModifier = {
  code: string;
  label: string;
  value: string;
};

type OrderLine = {
  lineId: string;
  itemId: string;
  name: string;
  quantity: number;
  notes?: string | null;
  modifiers?: OrderLineModifier[] | null;
};

type OrderPayload = {
  orderId: string;
  restaurantId?: string;
  locationId?: string;
  tableId?: string | null;
  sessionId?: string | null;
  source?: string;
  status: "PLACED" | "ACCEPTED" | "READY" | string;
  total?: Money | null;
  totalMoney?: Money | null;
  createdAt: string;
  updatedAt?: string;
  lines: OrderLine[];
};

type KitchenQueueResponse = {
  orders: OrderPayload[];
  nextCursor: string | null;
};

type EventEnvelope = {
  event_type: string;
  payload?: unknown;
};

type ApiErrorResponse = {
  error?: {
    code?: string;
    message?: string;
  };
};

type KitchenLane = "PLACED" | "ACCEPTED" | "READY";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";
const restaurantId = "rst_001";
const activeStatuses: KitchenLane[] = ["PLACED", "ACCEPTED", "READY"];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function getString(record: Record<string, unknown>, key: string): string | null {
  const value = record[key];
  return typeof value === "string" ? value : null;
}

function normalizeOrder(order: OrderPayload): OrderPayload {
  return {
    ...order,
    totalMoney: order.totalMoney ?? order.total ?? null,
    lines: Array.isArray(order.lines) ? order.lines : [],
  };
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function formatRelativeAge(value: string): string {
  const createdAt = new Date(value).getTime();
  if (Number.isNaN(createdAt)) {
    return "-";
  }
  const deltaMinutes = Math.max(0, Math.floor((Date.now() - createdAt) / 60000));
  if (deltaMinutes < 1) {
    return "now";
  }
  if (deltaMinutes < 60) {
    return `${deltaMinutes}m`;
  }
  const hours = Math.floor(deltaMinutes / 60);
  const minutes = deltaMinutes % 60;
  return `${hours}h ${minutes}m`;
}

function formatMoney(money: Money | null | undefined): string {
  if (!money || typeof money.amountCents !== "number" || typeof money.currency !== "string") {
    return "-";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: money.currency,
  }).format(money.amountCents / 100);
}

function formatModifier(modifier: OrderLineModifier): string {
  return modifier.value === "true" ? modifier.label : `${modifier.label}: ${modifier.value}`;
}

function getLocationLabel(order: OrderPayload): string {
  if (order.tableId?.trim()) {
    return order.tableId;
  }
  if (order.locationId?.trim()) {
    return order.locationId;
  }
  return "Unknown location";
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
    // Ignore malformed payloads.
  }
  return `request failed (${response.status})`;
}

async function fetchKitchenOrders(status: KitchenLane): Promise<OrderPayload[]> {
  const response = await fetch(
    `${apiBaseUrl}/v1/restaurants/${restaurantId}/kitchen/orders?status=${status}&limit=50`
  );
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  const payload = (await response.json()) as KitchenQueueResponse;
  return payload.orders.map(normalizeOrder);
}

async function advanceOrder(orderId: string, action: "accept" | "ready"): Promise<OrderPayload> {
  const response = await fetch(`${apiBaseUrl}/v1/orders/${encodeURIComponent(orderId)}/${action}`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
  return normalizeOrder((await response.json()) as OrderPayload);
}

function buildOrderFromEvent(rawPayload: unknown): OrderPayload | null {
  if (!isRecord(rawPayload)) {
    return null;
  }
  const orderId = getString(rawPayload, "orderId");
  if (!orderId) {
    return null;
  }
  return normalizeOrder({
    orderId,
    restaurantId: getString(rawPayload, "restaurantId") ?? undefined,
    locationId: getString(rawPayload, "locationId") ?? undefined,
    tableId: getString(rawPayload, "tableId") ?? undefined,
    sessionId: getString(rawPayload, "sessionId") ?? undefined,
    source: getString(rawPayload, "source") ?? undefined,
    status: getString(rawPayload, "status") ?? "PLACED",
    totalMoney: isRecord(rawPayload.totalMoney)
      ? {
          amountCents:
            typeof rawPayload.totalMoney.amountCents === "number"
              ? rawPayload.totalMoney.amountCents
              : null,
          currency:
            typeof rawPayload.totalMoney.currency === "string"
              ? rawPayload.totalMoney.currency
              : null,
        }
      : null,
    total: isRecord(rawPayload.total)
      ? {
          amountCents:
            typeof rawPayload.total.amountCents === "number" ? rawPayload.total.amountCents : null,
          currency: typeof rawPayload.total.currency === "string" ? rawPayload.total.currency : null,
        }
      : null,
    createdAt: getString(rawPayload, "createdAt") ?? "",
    updatedAt: getString(rawPayload, "updatedAt") ?? undefined,
    lines: Array.isArray(rawPayload.lines) ? (rawPayload.lines as OrderLine[]) : [],
  });
}

function App() {
  const [ordersById, setOrdersById] = useState<Record<string, OrderPayload>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState("Connecting");
  const [refreshing, setRefreshing] = useState(false);
  const [actionPending, setActionPending] = useState<Record<string, boolean>>({});
  const [actionError, setActionError] = useState<Record<string, string>>({});
  const ordersRef = useRef(ordersById);

  useEffect(() => {
    ordersRef.current = ordersById;
  }, [ordersById]);

  function mergeOrders(incoming: OrderPayload[]): void {
    setOrdersById((current) => {
      const next = { ...current };
      for (const incomingOrder of incoming) {
        next[incomingOrder.orderId] = normalizeOrder(incomingOrder);
      }
      return next;
    });
  }

  function removeOrder(orderId: string): void {
    setOrdersById((current) => {
      if (!(orderId in current)) {
        return current;
      }
      const next = { ...current };
      delete next[orderId];
      return next;
    });
  }

  async function refreshBoard(): Promise<void> {
    setRefreshing(true);
    setError(null);
    try {
      const payloads = await Promise.all(activeStatuses.map((status) => fetchKitchenOrders(status)));
      const next: Record<string, OrderPayload> = {};
      for (const order of payloads.flat()) {
        next[order.orderId] = order;
      }
      setOrdersById(next);
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "failed to load kitchen orders");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void refreshBoard();
  }, []);

  useEffect(() => {
    const url = new URL("/ws", wsBaseUrl);
    url.searchParams.set("restaurant_id", restaurantId);
    url.searchParams.set("role", "KITCHEN_DISPLAY");

    const socket = new WebSocket(url.toString());
    socket.onopen = () => setConnectionStatus("Connected");
    socket.onclose = () => setConnectionStatus("Disconnected");
    socket.onerror = () => setConnectionStatus("Disconnected");
    socket.onmessage = (event) => {
      try {
        const envelope = JSON.parse(event.data) as EventEnvelope;
        const order = buildOrderFromEvent(envelope.payload);
        if (!order) {
          return;
        }
        if (order.status === "PLACED" || order.status === "ACCEPTED" || order.status === "READY") {
          mergeOrders([order]);
        } else {
          removeOrder(order.orderId);
        }
      } catch {
        // Ignore malformed websocket payloads.
      }
    };

    return () => socket.close();
  }, []);

  async function handleAction(order: OrderPayload, action: "accept" | "ready"): Promise<void> {
    const optimisticStatus = action === "accept" ? "ACCEPTED" : "READY";
    setActionPending((current) => ({ ...current, [order.orderId]: true }));
    setActionError((current) => {
      const next = { ...current };
      delete next[order.orderId];
      return next;
    });
    mergeOrders([{ ...order, status: optimisticStatus }]);

    try {
      const updated = await advanceOrder(order.orderId, action);
      if (updated.status === "PLACED" || updated.status === "ACCEPTED" || updated.status === "READY") {
        mergeOrders([updated]);
      } else {
        removeOrder(updated.orderId);
      }
    } catch (updateError) {
      mergeOrders([order]);
      setActionError((current) => ({
        ...current,
        [order.orderId]: updateError instanceof Error ? updateError.message : "failed to update order",
      }));
      if (updateError instanceof Error && updateError.message.includes("INVALID_ORDER_TRANSITION")) {
        await refreshBoard();
      }
    } finally {
      setActionPending((current) => ({ ...current, [order.orderId]: false }));
    }
  }

  const laneOrders = useMemo(() => {
    const grouped: Record<KitchenLane, OrderPayload[]> = {
      PLACED: [],
      ACCEPTED: [],
      READY: [],
    };

    for (const order of Object.values(ordersById)) {
      if (order.status === "PLACED" || order.status === "ACCEPTED" || order.status === "READY") {
        grouped[order.status].push(order);
      }
    }

    for (const lane of activeStatuses) {
      grouped[lane].sort((left, right) => new Date(left.createdAt).getTime() - new Date(right.createdAt).getTime());
    }

    return grouped;
  }, [ordersById]);

  const totalActive = laneOrders.PLACED.length + laneOrders.ACCEPTED.length + laneOrders.READY.length;

  return (
    <main className="kitchenRoot">
      <header className="topBar">
        <div>
          <p className="eyebrow">Dedicated Kitchen Display</p>
          <h1 className="title">Kitchen Flow Board</h1>
          <p className="subtitle">
            This surface owns prep progression only. Accept and Ready stay here instead of leaking into
            host or service console workflows.
          </p>
        </div>
        <div className="topBarActions">
          <span className={connectionStatus === "Connected" ? "badge badgeLive" : "badge badgeMuted"}>
            {connectionStatus}
          </span>
          <button type="button" className="primaryButton" onClick={() => void refreshBoard()} disabled={refreshing}>
            {refreshing ? "Refreshing..." : "Refresh Queue"}
          </button>
        </div>
      </header>

      <section className="summaryRow">
        <div className="summaryCard">
          <span className="summaryLabel">Placed</span>
          <strong>{laneOrders.PLACED.length}</strong>
        </div>
        <div className="summaryCard">
          <span className="summaryLabel">Accepted</span>
          <strong>{laneOrders.ACCEPTED.length}</strong>
        </div>
        <div className="summaryCard">
          <span className="summaryLabel">Ready</span>
          <strong>{laneOrders.READY.length}</strong>
        </div>
        <div className="summaryCard">
          <span className="summaryLabel">Active total</span>
          <strong>{totalActive}</strong>
        </div>
      </section>

      {error ? <div className="errorBox">{error}</div> : null}

      <section className="laneGrid">
        {activeStatuses.map((lane) => (
          <section key={lane} className={`lane lane${lane}`}>
            <div className="laneHeader">
              <div>
                <p className="eyebrow">{lane === "PLACED" ? "Incoming" : lane === "ACCEPTED" ? "In Progress" : "Pickup / Handoff"}</p>
                <h2 className="laneTitle">{lane}</h2>
              </div>
              <span className="badge">{laneOrders[lane].length}</span>
            </div>

            <div className="laneScroll">
              {loading && laneOrders[lane].length === 0 ? <div className="infoBox">Loading {lane.toLowerCase()} orders...</div> : null}
              {!loading && laneOrders[lane].length === 0 ? (
                <div className="emptyState">No {lane.toLowerCase()} orders right now.</div>
              ) : null}

              <div className="cardStack">
                {laneOrders[lane].map((order) => {
                  const pending = actionPending[order.orderId] === true;
                  const laneAction = lane === "PLACED" ? "accept" : lane === "ACCEPTED" ? "ready" : null;
                  const laneLabel = lane === "PLACED" ? "Accept" : lane === "ACCEPTED" ? "Mark Ready" : null;

                  return (
                    <article key={order.orderId} className={`orderCard orderCard${lane}`}>
                      <div className="cardHeader">
                        <div>
                          <div className="orderId">{order.orderId}</div>
                          <p className="metaLine">{getLocationLabel(order)}</p>
                        </div>
                        <div className="metaGroup">
                          <span className={`statusChip statusChip${lane}`}>{order.status}</span>
                          <span className="ageChip">{formatRelativeAge(order.createdAt)}</span>
                        </div>
                      </div>

                      <div className="metaRow mutedText">
                        <span>Created {formatTimestamp(order.createdAt)}</span>
                        <span>Total {formatMoney(order.totalMoney ?? order.total)}</span>
                      </div>

                      <ul className="lineList">
                        {order.lines.map((line) => (
                          <li key={line.lineId} className="lineItem">
                            <div>
                              <span className="monoLine">{line.quantity}x</span> {line.name}
                            </div>
                            {Array.isArray(line.modifiers) && line.modifiers.length > 0 ? (
                              <div className="chipRow">
                                {line.modifiers.map((modifier) => (
                                  <span
                                    key={`${line.lineId}-${modifier.code}-${modifier.value}`}
                                    className="miniChip"
                                  >
                                    {formatModifier(modifier)}
                                  </span>
                                ))}
                              </div>
                            ) : null}
                            {typeof line.notes === "string" && line.notes.trim() ? (
                              <p className="mutedText">Notes: {line.notes}</p>
                            ) : null}
                          </li>
                        ))}
                      </ul>

                      {laneAction && laneLabel ? (
                        <button
                          type="button"
                          className="secondaryButton"
                          disabled={pending}
                          onClick={() => void handleAction(order, laneAction)}
                        >
                          {pending ? "Updating..." : laneLabel}
                        </button>
                      ) : null}

                      {actionError[order.orderId] ? <div className="errorBox">{actionError[order.orderId]}</div> : null}
                    </article>
                  );
                })}
              </div>
            </div>
          </section>
        ))}
      </section>
    </main>
  );
}

export default App;
