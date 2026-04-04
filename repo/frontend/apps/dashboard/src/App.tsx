import { useEffect, useMemo, useState } from "react";

type MoneyPayload = {
  amountCents?: number | null;
  currency?: string | null;
};

type OrderLinePayload = {
  lineId: string;
  itemId: string;
  name: string;
  quantity: number;
};

type OrderPayload = {
  orderId: string;
  restaurantId?: string;
  tableId: string;
  status: string;
  total?: MoneyPayload | null;
  totalMoney?: MoneyPayload | null;
  createdAt: string;
  lines: OrderLinePayload[];
};

type EventEnvelope = {
  event_type: string;
  payload?: unknown;
};

type TableOpenedPayload = {
  tableId: string;
  restaurantId?: string;
  openedAt?: string;
};

type TableClosedPayload = {
  tableId: string;
  closedAt?: string;
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
  totals: MoneyPayload;
  counts: {
    ordersTotal: number;
    placed: number;
    accepted: number;
    ready: number;
  };
  lastOrderAt: string | null;
};

type TableRegistryItem = {
  tableId: string;
  restaurantId: string;
  status: string;
  openedAt: string | null;
  closedAt: string | null;
  lastOrderAt: string | null;
  totals: MoneyPayload;
  counts: {
    ordersTotal: number;
    placed: number;
    accepted: number;
    ready: number;
  };
};

type TableRegistryResponse = {
  tables: TableRegistryItem[];
  nextCursor: string | null;
};

type ApiErrorResponse = {
  error?: {
    code?: string;
    message?: string;
  };
};

type ApiError = {
  code: string | null;
  message: string;
};

type StatusTab = "PLACED" | "ACCEPTED" | "READY";
type TablesFilter = "ALL" | "OPEN" | "CLOSED";
type DashboardView = "KITCHEN" | "TABLES";
type TableAction = "open" | "place" | "close" | null;

const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

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

function formatMoneyValue(money: MoneyPayload | null | undefined): string {
  if (!money || typeof money.amountCents !== "number" || typeof money.currency !== "string") {
    return "-";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: money.currency,
  }).format(money.amountCents / 100);
}

function getOrderMoney(order: OrderPayload): MoneyPayload | null | undefined {
  return order.totalMoney ?? order.total;
}

function normalizeOrder(order: OrderPayload): OrderPayload {
  return {
    ...order,
    lines: Array.isArray(order.lines) ? order.lines : [],
    totalMoney: order.totalMoney ?? order.total ?? null,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function getString(record: Record<string, unknown>, key: string): string | null {
  const value = record[key];
  return typeof value === "string" ? value : null;
}

function getTableIdFromPayload(payload: unknown): string | null {
  if (!isRecord(payload)) {
    return null;
  }
  return getString(payload, "tableId");
}

function buildOrderFromEvent(payload: Record<string, unknown>): OrderPayload | null {
  if (typeof payload.orderId !== "string") {
    return null;
  }
  return normalizeOrder({
    orderId: payload.orderId,
    restaurantId: typeof payload.restaurantId === "string" ? payload.restaurantId : undefined,
    tableId: typeof payload.tableId === "string" ? payload.tableId : "",
    status: typeof payload.status === "string" ? payload.status : "",
    totalMoney: payload.totalMoney as MoneyPayload | null | undefined,
    createdAt: typeof payload.createdAt === "string" ? payload.createdAt : "",
    lines: Array.isArray(payload.lines) ? (payload.lines as OrderLinePayload[]) : [],
  });
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

function formatApiError(error: ApiError): string {
  return error.code ? `${error.code}: ${error.message}` : error.message;
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

function getTableStatusChipClass(status: string): string {
  return status === "OPEN" ? "chip chipOpen" : "chip chipClosed";
}

async function readApiError(response: Response): Promise<ApiError> {
  try {
    const payload = (await response.json()) as ApiErrorResponse;
    if (payload.error?.message) {
      return {
        code: payload.error.code ?? null,
        message: payload.error.message,
      };
    }
  } catch {
    // Ignore malformed error payloads.
  }
  return {
    code: null,
    message: `request failed (${response.status})`,
  };
}

function App() {
  const [orders, setOrders] = useState<Record<string, OrderPayload>>({});
  const [tables, setTables] = useState<Record<string, TableRegistryItem>>({});
  const [connectionStatus, setConnectionStatus] = useState("Connecting");
  const [view, setView] = useState<DashboardView>("TABLES");
  const [activeStatus, setActiveStatus] = useState<StatusTab>("PLACED");
  const [tablesFilter, setTablesFilter] = useState<TablesFilter>("OPEN");
  const [selectedTableId, setSelectedTableId] = useState("tbl_001");
  const [loadingQueue, setLoadingQueue] = useState(false);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [tablesLoading, setTablesLoading] = useState(false);
  const [tablesError, setTablesError] = useState<string | null>(null);
  const [tableOrdersLoading, setTableOrdersLoading] = useState(false);
  const [tableOrdersError, setTableOrdersError] = useState<string | null>(null);
  const [tableSummary, setTableSummary] = useState<TableSummaryResponse | null>(null);
  const [tableActionPending, setTableActionPending] = useState<TableAction>(null);
  const [tableActionError, setTableActionError] = useState<string | null>(null);
  const [tableActionMessage, setTableActionMessage] = useState<string | null>(null);
  const [orderActionPending, setOrderActionPending] = useState<Record<string, boolean>>({});
  const [orderActionError, setOrderActionError] = useState<Record<string, string>>({});

  const kitchenQueueEndpoint = useMemo(
    () => `${apiBaseUrl}/v1/restaurants/rst_001/kitchen/orders`,
    []
  );
  const tableOrdersEndpoint = useMemo(
    () =>
      `${apiBaseUrl}/v1/restaurants/rst_001/tables/${encodeURIComponent(selectedTableId)}/orders`,
    [selectedTableId]
  );
  const tableSummaryEndpoint = useMemo(
    () =>
      `${apiBaseUrl}/v1/restaurants/rst_001/tables/${encodeURIComponent(selectedTableId)}/summary`,
    [selectedTableId]
  );
  const tableOpenEndpoint = useMemo(
    () => `${apiBaseUrl}/v1/restaurants/rst_001/tables/${encodeURIComponent(selectedTableId)}/open`,
    [selectedTableId]
  );
  const tableCloseEndpoint = useMemo(
    () =>
      `${apiBaseUrl}/v1/restaurants/rst_001/tables/${encodeURIComponent(selectedTableId)}/close`,
    [selectedTableId]
  );
  const placeOrderEndpoint = useMemo(
    () =>
      `${apiBaseUrl}/v1/restaurants/rst_001/tables/${encodeURIComponent(selectedTableId)}/orders`,
    [selectedTableId]
  );
  const tablesEndpoint = useMemo(
    () =>
      `${apiBaseUrl}/v1/restaurants/rst_001/tables?status=${encodeURIComponent(tablesFilter)}&limit=50`,
    [tablesFilter]
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
      for (const incomingOrder of incoming) {
        if (!incomingOrder.orderId) {
          continue;
        }
        next[incomingOrder.orderId] = normalizeOrder(incomingOrder);
      }
      return next;
    });
  }

  function updateOrder(
    orderId: string,
    updater: (order: OrderPayload) => OrderPayload
  ): void {
    setOrders((current) => {
      const existing = current[orderId];
      if (!existing) {
        return current;
      }
      return {
        ...current,
        [orderId]: normalizeOrder(updater(existing)),
      };
    });
  }

  function upsertTableRow(incoming: TableRegistryItem): void {
    setTables((current) => ({
      ...current,
      [incoming.tableId]: incoming,
    }));
  }

  async function loadTables(): Promise<void> {
    setTablesLoading(true);
    setTablesError(null);
    try {
      const response = await fetch(tablesEndpoint);
      if (!response.ok) {
        throw new Error(formatApiError(await readApiError(response)));
      }
      const payload = (await response.json()) as TableRegistryResponse;
      setTables(() => {
        const next: Record<string, TableRegistryItem> = {};
        for (const row of payload.tables) {
          next[row.tableId] = row;
        }
        return next;
      });
    } catch (error) {
      setTablesError(error instanceof Error ? error.message : "failed to load tables");
    } finally {
      setTablesLoading(false);
    }
  }

  async function loadKitchenQueue(status: StatusTab): Promise<void> {
    setLoadingQueue(true);
    setQueueError(null);
    try {
      const response = await fetch(`${kitchenQueueEndpoint}?status=${status}&limit=50`);
      if (!response.ok) {
        throw new Error(formatApiError(await readApiError(response)));
      }
      const payload = (await response.json()) as KitchenQueueResponse;
      mergeOrders(payload.orders);
    } catch (error) {
      setQueueError(error instanceof Error ? error.message : "failed to load kitchen queue");
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
        throw new Error(formatApiError(await readApiError(response)));
      }
      const payload = (await response.json()) as TableOrdersResponse;
      mergeOrders(payload.orders);
    } catch (error) {
      setTableOrdersError(error instanceof Error ? error.message : "failed to load table orders");
    } finally {
      setTableOrdersLoading(false);
    }
  }

  async function loadTableSummary(): Promise<void> {
    try {
      const response = await fetch(tableSummaryEndpoint);
      if (!response.ok) {
        throw new Error(formatApiError(await readApiError(response)));
      }
      const payload = (await response.json()) as TableSummaryResponse;
      setTableSummary(payload);
      setTables((current) => {
        const row = current[payload.tableId];
        if (!row) {
          return current;
        }
        return {
          ...current,
          [payload.tableId]: {
            ...row,
            status: payload.status,
            openedAt: payload.openedAt,
            closedAt: payload.closedAt,
            lastOrderAt: payload.lastOrderAt,
            totals: payload.totals,
            counts: payload.counts,
          },
        };
      });
    } catch {
      setTableSummary(null);
    }
  }

  async function refreshSelectedTable(): Promise<void> {
    await Promise.all([loadTableOrders(), loadTableSummary()]);
  }
  async function handleOrderAction(
    order: OrderPayload,
    action: "accept" | "ready"
  ): Promise<void> {
    const nextStatus = action === "accept" ? "ACCEPTED" : "READY";
    const previousStatus = order.status;

    setOrderActionPending((current) => ({ ...current, [order.orderId]: true }));
    setOrderActionError((current) => {
      const next = { ...current };
      delete next[order.orderId];
      return next;
    });
    updateOrder(order.orderId, (current) => ({ ...current, status: nextStatus }));

    try {
      const response = await fetch(`${apiBaseUrl}/v1/orders/${order.orderId}/${action}`, {
        method: "POST",
      });
      if (!response.ok) {
        const apiError = await readApiError(response);
        updateOrder(order.orderId, (current) => ({ ...current, status: previousStatus }));
        setOrderActionError((current) => ({
          ...current,
          [order.orderId]: formatApiError(apiError),
        }));
        if (apiError.code === "INVALID_ORDER_TRANSITION" || apiError.code === "CONFLICT") {
          await loadKitchenQueue(activeStatus);
          if (order.tableId === selectedTableId) {
            await refreshSelectedTable();
          }
        }
        return;
      }

      const payload = (await response.json()) as OrderPayload;
      mergeOrders([payload]);
      if (order.tableId === selectedTableId) {
        void loadTableSummary();
      }
      void loadTables();
    } finally {
      setOrderActionPending((current) => ({ ...current, [order.orderId]: false }));
    }
  }

  async function openTable(): Promise<void> {
    setTableActionPending("open");
    setTableActionError(null);
    setTableActionMessage(null);
    try {
      const response = await fetch(tableOpenEndpoint, { method: "POST" });
      if (!response.ok) {
        setTableActionError(formatApiError(await readApiError(response)));
        return;
      }
      setTableActionMessage(`Opened table ${selectedTableId}`);
      await Promise.all([loadTables(), refreshSelectedTable()]);
    } finally {
      setTableActionPending(null);
    }
  }

  async function placeTestOrder(): Promise<void> {
    setTableActionPending("place");
    setTableActionError(null);
    setTableActionMessage(null);
    try {
      const response = await fetch(placeOrderEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": buildIdempotencyKey(selectedTableId),
        },
        body: JSON.stringify({
          lines: [{ itemId: "itm_001", quantity: 1 }],
        }),
      });
      if (!response.ok) {
        setTableActionError(formatApiError(await readApiError(response)));
        return;
      }
      const payload = (await response.json()) as OrderPayload;
      mergeOrders([payload]);
      setTableActionMessage(`Placed test order for ${selectedTableId}`);
      await Promise.all([refreshSelectedTable(), loadTables()]);
    } finally {
      setTableActionPending(null);
    }
  }

  async function closeTable(): Promise<void> {
    setTableActionPending("close");
    setTableActionError(null);
    setTableActionMessage(null);
    try {
      const response = await fetch(tableCloseEndpoint, { method: "POST" });
      if (!response.ok) {
        setTableActionError(formatApiError(await readApiError(response)));
        return;
      }
      setTableActionMessage(`Closed table ${selectedTableId}`);
      await Promise.all([loadTables(), refreshSelectedTable()]);
    } finally {
      setTableActionPending(null);
    }
  }

  const kitchenQueue = useMemo(
    () =>
      Object.values(orders)
        .filter((order) => order.status === activeStatus)
        .sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime()),
    [activeStatus, orders]
  );

  const selectedTableOrders = useMemo(
    () =>
      Object.values(orders)
        .filter((order) => order.tableId === selectedTableId)
        .sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime()),
    [orders, selectedTableId]
  );

  const tablesList = useMemo(
    () =>
      Object.values(tables)
        .filter((row) => tablesFilter === "ALL" || row.status === tablesFilter)
        .sort((left, right) => {
          const leftOpened = left.openedAt ? new Date(left.openedAt).getTime() : 0;
          const rightOpened = right.openedAt ? new Date(right.openedAt).getTime() : 0;
          if (leftOpened !== rightOpened) {
            return rightOpened - leftOpened;
          }
          return right.tableId.localeCompare(left.tableId);
        }),
    [tables, tablesFilter]
  );

  useEffect(() => {
    void loadKitchenQueue(activeStatus);
  }, [activeStatus, kitchenQueueEndpoint]);

  useEffect(() => {
    void loadTables();
  }, [tablesEndpoint]);

  useEffect(() => {
    setTableActionError(null);
    setTableActionMessage(null);
    void refreshSelectedTable();
  }, [selectedTableId, tableOrdersEndpoint, tableSummaryEndpoint]);

  useEffect(() => {
    const socket = new WebSocket(wsUrl);
    socket.onopen = () => setConnectionStatus("Connected");
    socket.onclose = () => setConnectionStatus("Disconnected");
    socket.onerror = () => setConnectionStatus("Disconnected");
    socket.onmessage = (event) => {
      try {
        const envelope = JSON.parse(event.data) as EventEnvelope;
        const payload = envelope.payload;
        if (!isRecord(payload)) {
          return;
        }

        const order = buildOrderFromEvent(payload);
        if (order) {
          mergeOrders([order]);
          if (order.tableId === selectedTableId) {
            void loadTableSummary();
          }
          if (order.tableId) {
            setTables((current) => {
              const row = current[order.tableId];
              if (!row) {
                return current;
              }
              return {
                ...current,
                [order.tableId]: {
                  ...row,
                  lastOrderAt: order.createdAt || row.lastOrderAt,
                },
              };
            });
          }
          return;
        }

        const eventTableId = getTableIdFromPayload(payload);
        if (envelope.event_type === "table.opened" && eventTableId) {
          const openedPayload = payload as TableOpenedPayload;
          upsertTableRow({
            tableId: eventTableId,
            restaurantId:
              typeof openedPayload.restaurantId === "string"
                ? openedPayload.restaurantId
                : "rst_001",
            status: "OPEN",
            openedAt:
              typeof openedPayload.openedAt === "string" ? openedPayload.openedAt : null,
            closedAt: null,
            lastOrderAt: null,
            totals: { amountCents: 0, currency: "USD" },
            counts: { ordersTotal: 0, placed: 0, accepted: 0, ready: 0 },
          });
          return;
        }

        if (envelope.event_type === "table.closed" && eventTableId) {
          const closedPayload = payload as TableClosedPayload;
          setTables((current) => {
            const row = current[eventTableId];
            if (!row) {
              return current;
            }
            return {
              ...current,
              [eventTableId]: {
                ...row,
                status: "CLOSED",
                closedAt:
                  typeof closedPayload.closedAt === "string"
                    ? closedPayload.closedAt
                    : row.closedAt,
              },
            };
          });
          if (eventTableId === selectedTableId) {
            void loadTableSummary();
          }
        }
      } catch {
        // Ignore malformed or unsupported events.
      }
    };
    return () => socket.close();
  }, [selectedTableId, wsUrl]);
  return (
    <main className="container">
      <header className="header">
        <div>
          <p className="eyebrow">Restaurant Operating Platform</p>
          <h1 className="title">Kitchen Dashboard</h1>
          <p className="subtitle">
            Live kitchen queue, table registry, and table drill-down for <span className="mono">rst_001</span>.
          </p>
        </div>
        <div className={connectionStatus === "Connected" ? "badge badgeStrong" : "badge badgeMuted"}>
          {connectionStatus}
        </div>
      </header>

      <nav className="tabs" aria-label="Dashboard views">
        {(["TABLES", "KITCHEN"] as const).map((label) => (
          <button
            key={label}
            type="button"
            className={`tab ${view === label ? "tabActive" : ""}`}
            onClick={() => setView(label)}
          >
            {label}
          </button>
        ))}
      </nav>

      {view === "KITCHEN" ? (
        <section className="card">
          <div className="cardHeader">
            <div>
              <h2 className="sectionTitle">Kitchen Queue</h2>
              <p className="hint">Track the active queue and progress orders without leaving the dashboard.</p>
            </div>
            <div className="badge">{kitchenQueue.length} visible</div>
          </div>
          <div className="cardBody">
            <div className="tabs" aria-label="Kitchen status filters">
              {(["PLACED", "ACCEPTED", "READY"] as const).map((status) => (
                <button
                  key={status}
                  type="button"
                  className={`tab ${activeStatus === status ? "tabActive" : ""}`}
                  onClick={() => setActiveStatus(status)}
                >
                  {status}
                </button>
              ))}
            </div>

            {loadingQueue ? <div className="infoBox">Loading queue…</div> : null}
            {queueError ? <div className="errorBox">{queueError}</div> : null}

            {kitchenQueue.length === 0 && !loadingQueue ? (
              <div className="emptyState">No {activeStatus.toLowerCase()} orders are in the queue.</div>
            ) : null}

            <div className="listStack">
              {kitchenQueue.map((order) => {
                const isPending = orderActionPending[order.orderId] === true;
                const errorMessage = orderActionError[order.orderId];

                return (
                  <article key={order.orderId} className="row">
                    <div className="rowHeader">
                      <div>
                        <div className="rowTitle mono">{order.orderId}</div>
                        <p className="muted">
                          Table <span className="mono">{order.tableId}</span>
                        </p>
                      </div>
                      <span className={getOrderStatusChipClass(order.status)}>{order.status}</span>
                    </div>

                    <div className="statsGrid">
                      <div className="statCard">
                        <div className="statLabel">Total</div>
                        <div className="statValue">{formatMoneyValue(getOrderMoney(order))}</div>
                      </div>
                      <div className="statCard">
                        <div className="statLabel">Created</div>
                        <div className="statValue">{formatTimestamp(order.createdAt)}</div>
                      </div>
                    </div>

                    <div className="divider" />

                    <p className="rowBody">
                      {order.lines.length > 0
                        ? order.lines.map((line) => `${line.quantity}x ${line.name}`).join(", ")
                        : "No line items available."}
                    </p>

                    <div className="rowActions">
                      {order.status === "PLACED" ? (
                        <button
                          type="button"
                          className="btn btnPrimary btnSmall"
                          onClick={() => void handleOrderAction(order, "accept")}
                          disabled={isPending}
                        >
                          {isPending ? "Accepting…" : "Accept"}
                        </button>
                      ) : null}
                      {order.status === "ACCEPTED" ? (
                        <button
                          type="button"
                          className="btn btnSecondary btnSmall"
                          onClick={() => void handleOrderAction(order, "ready")}
                          disabled={isPending}
                        >
                          {isPending ? "Updating…" : "Mark Ready"}
                        </button>
                      ) : null}
                    </div>

                    {errorMessage ? <div className="errorBox">{errorMessage}</div> : null}
                  </article>
                );
              })}
            </div>
          </div>
        </section>
      ) : (
        <section className="pageStack">
          <section className="card">
            <div className="cardHeader">
              <div>
                <h2 className="sectionTitle">Restaurant Tables</h2>
                <p className="hint">Hydrate from REST, then keep the registry live from websocket events.</p>
              </div>
              <div className="badge">{tablesList.length} rows</div>
            </div>
            <div className="cardBody">
              <div className="toolbar">
                <div className="tabs" aria-label="Table status filters">
                  {(["OPEN", "CLOSED", "ALL"] as const).map((status) => (
                    <button
                      key={status}
                      type="button"
                      className={`tab ${tablesFilter === status ? "tabActive" : ""}`}
                      onClick={() => setTablesFilter(status)}
                    >
                      {status}
                    </button>
                  ))}
                </div>
                <button type="button" className="btn btnSecondary btnSmall" onClick={() => void loadTables()}>
                  Refresh
                </button>
              </div>

              {tablesLoading ? <div className="infoBox">Loading tables…</div> : null}
              {tablesError ? <div className="errorBox">{tablesError}</div> : null}
            </div>
          </section>

          <div className="layoutGrid">
            <section className="card">
              <div className="cardHeader">
                <div>
                  <h2 className="sectionTitle">Tables List</h2>
                  <p className="hint">Select a table to inspect orders, totals, and workflow actions.</p>
                </div>
              </div>
              <div className="cardBody">
                {tablesList.length === 0 && !tablesLoading ? (
                  <div className="emptyState">No tables match the current filter.</div>
                ) : null}

                <div className="listStack">
                  {tablesList.map((row) => (
                    <button
                      key={row.tableId}
                      type="button"
                      className={`row rowSelectable ${selectedTableId === row.tableId ? "rowSelected" : ""}`}
                      onClick={() => setSelectedTableId(row.tableId)}
                    >
                      <div className="rowHeader">
                        <div>
                          <div className="rowTitle mono">{row.tableId}</div>
                          <p className="muted">
                            Restaurant <span className="mono">{row.restaurantId}</span>
                          </p>
                        </div>
                        <span className={getTableStatusChipClass(row.status)}>{row.status}</span>
                      </div>

                      <div className="statsGrid">
                        <div className="statCard">
                          <div className="statLabel">Total</div>
                          <div className="statValue">{formatMoneyValue(row.totals)}</div>
                        </div>
                        <div className="statCard">
                          <div className="statLabel">Orders</div>
                          <div className="statValue">{row.counts.ordersTotal}</div>
                        </div>
                        <div className="statCard">
                          <div className="statLabel">Opened</div>
                          <div className="statValue">{formatTimestamp(row.openedAt)}</div>
                        </div>
                        <div className="statCard">
                          <div className="statLabel">Last Order</div>
                          <div className="statValue">{formatTimestamp(row.lastOrderAt)}</div>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </section>
            <section className="card">
              <div className="cardHeader">
                <div>
                  <h2 className="sectionTitle">Selected Table</h2>
                  <p className="hint">
                    Drive the order history view and quick actions from <span className="mono">{selectedTableId}</span>.
                  </p>
                </div>
                <span className="badge mono">{selectedTableId}</span>
              </div>
              <div className="cardBody">
                <div className="fieldRow">
                  <div className="fieldGroup">
                    <label className="label" htmlFor="dashboard-table-id">
                      Table ID
                    </label>
                    <input
                      id="dashboard-table-id"
                      className="input mono"
                      type="text"
                      value={selectedTableId}
                      onChange={(event) =>
                        setSelectedTableId(event.target.value.trim() || "tbl_001")
                      }
                      placeholder="tbl_001"
                    />
                  </div>
                </div>

                <div className="actionsBar">
                  <button
                    type="button"
                    className="btn btnPrimary"
                    onClick={() => void openTable()}
                    disabled={tableActionPending !== null}
                  >
                    {tableActionPending === "open" ? "Opening…" : "Open Table"}
                  </button>
                  <button
                    type="button"
                    className="btn btnSecondary"
                    onClick={() => void placeTestOrder()}
                    disabled={tableActionPending !== null}
                  >
                    {tableActionPending === "place" ? "Placing…" : "Place Test Order"}
                  </button>
                  <button
                    type="button"
                    className="btn btnDanger"
                    onClick={() => void closeTable()}
                    disabled={tableActionPending !== null}
                  >
                    {tableActionPending === "close" ? "Closing…" : "Close Table"}
                  </button>
                  <button
                    type="button"
                    className="btn btnSecondary"
                    onClick={() => void refreshSelectedTable()}
                  >
                    Reload Table Data
                  </button>
                </div>

                {tableActionMessage ? <div className="infoBox">{tableActionMessage}</div> : null}
                {tableActionError ? <div className="errorBox">{tableActionError}</div> : null}
                {tableOrdersLoading ? <div className="infoBox">Loading table orders…</div> : null}
                {tableOrdersError ? <div className="errorBox">{tableOrdersError}</div> : null}

                <div className="divider" />

                <h3 className="subheading">Summary</h3>
                {tableSummary ? (
                  <div className="statsGrid">
                    <div className="statCard">
                      <div className="statLabel">Status</div>
                      <div className="statValue">
                        <span className={getTableStatusChipClass(tableSummary.status)}>
                          {tableSummary.status}
                        </span>
                      </div>
                    </div>
                    <div className="statCard">
                      <div className="statLabel">Total</div>
                      <div className="statValue">{formatMoneyValue(tableSummary.totals)}</div>
                    </div>
                    <div className="statCard">
                      <div className="statLabel">Orders</div>
                      <div className="statValue">{tableSummary.counts.ordersTotal}</div>
                    </div>
                    <div className="statCard">
                      <div className="statLabel">Placed / Accepted / Ready</div>
                      <div className="statValue">
                        {tableSummary.counts.placed} / {tableSummary.counts.accepted} / {tableSummary.counts.ready}
                      </div>
                    </div>
                    <div className="statCard">
                      <div className="statLabel">Opened</div>
                      <div className="statValue">{formatTimestamp(tableSummary.openedAt)}</div>
                    </div>
                    <div className="statCard">
                      <div className="statLabel">Closed</div>
                      <div className="statValue">{formatTimestamp(tableSummary.closedAt)}</div>
                    </div>
                    <div className="statCard">
                      <div className="statLabel">Last Order</div>
                      <div className="statValue">{formatTimestamp(tableSummary.lastOrderAt)}</div>
                    </div>
                  </div>
                ) : (
                  <div className="emptyState">No table summary available.</div>
                )}

                <div className="divider" />

                <div className="sectionHeader">
                  <h3 className="subheading">Table Orders</h3>
                  <span className="badge">{selectedTableOrders.length} orders</span>
                </div>

                {selectedTableOrders.length === 0 && !tableOrdersLoading ? (
                  <div className="emptyState">No orders loaded for this table.</div>
                ) : null}

                <div className="listStack">
                  {selectedTableOrders.map((order) => (
                    <article key={order.orderId} className="row">
                      <div className="rowHeader">
                        <div>
                          <div className="rowTitle mono">{order.orderId}</div>
                          <p className="muted">Created {formatTimestamp(order.createdAt)}</p>
                        </div>
                        <span className={getOrderStatusChipClass(order.status)}>{order.status}</span>
                      </div>
                      <div className="rowMeta">
                        <span>Total {formatMoneyValue(getOrderMoney(order))}</span>
                        <span>
                          {order.lines.length > 0
                            ? order.lines.map((line) => `${line.quantity}x ${line.name}`).join(", ")
                            : "No line items available."}
                        </span>
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            </section>
          </div>
        </section>
      )}
    </main>
  );
}

export default App;
