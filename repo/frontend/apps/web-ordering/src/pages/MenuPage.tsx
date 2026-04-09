import { useEffect, useMemo, useState } from "react";

import {
  buildMenuSections,
  buildUrlForState,
  locationIdFromTableId,
  normalizeTableId,
  orderSourceForMode,
  readUrlStateFromHref,
  resolveActiveContext,
  type ActiveOrderingContext,
  type EntryMode,
  type OrderingUrlState,
} from "../lib/ordering";

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

type MenuCategory = {
  categoryId: string;
  name: string;
  categoryKind: "FOOD" | "DRINK";
  cuisineOrFamily: string;
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
  categories: MenuCategory[];
  items: MenuItem[];
};

type LocationRecord = {
  locationId: string;
  restaurantId: string;
  type: "TABLE" | "BAR_SEAT" | "ONLINE_PICKUP" | "ONLINE_DELIVERY";
  name: string;
  displayLabel: string;
  capacity: number | null;
  zone: string | null;
  isActive: boolean;
  createdAt: string;
  sessionStatus: "OPEN" | "CLOSED" | null;
  activeSessionId: string | null;
  lastSessionOpenedAt: string | null;
};

type LocationsResponse = {
  locations: LocationRecord[];
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

type OrderResponse = {
  orderId: string;
  tableId?: string | null;
  locationId?: string | null;
  status: string;
  total?: OrderMoney | null;
  totalMoney?: OrderMoney | null;
  createdAt: string;
  lines: OrderLine[];
};

type TableOrdersResponse = {
  orders: OrderResponse[];
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
const restaurantId = "rst_001";

function readInitialUrlState(): OrderingUrlState {
  if (typeof window === "undefined") {
    return { mode: "ONLINE_PICKUP", tableId: null, locationId: null };
  }
  return readUrlStateFromHref(window.location.href);
}

function applyUrlState(state: OrderingUrlState): void {
  if (typeof window === "undefined") {
    return;
  }
  window.history.replaceState(null, "", buildUrlForState(window.location.href, state));
}

function buildIdempotencyKey(context: ActiveContext): string {
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
  return `rop14-${context.mode.toLowerCase()}-${context.locationId ?? "none"}-${stamp}-${random}`;
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

function normalizeOrder(order: OrderResponse): OrderResponse {
  return {
    ...order,
    totalMoney: order.totalMoney ?? order.total ?? null,
    lines: Array.isArray(order.lines) ? order.lines : [],
  };
}

function getOrderMoney(order: OrderResponse): OrderMoney | null | undefined {
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

function MenuCategorySection({
  title,
  sections,
  onAddItem,
}: {
  title: string;
  sections: Array<{ category: MenuCategory; items: MenuItem[] }>;
  onAddItem: (item: MenuItem) => void;
}) {
  return (
    <section>
      <div className="sectionHeader">
        <h3 className="subheading">{title}</h3>
        <span className="badge">
          {sections.reduce((total, section) => total + section.items.length, 0)} items
        </span>
      </div>
      <div className="sectionStack compactStack">
        {sections.map(({ category, items }) => (
          <section key={category.categoryId} className="categorySection">
            <div className="categoryHeader">
              <div>
                <h4 className="subheading">{category.name}</h4>
                <p className="muted">{category.cuisineOrFamily.replace(/_/g, " ")}</p>
              </div>
              <span className="badge">{items.length}</span>
            </div>
            <div className="menuGrid">
              {items.map((item) => (
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
                    onClick={() => onAddItem(item)}
                    disabled={!item.isAvailable}
                  >
                    Add to Cart
                  </button>
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}

export function MenuPage() {
  const [menu, setMenu] = useState<MenuResponse | null>(null);
  const [locations, setLocations] = useState<LocationRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cart, setCart] = useState<CartLine[]>([]);
  const [placingOrder, setPlacingOrder] = useState(false);
  const [orderResult, setOrderResult] = useState<string | null>(null);
  const [tableOrders, setTableOrders] = useState<Record<string, OrderResponse>>({});
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [ordersError, setOrdersError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState("Connecting");
  const [urlState, setUrlState] = useState<OrderingUrlState>(readInitialUrlState);
  const [supportTableId, setSupportTableId] = useState("");

  function setNextUrlState(next: OrderingUrlState): void {
    setUrlState(next);
    applyUrlState(next);
  }

  const resolvedTableId = useMemo(() => normalizeTableId(urlState.tableId), [urlState.tableId]);
  const resolvedLocationId = useMemo(
    () => urlState.locationId ?? locationIdFromTableId(resolvedTableId),
    [resolvedTableId, urlState.locationId]
  );

  const activeContext = useMemo<ActiveOrderingContext>(
    () => resolveActiveContext(urlState, locations),
    [locations, urlState]
  );

  const canUseDineInMode =
    !!resolvedLocationId &&
    locations.some(
      (location) => location.locationId === resolvedLocationId && location.type === "TABLE"
    );

  const menuEndpoint = useMemo(() => `${apiBaseUrl}/v1/restaurants/${restaurantId}/menu`, []);
  const locationsEndpoint = useMemo(
    () => `${apiBaseUrl}/v1/restaurants/${restaurantId}/locations?is_active=true`,
    []
  );
  const tableOrdersEndpoint = useMemo(
    () =>
      activeContext.tableId
        ? `${apiBaseUrl}/v1/restaurants/${restaurantId}/tables/${encodeURIComponent(
            activeContext.tableId
          )}/orders?status=ALL&limit=50`
        : null,
    [activeContext.tableId]
  );
  const locationOrdersEndpoint = useMemo(
    () =>
      !activeContext.tableId && activeContext.locationId
        ? `${apiBaseUrl}/v1/restaurants/${restaurantId}/locations/${encodeURIComponent(
            activeContext.locationId
          )}/orders?status=ALL&limit=50`
        : null,
    [activeContext.locationId, activeContext.tableId]
  );
  const wsUrl = useMemo(() => {
    const url = new URL("/ws", wsBaseUrl);
    url.searchParams.set("restaurant_id", restaurantId);
    url.searchParams.set("role", "WEB_ORDERING");
    return url.toString();
  }, []);

  function mergeOrders(incoming: OrderResponse[]): void {
    setTableOrders((current) => {
      const next = { ...current };
      for (const incomingOrder of incoming) {
        next[incomingOrder.orderId] = normalizeOrder(incomingOrder);
      }
      return next;
    });
  }

  function updateCartLine(cartLineId: string, updater: (line: CartLine) => CartLine): void {
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
    const ordersEndpoint = tableOrdersEndpoint ?? locationOrdersEndpoint;
    if (!ordersEndpoint) {
      setTableOrders({});
      return;
    }
    setOrdersLoading(true);
    setOrdersError(null);
    try {
      const response = await fetch(ordersEndpoint);
      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }
      const payload = (await response.json()) as TableOrdersResponse;
      setTableOrders({});
      mergeOrders(payload.orders);
    } catch (loadError) {
      setOrdersError(
        loadError instanceof Error ? loadError.message : "failed to load location orders"
      );
    } finally {
      setOrdersLoading(false);
    }
  }

  useEffect(() => {
    let active = true;

    async function loadFoundation(): Promise<void> {
      setLoading(true);
      try {
        const [menuResponse, locationsResponse] = await Promise.all([
          fetch(menuEndpoint),
          fetch(locationsEndpoint),
        ]);
        if (!menuResponse.ok) {
          throw new Error(await readErrorMessage(menuResponse));
        }
        if (!locationsResponse.ok) {
          throw new Error(await readErrorMessage(locationsResponse));
        }
        const menuPayload = (await menuResponse.json()) as MenuResponse;
        const locationPayload = (await locationsResponse.json()) as LocationsResponse;
        if (active) {
          setMenu(menuPayload);
          setLocations(locationPayload.locations);
          setError(null);
        }
      } catch (loadError) {
        if (active) {
          setError(
            loadError instanceof Error ? loadError.message : "failed to load ordering data"
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadFoundation();
    return () => {
      active = false;
    };
  }, [locationsEndpoint, menuEndpoint]);

  useEffect(() => {
    setOrderResult(null);
    void loadTableOrders();
  }, [locationOrdersEndpoint, tableOrdersEndpoint]);

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
        const payloadTableId = typeof payload.tableId === "string" ? payload.tableId : null;
        const payloadLocationId =
          typeof payload.locationId === "string" ? payload.locationId : null;
        const matchesContext =
          (activeContext.tableId && payloadTableId === activeContext.tableId) ||
          (activeContext.locationId && payloadLocationId === activeContext.locationId);
        if (!matchesContext) {
          return;
        }
        mergeOrders([
          {
            orderId: payload.orderId,
            tableId: payloadTableId,
            locationId: payloadLocationId,
            status: String(payload.status ?? ""),
            totalMoney: payload.totalMoney as OrderMoney | null | undefined,
            total: payload.total as OrderMoney | null | undefined,
            createdAt: String(payload.createdAt ?? ""),
            lines: Array.isArray(payload.lines) ? (payload.lines as OrderLine[]) : [],
          },
        ]);
      } catch {
        // Ignore malformed event payloads.
      }
    };
    return () => socket.close();
  }, [activeContext.locationId, activeContext.tableId, wsUrl]);

  async function submitOrder(): Promise<void> {
    if (cart.length === 0 || !activeContext.locationId) {
      return;
    }

    setPlacingOrder(true);
    setOrderResult(null);
    try {
      const response = await fetch(`${apiBaseUrl}/v1/orders`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": buildIdempotencyKey(activeContext),
        },
        body: JSON.stringify({
          restaurantId,
          locationId: activeContext.locationId,
          sessionId: activeContext.sessionId,
          tableId: activeContext.tableId,
          source: orderSourceForMode(activeContext.mode),
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
                  return value ? { code: modifier.code, label: modifier.label, value } : null;
                })
                .filter(
                  (modifier): modifier is { code: string; label: string; value: string } =>
                    modifier !== null
                ) || null,
          })),
        }),
      });
      if (!response.ok) {
        throw new Error(await readErrorMessage(response));
      }
      const payload = normalizeOrder((await response.json()) as OrderResponse);
      mergeOrders([payload]);
      setCart([]);
      setOrderResult(`Created order ${payload.orderId} for ${activeContext.label}`);
      if (activeContext.tableId) {
        await loadTableOrders();
      }
    } catch (placeError) {
      setOrderResult(placeError instanceof Error ? placeError.message : "order failed");
    } finally {
      setPlacingOrder(false);
    }
  }

  function applySupportTable(): void {
    const normalized = normalizeTableId(supportTableId);
    if (!normalized) {
      return;
    }
    setNextUrlState({
      mode: "DINE_IN",
      tableId: normalized,
      locationId: locationIdFromTableId(normalized),
    });
  }

  const categoryById = useMemo(
    () => new Map((menu?.categories ?? []).map((category) => [category.categoryId, category])),
    [menu]
  );

  const foodSections = useMemo(() => buildMenuSections(menu, "FOOD"), [menu]);

  const drinkSections = useMemo(() => buildMenuSections(menu, "DRINK"), [menu]);

  const orderedTableOrders = useMemo(
    () =>
      Object.values(tableOrders).sort(
        (left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime()
      ),
    [tableOrders]
  );

  const cartTotal = useMemo(
    () => cart.reduce((total, line) => total + line.item.priceMoney.amountCents * line.quantity, 0),
    [cart]
  );

  const orderResultIsError = orderResult !== null && !orderResult.startsWith("Created order ");

  if (loading) {
    return (
      <main className="container">
        <section className="card">
          <div className="cardBody">
            <div className="infoBox">Loading ordering surface...</div>
          </div>
        </section>
      </main>
    );
  }

  if (error || !menu) {
    return (
      <main className="container">
        <section className="card">
          <div className="cardBody">
            <div className="errorBox">
              Failed to load ordering data: {error ?? "menu unavailable"}
            </div>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="container">
      <header className="header">
        <div>
          <p className="eyebrow">Browser Ordering Surface</p>
          <h1 className="title">FoodBiz Ordering</h1>
          <p className="subtitle">
            Dine-in uses scan-aware table context when present. Pickup and delivery stay available as
            browser-first paths.
          </p>
        </div>
        <div className={connectionStatus === "Connected" ? "badge badgeStrong" : "badge badgeMuted"}>
          {connectionStatus}
        </div>
      </header>

      <section className="card">
        <div className="cardHeader">
          <div>
            <h2 className="sectionTitle">Entry context</h2>
            <p className="hint">
              The URL is now the primary dine-in entry source so future signed QR links can plug in
              cleanly.
            </p>
          </div>
          <span className="badge">{activeContext.label}</span>
        </div>
        <div className="cardBody sectionStack">
          <div className="contextSwitch" role="tablist" aria-label="Ordering modes">
            <button
              type="button"
              className={`contextButton ${activeContext.mode === "DINE_IN" ? "contextButtonActive" : ""}`}
              disabled={!canUseDineInMode}
              onClick={() =>
                setNextUrlState({
                  mode: "DINE_IN",
                  tableId: resolvedTableId,
                  locationId: resolvedLocationId,
                })
              }
            >
              {canUseDineInMode
                ? `Dine-In ${activeContext.scanSource ? `(${activeContext.label})` : ""}`
                : "Scan a table QR"}
            </button>
            <button
              type="button"
              className={`contextButton ${activeContext.mode === "ONLINE_PICKUP" ? "contextButtonActive" : ""}`}
              onClick={() => setNextUrlState({ mode: "ONLINE_PICKUP", tableId: null, locationId: null })}
            >
              Pickup
            </button>
            <button
              type="button"
              className={`contextButton ${activeContext.mode === "ONLINE_DELIVERY" ? "contextButtonActive" : ""}`}
              onClick={() =>
                setNextUrlState({ mode: "ONLINE_DELIVERY", tableId: null, locationId: null })
              }
            >
              Delivery
            </button>
          </div>

          <div className="contextCard">
            <div className="rowHeader">
              <div>
                <h3 className="subheading">{activeContext.label}</h3>
                <p className="hint">{activeContext.subtitle}</p>
              </div>
              <div className="badgeRow">
                <span className="badge mono">{activeContext.locationId ?? "No location"}</span>
                {activeContext.tableId ? <span className="badge mono">{activeContext.tableId}</span> : null}
              </div>
            </div>
            <div className={activeContext.orderable ? "infoBox" : "errorBox"}>
              {activeContext.orderableMessage}
            </div>
          </div>

          {!canUseDineInMode ? (
            <div className="infoBox">
              No dine-in scan context is present. Use pickup or delivery, or open the support override
              to test a table manually.
            </div>
          ) : null}

          <details className="supportPanel">
            <summary>Support override for manual table lookup</summary>
            <div className="supportGrid">
              <div className="fieldGroup">
                <label className="label" htmlFor="support-table-id">
                  Table ID
                </label>
                <input
                  id="support-table-id"
                  className="input mono"
                  type="text"
                  placeholder="tbl_001"
                  value={supportTableId}
                  onChange={(event) => setSupportTableId(event.target.value)}
                />
              </div>
              <button type="button" className="btn btnSecondary" onClick={applySupportTable}>
                Apply table context
              </button>
            </div>
          </details>

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
              <p className="hint">
                Menu sections now follow backend category metadata instead of item-id naming hacks.
              </p>
            </div>
            <span className="badge">{menu.items.length} items</span>
          </div>
          <div className="cardBody sectionStack">
            <MenuCategorySection title="Food" sections={foodSections} onAddItem={addItemToCart} />
            <MenuCategorySection title="Drinks" sections={drinkSections} onAddItem={addItemToCart} />
          </div>
        </section>

        <section className="sidebarStack">
          <section className="card">
            <div className="cardHeader">
              <div>
                <h2 className="sectionTitle">Cart & Checkout</h2>
                <p className="hint">
                  Each line keeps its own quantity, notes, and item-specific modifiers.
                </p>
              </div>
              <span className="badge">{cart.length} lines</span>
            </div>
            <div className="cardBody">
              {cart.length === 0 ? (
                <div className="emptyState">Add food or drinks to start an order.</div>
              ) : null}

              <div className="listStack">
                {cart.map((line) => (
                  <article key={line.cartLineId} className="cartLine">
                    <div className="rowHeader">
                      <div>
                        <div className="rowTitle">{line.item.name}</div>
                        <p className="muted mono">
                          {categoryById.get(line.item.categoryId ?? "")?.name ?? line.item.itemId}
                        </p>
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
                disabled={
                  placingOrder ||
                  cart.length === 0 ||
                  !activeContext.orderable ||
                  !activeContext.locationId
                }
              >
                {placingOrder
                  ? "Placing Order..."
                  : `Place ${
                      activeContext.mode === "DINE_IN"
                        ? "Dine-In"
                        : activeContext.mode === "ONLINE_PICKUP"
                          ? "Pickup"
                          : "Delivery"
                    } Order`}
              </button>
            </div>
          </section>

          <section className="card">
            <div className="cardHeader">
              <div>
                <h2 className="sectionTitle">Recent orders</h2>
                <p className="hint">
                  {activeContext.tableId
                    ? `Hydrated from the live table history for ${activeContext.tableId}.`
                    : `Hydrated from the live ${activeContext.mode === "ONLINE_PICKUP" ? "pickup" : "delivery"} location queue.`}
                </p>
              </div>
              <span className="badge">{orderedTableOrders.length} orders</span>
            </div>
            <div className="cardBody">
              {ordersLoading ? <div className="infoBox">Loading orders...</div> : null}
              {ordersError ? <div className="errorBox">{ordersError}</div> : null}
              {!ordersLoading && orderedTableOrders.length === 0 ? (
                <div className="emptyState">
                  {activeContext.mode === "DINE_IN"
                    ? "No orders yet for this table."
                    : "No recent orders yet for this fulfillment lane."}
                </div>
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
