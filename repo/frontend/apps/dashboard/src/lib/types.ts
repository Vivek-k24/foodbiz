export type MoneyPayload = {
  amountCents?: number | null;
  currency?: string | null;
};

export type OrderLineModifierPayload = {
  code: string;
  label: string;
  value: string;
};

export type OrderLinePayload = {
  lineId: string;
  itemId: string;
  name: string;
  quantity: number;
  notes?: string | null;
  modifiers?: OrderLineModifierPayload[] | null;
};

export type OrderPayload = {
  orderId: string;
  restaurantId?: string;
  tableId: string;
  status: string;
  total?: MoneyPayload | null;
  totalMoney?: MoneyPayload | null;
  createdAt: string;
  lines: OrderLinePayload[];
};

export type KitchenQueueResponse = {
  orders: OrderPayload[];
  nextCursor: string | null;
};

export type TableOrdersResponse = {
  orders: OrderPayload[];
  nextCursor: string | null;
};

export type TableCounts = {
  ordersTotal: number;
  placed: number;
  accepted: number;
  ready: number;
};

export type TableSummaryResponse = {
  tableId: string;
  restaurantId: string;
  status: string;
  openedAt: string | null;
  closedAt: string | null;
  totals: MoneyPayload;
  counts: TableCounts;
  lastOrderAt: string | null;
};

export type TableRegistryItem = {
  tableId: string;
  restaurantId: string;
  status: string;
  openedAt: string | null;
  closedAt: string | null;
  lastOrderAt: string | null;
  totals: MoneyPayload;
  counts: TableCounts;
};

export type TableRegistryResponse = {
  tables: TableRegistryItem[];
  nextCursor: string | null;
};

export type ApiErrorResponse = {
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, unknown>;
  };
  requestId?: string;
};

export type ApiError = {
  code: string | null;
  message: string;
  requestId: string | null;
};

export type EventEnvelope = {
  event_type: string;
  restaurant_id?: string;
  request_id?: string | null;
  trace_id?: string | null;
  occurred_at?: string;
  payload?: unknown;
};

export type LocationType = "TABLE" | "BAR_SEAT" | "KIOSK_TABLE";
export type LocationUiStatus =
  | "AVAILABLE"
  | "OCCUPIED"
  | "ORDERING"
  | "ATTENTION"
  | "TURNOVER"
  | "MANUAL";
export type StaffMode = "ENTRANCE" | "SERVICE";
export type ViewportMode = "large" | "medium" | "narrow";
export type SecondaryPane = "QUEUE" | "DETAIL";

export type LocationCatalogEntry = {
  locationId: string;
  label: string;
  type: LocationType;
  zone: string;
  seatCount: number;
  sortOrder: number;
  manualOnly: boolean;
  kioskLinked: boolean;
  supportsBackendSession: boolean;
};

export type LocationCounts = {
  ordersTotal: number;
  placed: number;
  accepted: number;
  ready: number;
  served: number;
  settled: number;
};

export type StaffLocation = LocationCatalogEntry & {
  backendStatus: "OPEN" | "CLOSED" | null;
  sessionOpen: boolean;
  uiStatus: LocationUiStatus;
  openedAt: string | null;
  closedAt: string | null;
  lastOrderAt: string | null;
  totals: MoneyPayload;
  counts: LocationCounts;
  activeOrderIds: string[];
  assignmentState: "UNASSIGNED" | "MANUAL_ONLY" | "NOT_APPLICABLE";
};

export type QueueSection = {
  id: string;
  title: string;
  emptyText: string;
  items: StaffLocation[];
};

export type SummaryStats = {
  available: number;
  openSessions: number;
  attention: number;
  ordering: number;
  manual: number;
};

export type OrderAction = "accept" | "ready" | "served" | "settled";
