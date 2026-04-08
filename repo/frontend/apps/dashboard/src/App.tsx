import { useEffect, useState } from "react";

import { DetailPane } from "./components/DetailPane";
import { FloorPane } from "./components/FloorPane";
import { QueuePane } from "./components/QueuePane";
import { TopBar } from "./components/TopBar";
import { useStaffConsoleData } from "./hooks/useStaffConsoleData";
import { useViewportMode } from "./hooks/useViewportMode";
import type { SecondaryPane } from "./lib/types";

function App() {
  const viewportMode = useViewportMode();
  const [secondaryPane, setSecondaryPane] = useState<SecondaryPane>("QUEUE");
  const {
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
    handleOpenLocation,
    handleCloseLocation,
    handleOrderAction,
  } = useStaffConsoleData();

  useEffect(() => {
    if (viewportMode === "large") {
      setSecondaryPane("QUEUE");
    }
  }, [viewportMode]);

  function handleSelectLocation(locationId: string): void {
    setSelectedLocationId(locationId);
    if (viewportMode !== "large") {
      setSecondaryPane("DETAIL");
    }
  }

  return (
    <main className="staffConsoleRoot">
      <TopBar
        mode={mode}
        onModeChange={setMode}
        search={search}
        onSearchChange={setSearch}
        typeFilter={typeFilter}
        onTypeFilterChange={setTypeFilter}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        summaryStats={summaryStats}
        connectionStatus={connectionStatus}
        onRefresh={() => void refreshAll()}
        refreshing={registryLoading}
      />

      {(registryError || detailError) ? (
        <div className="globalBanner cardSurface">
          <strong>Live data is degraded.</strong>
          <span>
            {registryError ?? detailError} The console keeps the floor model visible so operators can
            maintain context while connectivity recovers.
          </span>
        </div>
      ) : null}

      {viewportMode !== "large" ? (
        <div className="secondaryNav cardSurface">
          <button
            type="button"
            className={`modeButton ${secondaryPane === "QUEUE" ? "modeButtonActive" : ""}`}
            onClick={() => setSecondaryPane("QUEUE")}
          >
            Queue Pane
          </button>
          <button
            type="button"
            className={`modeButton ${secondaryPane === "DETAIL" ? "modeButtonActive" : ""}`}
            onClick={() => setSecondaryPane("DETAIL")}
          >
            Detail Pane
          </button>
        </div>
      ) : null}

      <section className="consoleViewport">
        {viewportMode === "large" ? (
          <div className="consoleShell consoleShellLarge">
            <QueuePane
              mode={mode}
              sections={queueSections}
              selectedLocationId={selectedLocationId}
              onSelectLocation={handleSelectLocation}
              loading={registryLoading}
              error={registryError}
            />
            <FloorPane
              groupedLocations={groupedLocations}
              selectedLocationId={selectedLocationId}
              onSelectLocation={handleSelectLocation}
              loading={registryLoading}
              error={registryError}
            />
            <DetailPane
              mode={mode}
              location={selectedLocation}
              summary={selectedSummary}
              orders={selectedOrders}
              loading={detailLoading}
              error={detailError}
              message={detailMessage}
              locationActionPending={locationActionPending}
              orderActionPending={orderActionPending}
              orderActionError={orderActionError}
              onOpenLocation={() => void handleOpenLocation()}
              onCloseLocation={() => void handleCloseLocation()}
              onOrderAction={(order, action) => void handleOrderAction(order, action)}
            />
          </div>
        ) : (
          <div
            className={`consoleShell ${
              viewportMode === "medium" ? "consoleShellMedium" : "consoleShellNarrow"
            }`}
          >
            <FloorPane
              groupedLocations={groupedLocations}
              selectedLocationId={selectedLocationId}
              onSelectLocation={handleSelectLocation}
              loading={registryLoading}
              error={registryError}
            />

            {secondaryPane === "QUEUE" ? (
              <QueuePane
                mode={mode}
                sections={queueSections}
                selectedLocationId={selectedLocationId}
                onSelectLocation={handleSelectLocation}
                loading={registryLoading}
                error={registryError}
              />
            ) : (
              <DetailPane
                mode={mode}
                location={selectedLocation}
                summary={selectedSummary}
                orders={selectedOrders}
                loading={detailLoading}
                error={detailError}
                message={detailMessage}
                locationActionPending={locationActionPending}
                orderActionPending={orderActionPending}
                orderActionError={orderActionError}
                onOpenLocation={() => void handleOpenLocation()}
                onCloseLocation={() => void handleCloseLocation()}
                onOrderAction={(order, action) => void handleOrderAction(order, action)}
              />
            )}
          </div>
        )}
      </section>
    </main>
  );
}

export default App;
