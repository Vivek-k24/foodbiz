import { useEffect, useMemo, useState } from "react";

type Money = {
  amountCents: number;
  currency: string;
};

type AllowedModifier = {
  code: string;
  label: string;
  kind: "toggle" | "choice" | "text";
  options?: string[] | null;
};

type MenuItem = {
  itemId: string;
  name: string;
  description?: string | null;
  priceMoney: Money;
  isAvailable: boolean;
  categoryId?: string | null;
  allowedModifiers?: AllowedModifier[] | null;
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

type CartLine = {
  cartLineId: string;
  item: MenuItem;
  quantity: number;
  notes: string;
  modifierValues: Record<string, string>;
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
    case "SERVED":
      return "chip chipServed";
    case "SETTLED":
      return "chip chipSettled";
    default:
      return "chip";
  }
}

function formatModifierValue(modifier: OrderLineModifier): string {
  return modifier.value === "true" ? modifier.label : `${modifier.label}: ${modifier.value}`;
}

function buildCartLineId(): string {
  return `cart_${Math.random().toString(36).slice(2, 10)}`;
}

function buildInitialModifierValues(item: MenuItem): Record<string, string> {
  const values: Record<string, string> = {};
  for (const modifier of item.allowedModifiers ?? []) {
    if (modifier.kind === "choice" && Array.isArray(modifier.options) && modifier.options.length > 0) {
      values[modifier.code] = modifier.options[0];
    }
  }
  return values;
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
  const [cart, setCart] = useState<CartLine[]>([]);
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
      `${apiBaseUrl}/v1/restaurants/rst_001/tables/${encodeURIComponent(
        tableId
      )}/orders?status=ALL&limit=50`,
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

  function updateCartLine(
    cartLineId: string,
    updater: (line: CartLine) => CartLine
  ): void {
    setCart((current) =>
      current.map((line) => (line.cartLineId === cartLineId ? updater(line) : line))
    );
  }

  function removeCartLine(cartLineId: string): void {
    setCart((current) => current.filter((line) => line.cartLineId !== cartLineId));
  }

  function addItemToCart(item: MenuItem): void {
    if (!item.isAvailable) {
      return;
    }
    setCart((current) => [
      ...current,
      {
        cartLineId: buildCartLineId(),
        item,
        quantity: 1,
        notes: "",
        modifierValues: buildInitialModifierValues(item),
      },
    ]);
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

  async function submitOrder(): Promise<void> {
    if (cart.length === 0) {
      return;
    }

    setPlacingOrder(true);
    setOrderResult(null);
    try {
      const response = await fetch(placeOrderEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": buildIdempotencyKey(tableId),
        },
        body: JSON.stringify({
          lines: cart.map((line) => ({
            itemId: line.item.itemId,
            quantity: line.quantity,
            notes: line.notes.trim() || null,
            modifiers:
              (line.item.allowedModifiers ?? [])
                .map((modifier) => {
                  const value = line.modifierValues[modifier.code] ?? "";
                  if (modifier.kind === "toggle") {
                    return value === "true"
                      ? { code: modifier.code, label: modifier.label, value: "true" }
                      : null;
                  }
                  if (modifier.kind === "text") {
                    return value.trim()
                      ? { code: modifier.code, label: modifier.label, value: value.trim() }
                      : null;
                  }
                  return value
                    ? { code: modifier.code, label: modifier.label, value }
                    : null;
                })
                .filter((modifier): modifier is { code: string; label: string; value: string } => modifier !== null)
                || null,
          })),
        }),
      });
      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }
      const payload = normalizeOrder((await response.json()) as TableOrder);
      mergeOrders([payload]);
      setCart([]);
      setOrderResult(`Created order ${payload.orderId} for ${tableId}`);
      await loadTableOrders();
    } catch (placeError) {
      setOrderResult(placeError instanceof Error ? placeError.message : "order failed");
    } finally {
      setPlacingOrder(false);
    }
  }

  const foodItems = useMemo(
    () =>
      (menu?.items ?? [])
        .filter((item) => !item.itemId.startsWith("drink_"))
        .sort((left, right) => left.itemId.localeCompare(right.itemId)),
    [menu]
  );
  const drinkItems = useMemo(
    () =>
      (menu?.items ?? [])
        .filter((item) => item.itemId.startsWith("drink_"))
        .sort((left, right) => left.itemId.localeCompare(right.itemId)),
    [menu]
  );
  const orderedTableOrders = useMemo(
    () =>
      Object.values(tableOrders)
        .filter((order) => order.tableId === tableId)
        .sort(
          (left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime()
        ),
    [tableId, tableOrders]
  );
  const cartTotal = useMemo(
    () =>
      cart.reduce(
        (total, line) => total + line.item.priceMoney.amountCents * line.quantity,
        0
      ),
    [cart]
  );
  const orderResultIsError = orderResult !== null && !orderResult.startsWith("Created order ");

  if (loading) {
    return (
      <main className="container">
        <section className="card">
          <div className="cardBody">
            <div className="infoBox">Loading menu...</div>
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
          <h1 className="title">Italian Ordering Demo</h1>
          <p className="subtitle">
            Browse <span className="mono">{menu.items.length}</span> seeded items, build a cart,
            and place an order for table <span className="mono">{tableId}</span>.
          </p>
        </div>
        <div className={connectionStatus === "Connected" ? "badge badgeStrong" : "badge badgeMuted"}>
          {connectionStatus}
        </div>
      </header>

      <section className="card">
        <div className="cardHeader">
          <div>
            <h2 className="sectionTitle">Ordering Controls</h2>
            <p className="hint">The selected table is stored locally and reused after refresh.</p>
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
              <span className="label">Cart Summary</span>
              <div className="summaryBar">
                <span>{cart.length} lines</span>
                <span>{formatMenuMoney({ amountCents: cartTotal, currency: "USD" })}</span>
              </div>
            </div>
          </div>

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
              <p className="hint">Food and drinks render separately, and each card carries item-specific modifier controls into the cart.</p>
            </div>
            <span className="badge">{menu.items.length} items</span>
          </div>
          <div className="cardBody sectionStack">
            <section>
              <div className="sectionHeader">
                <h3 className="subheading">Food</h3>
                <span className="badge">{foodItems.length}</span>
              </div>
              <div className="menuGrid">
                {foodItems.map((item) => (
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
                    <div className="divider" />
                    <button
                      type="button"
                      className="btn btnPrimary"
                      onClick={() => addItemToCart(item)}
                      disabled={!item.isAvailable}
                    >
                      Add to Cart
                    </button>
                  </article>
                ))}
              </div>
            </section>

            <section>
              <div className="sectionHeader">
                <h3 className="subheading">Drinks</h3>
                <span className="badge">{drinkItems.length}</span>
              </div>
              <div className="menuGrid">
                {drinkItems.map((item) => (
                  <article key={item.itemId} className="menuCard">
                    <div className="rowHeader">
                      <div>
                        <h3 className="subheading">{item.name}</h3>
                        <p className="muted mono">{item.itemId}</p>
                      </div>
                      <span className={item.isAvailable ? "chip chipAccepted" : "chip chipClosed"}>
                        {item.isAvailable ? "Available" : "Unavailable"}
                      </span>
                    </div>
                    <p className="menuPrice">{formatMenuMoney(item.priceMoney)}</p>
                    <p className="rowBody">{item.description?.trim() || "No description provided."}</p>
                    <div className="divider" />
                    <button
                      type="button"
                      className="btn btnPrimary"
                      onClick={() => addItemToCart(item)}
                      disabled={!item.isAvailable}
                    >
                      Add to Cart
                    </button>
                  </article>
                ))}
              </div>
            </section>
          </div>
        </section>

        <section className="sidebarStack">
          <section className="card">
            <div className="cardHeader">
              <div>
                <h2 className="sectionTitle">Cart</h2>
                <p className="hint">Each cart line keeps its own quantity, notes, and item-specific modifiers.</p>
              </div>
              <span className="badge">{cart.length} lines</span>
            </div>
            <div className="cardBody">
              {cart.length === 0 ? <div className="emptyState">Add food or drinks to start an order.</div> : null}

              <div className="listStack">
                {cart.map((line) => (
                  <article key={line.cartLineId} className="cartLine">
                    <div className="rowHeader">
                      <div>
                        <div className="rowTitle">{line.item.name}</div>
                        <p className="muted mono">{line.item.itemId}</p>
                      </div>
                      <span className="badge">{formatMenuMoney(line.item.priceMoney)}</span>
                    </div>

                    <div className="cartQuantityRow">
                      <span className="label">Quantity</span>
                      <div className="quantityControls">
                        <button
                          type="button"
                          className="btn btnSecondary btnSmall"
                          onClick={() =>
                            updateCartLine(line.cartLineId, (current) => ({
                              ...current,
                              quantity: Math.max(1, current.quantity - 1),
                            }))
                          }
                        >
                          -
                        </button>
                        <span className="quantityValue mono">{line.quantity}</span>
                        <button
                          type="button"
                          className="btn btnSecondary btnSmall"
                          onClick={() =>
                            updateCartLine(line.cartLineId, (current) => ({
                              ...current,
                              quantity: current.quantity + 1,
                            }))
                          }
                        >
                          +
                        </button>
                        <button
                          type="button"
                          className="btn btnSecondary btnSmall"
                          onClick={() => removeCartLine(line.cartLineId)}
                        >
                          Remove
                        </button>
                      </div>
                    </div>

                    {(line.item.allowedModifiers ?? []).length > 0 ? (
                      <div className="modifierGroup">
                        {(line.item.allowedModifiers ?? []).map((modifier) => (
                          <div key={`${line.cartLineId}-${modifier.code}`} className="fieldGroup">
                            <label className="label">{modifier.label}</label>
                            {modifier.kind === "toggle" ? (
                              <label className="toggleRow">
                                <input
                                  type="checkbox"
                                  checked={line.modifierValues[modifier.code] === "true"}
                                  onChange={(event) =>
                                    updateCartLine(line.cartLineId, (current) => {
                                      const nextValues = { ...current.modifierValues };
                                      if (event.target.checked) {
                                        nextValues[modifier.code] = "true";
                                      } else {
                                        delete nextValues[modifier.code];
                                      }
                                      return { ...current, modifierValues: nextValues };
                                    })
                                  }
                                />
                                <span>{modifier.label}</span>
                              </label>
                            ) : null}
                            {modifier.kind === "choice" ? (
                              <select
                                className="input"
                                value={line.modifierValues[modifier.code] ?? ""}
                                onChange={(event) =>
                                  updateCartLine(line.cartLineId, (current) => ({
                                    ...current,
                                    modifierValues: {
                                      ...current.modifierValues,
                                      [modifier.code]: event.target.value,
                                    },
                                  }))
                                }
                              >
                                {(modifier.options ?? []).map((option) => (
                                  <option key={option} value={option}>
                                    {option}
                                  </option>
                                ))}
                              </select>
                            ) : null}
                            {modifier.kind === "text" ? (
                              <input
                                className="input"
                                type="text"
                                maxLength={80}
                                value={line.modifierValues[modifier.code] ?? ""}
                                onChange={(event) =>
                                  updateCartLine(line.cartLineId, (current) => ({
                                    ...current,
                                    modifierValues: {
                                      ...current.modifierValues,
                                      [modifier.code]: event.target.value,
                                    },
                                  }))
                                }
                              />
                            ) : null}
                          </div>
                        ))}
                      </div>
                    ) : null}

                    <div className="fieldGroup">
                      <label className="label" htmlFor={`notes-${line.cartLineId}`}>
                        Notes
                      </label>
                      <textarea
                        id={`notes-${line.cartLineId}`}
                        className="input textArea"
                        rows={2}
                        value={line.notes}
                        onChange={(event) =>
                          updateCartLine(line.cartLineId, (current) => ({
                            ...current,
                            notes: event.target.value,
                          }))
                        }
                      />
                    </div>
                  </article>
                ))}
              </div>

              <div className="divider" />

              <div className="summaryBar">
                <span>Cart Total</span>
                <span>{formatMenuMoney({ amountCents: cartTotal, currency: "USD" })}</span>
              </div>
              <button
                type="button"
                className="btn btnPrimary"
                onClick={() => void submitOrder()}
                disabled={placingOrder || cart.length === 0}
              >
                {placingOrder ? "Placing Order..." : "Place Order"}
              </button>
            </div>
          </section>

          <section className="card">
            <div className="cardHeader">
              <div>
                <h2 className="sectionTitle">My Table Orders</h2>
                <p className="hint">
                  Hydrated from REST for <span className="mono">{tableId}</span>, then kept current from websocket events.
                </p>
              </div>
              <span className="badge">{orderedTableOrders.length} orders</span>
            </div>
            <div className="cardBody">
              {ordersLoading ? <div className="infoBox">Loading orders...</div> : null}
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
                    <ul className="orderLineList">
                      {order.lines.map((line) => (
                        <li key={line.lineId} className="orderLineItem">
                          <div>
                            <span className="mono">{line.quantity}x</span> {line.name}
                          </div>
                          {Array.isArray(line.modifiers) && line.modifiers.length > 0 ? (
                            <div className="modifierChips">
                              {line.modifiers.map((modifier) => (
                                <span
                                  key={`${line.lineId}-${modifier.code}-${modifier.value}`}
                                  className="modifierChip"
                                >
                                  {formatModifierValue(modifier)}
                                </span>
                              ))}
                            </div>
                          ) : null}
                          {typeof line.notes === "string" && line.notes.trim() ? (
                            <p className="lineNotes">Notes: {line.notes}</p>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  </article>
                ))}
              </div>
            </div>
          </section>
        </section>
      </div>
    </main>
  );
}
