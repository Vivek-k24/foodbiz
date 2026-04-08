import { useEffect, useMemo, useRef, useState } from "react";

import {
  advanceOrder,
  buildStaffConsoleWsUrl,
  closeLocation,
  fetchLocationOrders,
  fetchLocations,
  fetchLocationSummary,
  fetchTableRegistry,
  openLocation,
} from "../lib/api";
import { buildOrderFromEvent, getTableEventPayload, parseEnvelope } from "../lib/events";
import { maxTimestamp, normalizeOrder } from "../lib/formatting";
import {
  buildQueueSections,
  buildStaffLocations,
  buildSummaryStats,
  filterLocations,
  groupLocationsByZone,
} from "../lib/locationViewModel";
import type {
  LocationRecord,
  OrderAction,
  OrderPayload,
  StaffLocation,
  StaffMode,
  TableRegistryItem,
  TableSummaryResponse,
} from "../lib/types";

function sortOrdersByNewest(left: OrderPayload, right: OrderPayload): number {
  return new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime();
}

function updateRowsForOrder(
  rows: Record<string, TableRegistryItem>,
  previousOrder: OrderPayload | undefined,
  nextOrder: OrderPayload
): Record<string, TableRegistryItem> {
  if (!nextOrder.tableId) {
    return rows;
  }

  const row = rows[nextOrder.tableId];
  if (!row) {
    return rows;
  }

  const nextCounts = { ...row.counts };
  const removeStatus = previousOrder?.status;
  const addStatus = nextOrder.status;

  if (!previousOrder) {
    nextCounts.ordersTotal += 1;
  }

  const decrement = (status: string | undefined): void => {
    if (status === "PLACED") {
      nextCounts.placed = Math.max(0, nextCounts.placed - 1);
    }
    if (status === "ACCEPTED") {
      nextCounts.accepted = Math.max(0, nextCounts.accepted - 1);
    }
    if (status === "READY") {
      nextCounts.ready = Math.max(0, nextCounts.ready - 1);
    }
    if (status === "SERVED") {
      nextCounts.served = Math.max(0, nextCounts.served - 1);
    }
    if (status === "SETTLED") {
      nextCounts.settled = Math.max(0, nextCounts.settled - 1);
    }
  };

  const increment = (status: string): void => {
    if (status === "PLACED") {
      nextCounts.placed += 1;
    }
    if (status === "ACCEPTED") {
      nextCounts.accepted += 1;
    }
    if (status === "READY") {
      nextCounts.ready += 1;
    }
    if (status === "SERVED") {
      nextCounts.served += 1;
    }
    if (status === "SETTLED") {
      nextCounts.settled += 1;
    }
  };

  decrement(removeStatus);
  increment(addStatus);

  return {
    ...rows,
    [nextOrder.tableId]: {
      ...row,
      lastOrderAt: maxTimestamp(row.lastOrderAt, nextOrder.createdAt),
      counts: nextCounts,
      status: row.status === "CLOSED" ? "OPEN" : row.status,
    },
  };
}

function mapTableRows(items: TableRegistryItem[]): Record<string, TableRegistryItem> {
  const next: Record<string, TableRegistryItem> = {};
  for (const row of items) {
    next[row.tableId] = row;
  }
  return next;
}

export function useStaffConsoleData() {
  const [mode, setMode] = useState<StaffMode>("ENTRANCE");
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<StaffLocation["type"] | "ALL">("ALL");
  const [statusFilter, setStatusFilter] = useState<StaffLocation["uiStatus"] | "ALL">("ALL");
  const [selectedLocationId, setSelectedLocationId] = useState("loc_tbl_001");
  const [locationRows, setLocationRows] = useState<LocationRecord[]>([]);
  const [tableRows, setTableRows] = useState<Record<string, TableRegistryItem>>({});
  const [ordersById, setOrdersById] = useState<Record<string, OrderPayload>>({});
  const [selectedSummary, setSelectedSummary] = useState<TableSummaryResponse | null>(null);
  const [connectionStatus, setConnectionStatus] = useState("Connecting");
  const [registryLoading, setRegistryLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [registryError, setRegistryError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailMessage, setDetailMessage] = useState<string | null>(null);
  const [locationActionPending, setLocationActionPending] = useState<"open" | "close" | null>(null);
  const [orderActionPending, setOrderActionPending] = useState<Record<string, boolean>>({});
  const [orderActionError, setOrderActionError] = useState<Record<string, string>>({});

  const locationRowsRef = useRef(locationRows);
  const tableRowsRef = useRef(tableRows);
  const ordersByIdRef = useRef(ordersById);

  useEffect(() => {
    locationRowsRef.current = locationRows;
  }, [locationRows]);

  useEffect(() => {
    tableRowsRef.current = tableRows;
  }, [tableRows]);

  useEffect(() => {
    ordersByIdRef.current = ordersById;
  }, [ordersById]);

  const locations = useMemo(
    () => buildStaffLocations(locationRows, tableRows),
    [locationRows, tableRows]
  );
  const filteredLocations = useMemo(
    () => filterLocations(locations, search, typeFilter, statusFilter),
    [locations, search, typeFilter, statusFilter]
  );
  const groupedLocations = useMemo(
    () => groupLocationsByZone(filteredLocations),
    [filteredLocations]
  );
  const queueSections = useMemo(
    () => buildQueueSections(mode, filteredLocations),
    [filteredLocations, mode]
  );
  const summaryStats = useMemo(() => buildSummaryStats(locations), [locations]);
  const selectedLocation = useMemo(
    () => locations.find((location) => location.locationId === selectedLocationId) ?? null,
    [locations, selectedLocationId]
  );
  const selectedOrders = useMemo(() => {
    if (!selectedLocation) {
      return [];
    }
    return Object.values(ordersById)
      .filter((order) => {
        if (selectedLocation.backendTableId) {
          return order.tableId === selectedLocation.backendTableId;
        }
        return order.locationId === selectedLocation.locationId;
      })
      .sort(sortOrdersByNewest);
  }, [ordersById, selectedLocation]);

  function mergeOrders(incoming: OrderPayload[]): void {
    const currentOrders = ordersByIdRef.current;
    const currentRows = tableRowsRef.current;
    let nextOrders = currentOrders;
    let nextRows = currentRows;

    for (const rawOrder of incoming) {
      if (!rawOrder.orderId) {
        continue;
      }
      const order = normalizeOrder(rawOrder);
      const previousOrder = nextOrders[order.orderId];
      if (nextOrders === currentOrders) {
        nextOrders = { ...currentOrders };
      }
      nextOrders[order.orderId] = order;
      nextRows = updateRowsForOrder(nextRows, previousOrder, order);
    }

    if (nextOrders !== currentOrders) {
      ordersByIdRef.current = nextOrders;
      setOrdersById(nextOrders);
    }
    if (nextRows !== currentRows) {
      tableRowsRef.current = nextRows;
      setTableRows(nextRows);
    }
  }

  async function loadFoundation(): Promise<LocationRecord[]> {
    setRegistryLoading(true);
    setRegistryError(null);
    try {
      const [locationsPayload, tableRegistryPayload] = await Promise.all([
        fetchLocations(),
        fetchTableRegistry(),
      ]);
      setLocationRows(locationsPayload.locations);
      const nextRows = mapTableRows(tableRegistryPayload.tables);
      setTableRows(nextRows);
      return locationsPayload.locations;
    } catch (error) {
      setRegistryError(error instanceof Error ? error.message : "failed to load staff console data");
      return [];
    } finally {
      setRegistryLoading(false);
    }
  }

  async function loadSelectedLocationData(
    locationId = selectedLocationId,
    availableLocations: LocationRecord[] = locationRowsRef.current
  ): Promise<void> {
    const location = availableLocations.find((row) => row.locationId === locationId) ?? null;
    const tableId = location?.type === "TABLE" ? locationId.replace(/^loc_/, "") : null;

    if (!tableId) {
      setSelectedSummary(null);
      setDetailError(null);
      return;
    }

    setDetailLoading(true);
    setDetailError(null);
    try {
      const [orders, summary] = await Promise.all([
        fetchLocationOrders(tableId),
        fetchLocationSummary(tableId),
      ]);
      mergeOrders(orders);
      setSelectedSummary(summary);
      setTableRows((current) => {
        const existing = current[tableId];
        if (!existing) {
          return current;
        }
        return {
          ...current,
          [tableId]: {
            ...existing,
            status: summary.status,
            openedAt: summary.openedAt,
            closedAt: summary.closedAt,
            lastOrderAt: summary.lastOrderAt,
            totals: summary.totals,
            counts: summary.counts,
          },
        };
      });
    } catch (error) {
      setSelectedSummary(null);
      setDetailError(error instanceof Error ? error.message : "failed to load location detail");
    } finally {
      setDetailLoading(false);
    }
  }

  async function refreshAll(): Promise<void> {
    const loadedLocations = await loadFoundation();
    await loadSelectedLocationData(selectedLocationId, loadedLocations);
  }

  async function handleOpenLocation(): Promise<void> {
    if (!selectedLocation?.backendTableId) {
      return;
    }
    setLocationActionPending("open");
    setDetailError(null);
    setDetailMessage(null);
    try {
      await openLocation(selectedLocation.backendTableId);
      setDetailMessage(`Opened session for ${selectedLocation.label}.`);
      await refreshAll();
    } catch (error) {
      setDetailError(error instanceof Error ? error.message : "failed to open session");
    } finally {
      setLocationActionPending(null);
    }
  }

  async function handleCloseLocation(): Promise<void> {
    if (!selectedLocation?.backendTableId) {
      return;
    }
    setLocationActionPending("close");
    setDetailError(null);
    setDetailMessage(null);
    try {
      await closeLocation(selectedLocation.backendTableId);
      setDetailMessage(`Closed session for ${selectedLocation.label}.`);
      await refreshAll();
    } catch (error) {
      setDetailError(error instanceof Error ? error.message : "failed to close session");
    } finally {
      setLocationActionPending(null);
    }
  }

  async function handleOrderAction(order: OrderPayload, action: OrderAction): Promise<void> {
    const nextStatus = action === "served" ? "SERVED" : "SETTLED";

    setOrderActionPending((current) => ({ ...current, [order.orderId]: true }));
    setOrderActionError((current) => {
      const next = { ...current };
      delete next[order.orderId];
      return next;
    });

    const previousOrder = order;
    mergeOrders([{ ...order, status: nextStatus }]);

    try {
      const updated = await advanceOrder(order.orderId, action);
      mergeOrders([updated]);
      if (selectedLocation?.backendTableId && updated.tableId === selectedLocation.backendTableId) {
        await loadSelectedLocationData(selectedLocation.locationId);
      }
    } catch (error) {
      mergeOrders([previousOrder]);
      const message = error instanceof Error ? error.message : "failed to update order";
      setOrderActionError((current) => ({ ...current, [order.orderId]: message }));
      if (message.includes("INVALID_ORDER_TRANSITION") || message.includes("CONFLICT")) {
        await refreshAll();
      }
    } finally {
      setOrderActionPending((current) => ({ ...current, [order.orderId]: false }));
    }
  }

  useEffect(() => {
    void refreshAll();
  }, []);

  useEffect(() => {
    if (locationRows.length === 0) {
      return;
    }
    const exists = locationRows.some((location) => location.locationId === selectedLocationId);
    if (!exists) {
      const fallbackLocation = locationRows.find((location) => location.type === "TABLE") ?? locationRows[0];
      if (fallbackLocation) {
        setSelectedLocationId(fallbackLocation.locationId);
      }
    }
  }, [locationRows, selectedLocationId]);

  useEffect(() => {
    setDetailMessage(null);
    void loadSelectedLocationData();
  }, [selectedLocationId]);

  useEffect(() => {
    const socket = new WebSocket(buildStaffConsoleWsUrl());
    socket.onopen = () => setConnectionStatus("Connected");
    socket.onclose = () => setConnectionStatus("Disconnected");
    socket.onerror = () => setConnectionStatus("Disconnected");
    socket.onmessage = (event) => {
      const envelope = parseEnvelope(event.data);
      if (!envelope) {
        return;
      }

      const order = buildOrderFromEvent(envelope.payload);
      if (order) {
        mergeOrders([order]);
        if (
          (selectedLocation?.backendTableId && order.tableId === selectedLocation.backendTableId) ||
          order.locationId === selectedLocationId
        ) {
          void loadSelectedLocationData(selectedLocationId);
        }
        return;
      }

      const tableEvent = getTableEventPayload(envelope.payload);
      if (!tableEvent) {
        return;
      }

      setTableRows((current) => {
        const existing = current[tableEvent.tableId];
        if (!existing) {
          return current;
        }
        return {
          ...current,
          [tableEvent.tableId]: {
            ...existing,
            status:
              tableEvent.status === "OPEN" || tableEvent.status === "CLOSED"
                ? tableEvent.status
                : existing.status,
            openedAt: tableEvent.openedAt ?? existing.openedAt,
            closedAt: tableEvent.closedAt ?? existing.closedAt,
          },
        };
      });

      if (selectedLocation?.backendTableId === tableEvent.tableId) {
        void loadSelectedLocationData(selectedLocationId);
      }
    };

    return () => socket.close();
  }, [selectedLocation, selectedLocationId]);

  return {
    mode,
    setMode,
    search,
    setSearch,
    typeFilter,
    setTypeFilter,
    statusFilter,
    setStatusFilter,
    selectedLocationId,
    setSelectedLocationId,
    selectedLocation,
    selectedOrders,
    selectedSummary,
    locations,
    filteredLocations,
    groupedLocations,
    queueSections,
    summaryStats,
    connectionStatus,
    registryLoading,
    detailLoading,
    registryError,
    detailError,
    detailMessage,
    locationActionPending,
    orderActionPending,
    orderActionError,
    refreshAll,
    loadSelectedLocationData,
    handleOpenLocation,
    handleCloseLocation,
    handleOrderAction,
  };
}
