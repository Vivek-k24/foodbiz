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
        if (!payload) {
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

        if (envelope.event_type === "table.opened" && typeof payload.tableId === "string") {
          upsertTableRow({
            tableId: payload.tableId,
            restaurantId: typeof payload.restaurantId === "string" ? payload.restaurantId : "rst_001",
            status: "OPEN",
            openedAt: typeof payload.openedAt === "string" ? payload.openedAt : null,
            closedAt: null,
            lastOrderAt: null,
            totals: { amountCents: 0, currency: "USD" },
            counts: { ordersTotal: 0, placed: 0, accepted: 0, ready: 0 },
          });
          return;
        }

        if (envelope.event_type === "table.closed" && typeof payload.tableId === "string") {
          setTables((current) => {
            const row = current[payload.tableId];
            if (!row) {
              return current;
            }
            return {
              ...current,
              [payload.tableId]: {
                ...row,
                status: "CLOSED",
                closedAt: typeof payload.closedAt === "string" ? payload.closedAt : row.closedAt,
              },
            };
          });
          if (payload.tableId === selectedTableId) {
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
    <main style={{ fontFamily: "sans-serif", padding: 16 }}>
      <h1>Kitchen Dashboard</h1>
      <p>Connection: {connectionStatus}</p>

      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        {(["TABLES", "KITCHEN"] as const).map((label) => (
          <button
            key={label}
            type="button"
            onClick={() => setView(label)}
            style={{
              background: view === label ? "#111827" : "#f3f4f6",
              color: view === label ? "#ffffff" : "#111827",
              border: "1px solid #d1d5db",
              padding: "6px 10px",
              cursor: "pointer",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {view === "KITCHEN" ? (
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
                  cursor: "pointer",
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
            {kitchenQueue.map((order) => {
              const isPending = orderActionPending[order.orderId] === true;
              const errorMessage = orderActionError[order.orderId];

              return (
                <li key={order.orderId} style={{ marginBottom: 14 }}>
                  <div>
                    <strong>{order.orderId}</strong> | table {order.tableId}
                  </div>
                  <div>Status: {order.status}</div>
                  <div>{formatMoneyValue(getOrderMoney(order))}</div>
                  <div>{order.lines.map((line) => `${line.quantity}x ${line.name}`).join(", ")}</div>
                  <div>Created: {formatTimestamp(order.createdAt)}</div>
                  <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
                    {order.status === "PLACED" ? (
                      <button
                        type="button"
                        onClick={() => void handleOrderAction(order, "accept")}
                        disabled={isPending}
                      >
                        {isPending ? "Accepting..." : "Accept"}
                      </button>
                    ) : null}
                    {order.status === "ACCEPTED" ? (
                      <button
                        type="button"
                        onClick={() => void handleOrderAction(order, "ready")}
                        disabled={isPending}
                      >
                        {isPending ? "Updating..." : "Mark Ready"}
                      </button>
                    ) : null}
                  </div>
                  {errorMessage ? <p>{errorMessage}</p> : null}
                </li>
              );
            })}
          </ul>
        </section>
      ) : (
        <section style={{ marginBottom: 24 }}>
          <h2>Tables</h2>
          <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
            {(["OPEN", "CLOSED", "ALL"] as const).map((status) => (
              <button
                key={status}
                type="button"
                onClick={() => setTablesFilter(status)}
                style={{
                  background: tablesFilter === status ? "#111827" : "#f3f4f6",
                  color: tablesFilter === status ? "#ffffff" : "#111827",
                  border: "1px solid #d1d5db",
                  padding: "6px 10px",
                  cursor: "pointer",
                }}
              >
                {status}
              </button>
            ))}
            <button type="button" onClick={() => void loadTables()}>
              Refresh
            </button>
          </div>

          <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
            <input
              type="text"
              value={selectedTableId}
              onChange={(event) => setSelectedTableId(event.target.value.trim() || "tbl_001")}
              placeholder="Table ID"
            />
            <button
              type="button"
              onClick={() => void openTable()}
              disabled={tableActionPending !== null}
            >
              {tableActionPending === "open" ? "Opening..." : "Open Table"}
            </button>
            <button
              type="button"
              onClick={() => void placeTestOrder()}
              disabled={tableActionPending !== null}
            >
              {tableActionPending === "place" ? "Placing..." : "Place Test Order"}
            </button>
            <button
              type="button"
              onClick={() => void closeTable()}
              disabled={tableActionPending !== null}
            >
              {tableActionPending === "close" ? "Closing..." : "Close Table"}
            </button>
          </div>

          {tableActionMessage ? <p>{tableActionMessage}</p> : null}
          {tableActionError ? <p>{tableActionError}</p> : null}
          {tablesLoading ? <p>Loading tables...</p> : null}
          {tablesError ? <p>Tables error: {tablesError}</p> : null}

          <p>Rows: {tablesList.length}</p>
          <ul>
            {tablesList.map((row) => (
              <li
                key={row.tableId}
                style={{
                  marginBottom: 10,
                  padding: 8,
                  border: selectedTableId === row.tableId ? "1px solid #111827" : "1px solid #d1d5db",
                }}
              >
                <button type="button" onClick={() => setSelectedTableId(row.tableId)}>
                  Select
                </button>{" "}
                <strong>{row.tableId}</strong> | {row.status} | opened {formatTimestamp(row.openedAt)} |
                closed {formatTimestamp(row.closedAt)} | last order {formatTimestamp(row.lastOrderAt)} |
                total {formatMoneyValue(row.totals)} | counts: total={row.counts.ordersTotal}, placed=
                {row.counts.placed}, accepted={row.counts.accepted}, ready={row.counts.ready}
              </li>
            ))}
          </ul>

          <section>
            <h2>Selected Table ({selectedTableId})</h2>
            <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
              <button type="button" onClick={() => void refreshSelectedTable()}>
                Reload Table Data
              </button>
            </div>
            {tableOrdersLoading ? <p>Loading table orders...</p> : null}
            {tableOrdersError ? <p>Table orders error: {tableOrdersError}</p> : null}

            <h3>Table Summary</h3>
            {tableSummary ? (
              <div>
                <p>Status: {tableSummary.status}</p>
                <p>Total: {formatMoneyValue(tableSummary.totals)}</p>
                <p>
                  Counts: total={tableSummary.counts.ordersTotal}, placed={tableSummary.counts.placed},
                  accepted={tableSummary.counts.accepted}, ready={tableSummary.counts.ready}
                </p>
                <p>Opened: {formatTimestamp(tableSummary.openedAt)}</p>
                <p>Closed: {formatTimestamp(tableSummary.closedAt)}</p>
                <p>Last order: {formatTimestamp(tableSummary.lastOrderAt)}</p>
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
                  <div>Total: {formatMoneyValue(getOrderMoney(order))}</div>
                  <div>Created: {formatTimestamp(order.createdAt)}</div>
                </li>
              ))}
            </ul>
          </section>
        </section>
      )}
    </main>
  );
}

export default App;
