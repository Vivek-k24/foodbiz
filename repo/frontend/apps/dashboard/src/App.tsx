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

type TableRegistryItem = {
  tableId: string;
  restaurantId: string;
  status: string;
  openedAt: string | null;
  closedAt: string | null;
  lastOrderAt: string | null;
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
};

type TableRegistryResponse = {
  tables: TableRegistryItem[];
  nextCursor: string | null;
};

type StatusTab = "PLACED" | "ACCEPTED" | "READY";
type TablesFilter = "ALL" | "OPEN" | "CLOSED";
type DashboardView = "KITCHEN" | "TABLES";

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
  const [tables, setTables] = useState<Record<string, TableRegistryItem>>({});
  const [connectionStatus, setConnectionStatus] = useState("Connecting");
  const [activeStatus, setActiveStatus] = useState<StatusTab>("PLACED");
  const [view, setView] = useState<DashboardView>("TABLES");
  const [tablesFilter, setTablesFilter] = useState<TablesFilter>("OPEN");
  const [loadingQueue, setLoadingQueue] = useState(false);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [tablesLoading, setTablesLoading] = useState(false);
  const [tablesError, setTablesError] = useState<string | null>(null);
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
      for (const order of incoming) {
        if (!order.orderId) {
          continue;
        }
        next[order.orderId] = order;
      }
      return next;
    });
  }

  function upsertTableRow(incoming: TableRegistryItem): void {
    setTables((current) => ({ ...current, [incoming.tableId]: incoming }));
  }

  async function loadTables(): Promise<void> {
    setTablesLoading(true);
    setTablesError(null);
    try {
      const response = await fetch(tablesEndpoint);
      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }
      const payload = (await response.json()) as TableRegistryResponse;
      setTables(() => {
        const next: Record<string, TableRegistryItem> = {};
        for (const row of payload.tables) {
          next[row.tableId] = row;
        }
        return next;
      });
    } catch (err) {
      setTablesError(err instanceof Error ? err.message : "failed to load tables");
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
            counts: payload.counts
          }
        };
      });
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

  const tablesList = useMemo(
    () =>
      Object.values(tables).sort((a, b) => {
        const left = a.openedAt ? new Date(a.openedAt).getTime() : 0;
        const right = b.openedAt ? new Date(b.openedAt).getTime() : 0;
        if (left !== right) {
          return right - left;
        }
        return b.tableId.localeCompare(a.tableId);
      }),
    [tables]
  );

  useEffect(() => {
    void loadKitchenQueue(activeStatus);
  }, [activeStatus, kitchenQueueEndpoint]);

  useEffect(() => {
    void loadTables();
  }, [tablesEndpoint]);

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
          const payloadTableId = String(payload.tableId ?? "");
          const payloadCreatedAt = String(payload.createdAt ?? "");
          mergeOrders([
            {
              orderId: payload.orderId,
              tableId: payloadTableId,
              status: String(payload.status ?? ""),
              totalMoney: payload.totalMoney as MoneyPayload | null | undefined,
              createdAt: payloadCreatedAt,
              lines: Array.isArray(payload.lines) ? (payload.lines as OrderLinePayload[]) : []
            }
          ]);
          if (payloadTableId) {
            setTables((current) => {
              const row = current[payloadTableId];
              if (!row) {
                return current;
              }
              return {
                ...current,
                [payloadTableId]: {
                  ...row,
                  lastOrderAt: payloadCreatedAt || row.lastOrderAt
                }
              };
            });
          }
          return;
        }
        if (
          parsed.event_type === "table.opened" &&
          payload &&
          typeof payload.tableId === "string"
        ) {
          upsertTableRow({
            tableId: payload.tableId,
            restaurantId: String(payload.restaurantId ?? "rst_001"),
            status: "OPEN",
            openedAt: String(payload.openedAt ?? ""),
            closedAt: null,
            lastOrderAt: null,
            totals: { amountCents: 0, currency: "USD" },
            counts: { ordersTotal: 0, placed: 0, accepted: 0, ready: 0 }
          });
          if (tablesFilter === "OPEN" || tablesFilter === "ALL") {
            void loadTables();
          }
          return;
        }
        if (
          parsed.event_type === "table.closed" &&
          payload &&
          typeof payload.tableId === "string"
        ) {
          const payloadTableId = payload.tableId;
          setTables((current) => {
            const row = current[payloadTableId];
            if (!row) {
              return current;
            }
            return {
              ...current,
              [payloadTableId]: {
                ...row,
                status: "CLOSED",
                closedAt: String(payload.closedAt ?? row.closedAt)
              }
            };
          });
          if (payloadTableId === tableId) {
            setTableActionMessage(`Table ${tableId} closed`);
            void loadTableSummary();
          }
          if (tablesFilter === "CLOSED" || tablesFilter === "ALL") {
            void loadTables();
          }
        }
      } catch {
        // Ignore malformed or unsupported events.
      }
    };
    return () => socket.close();
  }, [tableId, tablesFilter, wsUrl]);

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
              cursor: "pointer"
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
      ) : (
        <section style={{ marginBottom: 24 }}>
          <h2>Tables</h2>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
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
                  cursor: "pointer"
                }}
              >
                {status}
              </button>
            ))}
            <button type="button" onClick={() => void loadTables()}>
              Refresh
            </button>
          </div>
          {tablesLoading ? <p>Loading tables...</p> : null}
          {tablesError ? <p>Tables error: {tablesError}</p> : null}
          <p>Rows: {tablesList.length}</p>
          <ul>
            {tablesList.map((row) => (
              <li key={row.tableId} style={{ marginBottom: 10 }}>
                <button
                  type="button"
                  onClick={() => setTableId(row.tableId)}
                  style={{ cursor: "pointer" }}
                >
                  Select
                </button>{" "}
                <strong>{row.tableId}</strong> | {row.status} | opened {formatTime(row.openedAt)} |
                closed {formatTime(row.closedAt)} | last order {formatTime(row.lastOrderAt)} |
                total {formatMoney(row.totals.amountCents, row.totals.currency)} | counts:
                total={row.counts.ordersTotal}, placed={row.counts.placed}, accepted=
                {row.counts.accepted}, ready={row.counts.ready}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <h2>Selected Table ({tableId})</h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <button type="button" onClick={() => void loadTableOrders()}>
            Reload Table Orders
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
