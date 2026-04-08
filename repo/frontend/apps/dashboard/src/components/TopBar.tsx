import { venueName } from "../lib/locationCatalog";
import type { StaffLocation, StaffMode, SummaryStats } from "../lib/types";

const typeFilterOptions: Array<{ value: StaffLocation["type"] | "ALL"; label: string }> = [
  { value: "ALL", label: "All locations" },
  { value: "TABLE", label: "Dining tables" },
  { value: "BAR_SEAT", label: "Bar seats" },
  { value: "ONLINE_PICKUP", label: "Pickup lane" },
  { value: "ONLINE_DELIVERY", label: "Delivery lane" },
];

const statusFilterOptions: Array<{ value: StaffLocation["uiStatus"] | "ALL"; label: string }> = [
  { value: "ALL", label: "All statuses" },
  { value: "AVAILABLE", label: "Available" },
  { value: "OCCUPIED", label: "Occupied" },
  { value: "ORDERING", label: "Ordering" },
  { value: "ATTENTION", label: "Attention" },
  { value: "TURNOVER", label: "Turnover" },
  { value: "MANUAL", label: "Manual" },
];

type TopBarProps = {
  mode: StaffMode;
  onModeChange: (mode: StaffMode) => void;
  search: string;
  onSearchChange: (value: string) => void;
  typeFilter: StaffLocation["type"] | "ALL";
  onTypeFilterChange: (value: StaffLocation["type"] | "ALL") => void;
  statusFilter: StaffLocation["uiStatus"] | "ALL";
  onStatusFilterChange: (value: StaffLocation["uiStatus"] | "ALL") => void;
  summaryStats: SummaryStats;
  connectionStatus: string;
  onRefresh: () => void;
  refreshing: boolean;
};

export function TopBar({
  mode,
  onModeChange,
  search,
  onSearchChange,
  typeFilter,
  onTypeFilterChange,
  statusFilter,
  onStatusFilterChange,
  summaryStats,
  connectionStatus,
  onRefresh,
  refreshing,
}: TopBarProps) {
  return (
    <header className="consoleTopBar cardSurface">
      <div className="consoleHeading">
        <p className="eyebrow">Browser Staff Console</p>
        <h1 className="pageTitle">{venueName}</h1>
        <p className="pageSubtitle">
          Responsive entrance and service operations surface aligned to live locations, sessions,
          and service follow-through. Kitchen prep progression now belongs in the dedicated kitchen
          display.
        </p>
      </div>

      <div className="modeSwitch" role="tablist" aria-label="Staff console modes">
        {(["ENTRANCE", "SERVICE"] as const).map((nextMode) => (
          <button
            key={nextMode}
            type="button"
            className={`modeButton ${mode === nextMode ? "modeButtonActive" : ""}`}
            onClick={() => onModeChange(nextMode)}
          >
            {nextMode === "ENTRANCE" ? "Entrance Mode" : "Service Mode"}
          </button>
        ))}
      </div>

      <div className="summaryStrip" aria-label="Operational summary">
        <div className="summaryMetric">
          <span className="summaryLabel">Available</span>
          <strong>{summaryStats.available}</strong>
        </div>
        <div className="summaryMetric">
          <span className="summaryLabel">Open sessions</span>
          <strong>{summaryStats.openSessions}</strong>
        </div>
        <div className="summaryMetric">
          <span className="summaryLabel">Attention</span>
          <strong>{summaryStats.attention}</strong>
        </div>
        <div className="summaryMetric">
          <span className="summaryLabel">Ordering</span>
          <strong>{summaryStats.ordering}</strong>
        </div>
        <div className="summaryMetric">
          <span className="summaryLabel">Bar awareness</span>
          <strong>{summaryStats.manual}</strong>
        </div>
      </div>

      <div className="toolbarGrid">
        <label className="fieldGroup" htmlFor="staff-search">
          <span className="fieldLabel">Search locations</span>
          <input
            id="staff-search"
            className="inputField"
            type="search"
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Find by id, label, zone"
          />
        </label>

        <label className="fieldGroup" htmlFor="staff-type-filter">
          <span className="fieldLabel">Location type</span>
          <select
            id="staff-type-filter"
            className="inputField"
            value={typeFilter}
            onChange={(event) =>
              onTypeFilterChange(event.target.value as StaffLocation["type"] | "ALL")
            }
          >
            {typeFilterOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="fieldGroup" htmlFor="staff-status-filter">
          <span className="fieldLabel">Operational status</span>
          <select
            id="staff-status-filter"
            className="inputField"
            value={statusFilter}
            onChange={(event) =>
              onStatusFilterChange(event.target.value as StaffLocation["uiStatus"] | "ALL")
            }
          >
            {statusFilterOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <div className="toolbarActions">
          <div className={connectionStatus === "Connected" ? "badge badgeLive" : "badge badgeMuted"}>
            {connectionStatus}
          </div>
          <button type="button" className="primaryButton" onClick={onRefresh} disabled={refreshing}>
            {refreshing ? "Refreshing..." : "Refresh Live Data"}
          </button>
        </div>
      </div>
    </header>
  );
}
