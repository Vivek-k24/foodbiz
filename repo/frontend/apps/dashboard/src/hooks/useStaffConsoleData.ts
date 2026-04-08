import { useEffect, useMemo, useRef, useState } from "react";

import {
  advanceOrder,
  buildStaffConsoleWsUrl,
  closeLocation,
  fetchKitchenOrders,
  fetchLocationOrders,
  fetchLocationSummary,
  fetchTableRegistry,
  openLocation,
} from "../lib/api";
import { parseEnvelope, buildOrderFromEvent, getTableEventPayload } from "../lib/events";
import { maxTimestamp, normalizeOrder } from "../lib/formatting";
import {
  buildQueueSections,
  buildStaffLocations,
  buildSummaryStats,
  filterLocations,
  groupLocationsByZone,
} from "../lib/locationViewModel";
import { supportsBackendLocation } from "../lib/locationCatalog";
import type {
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
  const row = rows[nextOrder.tableId];
  if (!row) {
    return rows;
  }

  const nextCounts = {
    ...row.counts,
  };

  const removeStatus = previousOrder?.status;
  const addStatus = nextOrder.status;

  if (!previousOrder) {
    nextCounts.ordersTotal += 1;
  }

  if (removeStatus === "PLACED") {
    nextCounts.placed = Math.max(0, nextCounts.placed - 1);
  }
  if (removeStatus === "ACCEPTED") {
    nextCounts.accepted = Math.max(0, nextCounts.accepted - 1);
  }
  if (removeStatus === "READY") {
    nextCounts.ready = Math.max(0, nextCounts.ready - 1);
  }

  if (addStatus === "PLACED") {
    nextCounts.placed += 1;
  }
  if (addStatus === "ACCEPTED") {
    nextCounts.accepted += 1;
  }
  if (addStatus === "READY") {
    nextCounts.ready += 1;
  }

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

export function useStaffConsoleData() {
  const [mode, setMode] = useState<StaffMode>("ENTRANCE");
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<StaffLocation["type"] | "ALL">("ALL");
  const [statusFilter, setStatusFilter] = useState<StaffLocation["uiStatus"] | "ALL">("ALL");
  const [selectedLocationId, setSelectedLocationId] = useState("tbl_001");
  const [tableRows, setTableRows] = useState<Record<string, TableRegistryItem>>({});
  const [ordersById, setOrdersById] = useState<Record<string, OrderPayload>>({});
  const [selectedSummary, setSelectedSummary] = useState<TableSummaryResponse | null>(null);
  const [connectionStatus, setConnectionStatus] = useState("Connecting");
  const [registryLoading, setRegistryLoading] = useState(false);
  const [activityLoading, setActivityLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [registryError, setRegistryError] = useState<string | null>(null);
  const [activityError, setActivityError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailMessage, setDetailMessage] = useState<string | null>(null);
  const [locationActionPending, setLocationActionPending] = useState<"open" | "close" | null>(null);
  const [orderActionPending, setOrderActionPending] = useState<Record<string, boolean>>({});
  const [orderActionError, setOrderActionError] = useState<Record<string, string>>({});
  const tableRowsRef = useRef(tableRows);
  const ordersByIdRef = useRef(ordersById);

  useEffect(() => {
    tableRowsRef.current = tableRows;
  }, [tableRows]);

  useEffect(() => {
    ordersByIdRef.current = ordersById;
  }, [ordersById]);

  const locations = useMemo(
    () => buildStaffLocations(tableRows, ordersById),
    [ordersById, tableRows]
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
  const selectedOrders = useMemo(
    () =>
      Object.values(ordersById)
        .filter((order) => order.tableId === selectedLocationId)
        .sort(sortOrdersByNewest),
    [ordersById, selectedLocationId]
  );

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

  async function loadRegistry(): Promise<void> {
    setRegistryLoading(true);
    setRegistryError(null);
    try {
      const payload = await fetchTableRegistry();
      setTableRows(() => {
        const next: Record<string, TableRegistryItem> = {};
        for (const row of payload.tables) {
          next[row.tableId] = row;
        }
        return next;
      });
    } catch (error) {
      setRegistryError(error instanceof Error ? error.message : "failed to load locations");
    } finally {
      setRegistryLoading(false);
    }
  }

  async function loadActivity(): Promise<void> {
    setActivityLoading(true);
    setActivityError(null);
    try {
      mergeOrders(await fetchKitchenOrders());
    } catch (error) {
      setActivityError(error instanceof Error ? error.message : "failed to load active orders");
    } finally {
      setActivityLoading(false);
    }
  }

  async function loadSelectedLocationData(locationId = selectedLocationId): Promise<void> {
    if (!supportsBackendLocation(locationId)) {
      setSelectedSummary(null);
      setDetailError(null);
      return;
    }

    setDetailLoading(true);
    setDetailError(null);
    try {
      const [orders, summary] = await Promise.all([
        fetchLocationOrders(locationId),
        fetchLocationSummary(locationId),
      ]);
      mergeOrders(orders);
      setSelectedSummary(summary);
      setTableRows((current) => {
        const existing = current[locationId];
        if (!existing) {
          return current;
        }
        return {
          ...current,
          [locationId]: {
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
    await Promise.all([loadRegistry(), loadActivity()]);
    await loadSelectedLocationData();
  }

  async function handleOpenLocation(): Promise<void> {
    if (!selectedLocation?.supportsBackendSession) {
      return;
    }
    setLocationActionPending("open");
    setDetailError(null);
    setDetailMessage(null);
    try {
      await openLocation(selectedLocation.locationId);
      setDetailMessage(`Opened session for ${selectedLocation.label}.`);
      await Promise.all([loadRegistry(), loadSelectedLocationData(selectedLocation.locationId)]);
    } catch (error) {
      setDetailError(error instanceof Error ? error.message : "failed to open session");
    } finally {
      setLocationActionPending(null);
    }
  }

  async function handleCloseLocation(): Promise<void> {
    if (!selectedLocation?.supportsBackendSession) {
      return;
    }
    setLocationActionPending("close");
    setDetailError(null);
    setDetailMessage(null);
    try {
      await closeLocation(selectedLocation.locationId);
      setDetailMessage(`Closed session for ${selectedLocation.label}.`);
      await Promise.all([loadRegistry(), loadSelectedLocationData(selectedLocation.locationId)]);
    } catch (error) {
      setDetailError(error instanceof Error ? error.message : "failed to close session");
    } finally {
      setLocationActionPending(null);
    }
  }

  async function handleOrderAction(order: OrderPayload, action: OrderAction): Promise<void> {
    const nextStatus =
      action === "accept"
        ? "ACCEPTED"
        : action === "ready"
          ? "READY"
          : action === "served"
            ? "SERVED"
            : "SETTLED";

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
      if (updated.tableId === selectedLocationId) {
        await loadSelectedLocationData(selectedLocationId);
      }
    } catch (error) {
      mergeOrders([previousOrder]);
      const message = error instanceof Error ? error.message : "failed to update order";
      setOrderActionError((current) => ({ ...current, [order.orderId]: message }));
      if (message.includes("INVALID_ORDER_TRANSITION") || message.includes("CONFLICT")) {
        await Promise.all([loadRegistry(), loadActivity(), loadSelectedLocationData(previousOrder.tableId)]);
      }
    } finally {
      setOrderActionPending((current) => ({ ...current, [order.orderId]: false }));
    }
  }

  useEffect(() => {
    void refreshAll();
  }, []);

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
        if (order.tableId === selectedLocationId) {
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

      if (tableEvent.tableId === selectedLocationId) {
        void loadSelectedLocationData(selectedLocationId);
      }
    };

    return () => socket.close();
  }, [selectedLocationId]);

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
    activityLoading,
    detailLoading,
    registryError,
    activityError,
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
