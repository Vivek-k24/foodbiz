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

function getOrderStatusChipClass(status: string): string {
  switch (status) {
    case "PLACED":
      return "chip chipPlaced";
    case "ACCEPTED":
      return "chip chipAccepted";
    case "READY":
      return "chip chipReady";
    default:
      return "chip";
  }
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
    () => `${apiBaseUrl}/v1/restaurants/rst_001/tables/${encodeURIComponent(tableId)}/orders`,
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

  const orderResultIsError = orderResult !== null && !orderResult.startsWith("Created order ");

  if (loading) {
    return (
      <main className="container">
        <section className="card">
          <div className="cardBody">
            <div className="infoBox">Loading menu…</div>
          </div>
        </section>
      </main>
    );
  }

  if (error) {
    return (
      <main className="container">
        <section className="card">
          <div className="cardBody">
            <div className="errorBox">Failed to load menu: {error}</div>
          </div>
        </section>
      </main>
    );
  }

  if (!menu) {
    return (
      <main className="container">
        <section className="card">
          <div className="cardBody">
            <div className="emptyState">No menu available.</div>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="container">
      <header className="header">
        <div>
          <p className="eyebrow">Restaurant Operating Platform</p>
          <h1 className="title">Restaurant Menu</h1>
          <p className="subtitle">
            Live ordering view for <span className="mono">{menu.restaurantId}</span> using menu version <span className="mono">v{menu.menuVersion}</span>.
          </p>
        </div>
        <div className={connectionStatus === "Connected" ? "badge badgeStrong" : "badge badgeMuted"}>
          {connectionStatus}
        </div>
      </header>

      <section className="card">
        <div className="cardHeader">
          <div>
            <h2 className="sectionTitle">Table Controls</h2>
            <p className="hint">Choose a table, keep it in local storage, and place a test order against the seeded menu.</p>
          </div>
          <span className="badge mono">{tableId}</span>
        </div>
        <div className="cardBody">
          <div className="controlGrid">
            <div className="fieldGroup">
              <label className="label" htmlFor="table-id-input">
                Table ID
              </label>
              <input
                id="table-id-input"
                className="input mono"
                type="text"
                value={tableId}
                onChange={(event) => setTableId(event.target.value.trim() || "tbl_001")}
              />
            </div>
            <div className="fieldGroup">
              <span className="label">Quick Action</span>
              <button type="button" className="btn btnPrimary" onClick={() => void placeTestOrder()} disabled={placingOrder}>
                {placingOrder ? "Placing…" : "Place Test Order"}
              </button>
            </div>
          </div>

          <p className="hint">The quick action posts a single line item for <span className="mono">itm_001</span> using a fresh idempotency key.</p>

          {orderResult ? (
            <div className={orderResultIsError ? "errorBox" : "infoBox"}>{orderResult}</div>
          ) : null}
        </div>
      </section>

      <div className="pageGrid">
        <section className="card">
          <div className="cardHeader">
            <div>
              <h2 className="sectionTitle">Menu</h2>
              <p className="hint">Available menu items are rendered as a responsive card grid for quick scanning.</p>
            </div>
            <span className="badge">{menu.items.length} items</span>
          </div>
          <div className="cardBody">
            <div className="menuGrid">
              {menu.items.map((item) => (
                <article key={item.itemId} className="menuCard">
                  <div className="rowHeader">
                    <div>
                      <h3 className="subheading">{item.name}</h3>
                      <p className="muted mono">{item.itemId}</p>
                    </div>
                    <span className={item.isAvailable ? "chip chipPlaced" : "chip chipClosed"}>
                      {item.isAvailable ? "Available" : "Unavailable"}
                    </span>
                  </div>
                  <p className="menuPrice">{formatMenuMoney(item.priceMoney)}</p>
                  <p className="rowBody">{item.description?.trim() || "No description provided."}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="card">
          <div className="cardHeader">
            <div>
              <h2 className="sectionTitle">My Table Orders</h2>
              <p className="hint">Hydrated from REST for <span className="mono">{tableId}</span>, then kept current from websocket events.</p>
            </div>
            <span className="badge">{orderedTableOrders.length} orders</span>
          </div>
          <div className="cardBody">
            {ordersLoading ? <div className="infoBox">Loading orders…</div> : null}
            {ordersError ? <div className="errorBox">{ordersError}</div> : null}
            {!ordersLoading && orderedTableOrders.length === 0 ? (
              <div className="emptyState">No orders yet for this table.</div>
            ) : null}

            <div className="listStack">
              {orderedTableOrders.map((order) => (
                <article key={order.orderId} className="row">
                  <div className="rowHeader">
                    <div>
                      <div className="rowTitle mono">{order.orderId}</div>
                      <p className="muted">Created {formatTimestamp(order.createdAt)}</p>
                    </div>
                    <span className={getOrderStatusChipClass(order.status)}>{order.status}</span>
                  </div>
                  <div className="statsGrid">
                    <div className="statCard">
                      <div className="statLabel">Total</div>
                      <div className="statValue">{formatOrderTotal(getOrderMoney(order))}</div>
                    </div>
                    <div className="statCard">
                      <div className="statLabel">Lines</div>
                      <div className="statValue">{order.lines.length}</div>
                    </div>
                  </div>
                  <div className="divider" />
                  <p className="rowBody">
                    {order.lines.length > 0
                      ? order.lines.map((line) => `${line.quantity}x ${line.name}`).join(", ")
                      : "No line items available."}
                  </p>
                </article>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
