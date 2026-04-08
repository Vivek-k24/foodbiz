import { formatMoneyValue, formatTimestamp } from "../lib/formatting";
import type { QueueSection, StaffLocation, StaffMode } from "../lib/types";
import { locationStatusClass, locationTypeClass } from "./StatusBadge";

type QueuePaneProps = {
  mode: StaffMode;
  sections: QueueSection[];
  selectedLocationId: string;
  onSelectLocation: (locationId: string) => void;
  loading: boolean;
  error: string | null;
};

export function QueuePane({
  mode,
  sections,
  selectedLocationId,
  onSelectLocation,
  loading,
  error,
}: QueuePaneProps) {
  return (
    <section className="shellPane cardSurface queuePane">
      <div className="paneHeader">
        <div>
          <p className="eyebrow">Operational queue</p>
          <h2 className="paneTitle">{mode === "ENTRANCE" ? "Arrivals and occupancy" : "Service attention"}</h2>
          <p className="paneHint">
            {mode === "ENTRANCE"
              ? "Use this pane to seat guests quickly, spot open sessions, and keep turnover visible."
              : "Use this pane to spot active work, ready handoff points, and open sessions that still need ownership."}
          </p>
        </div>
      </div>

      {loading ? <div className="infoBox">Loading queue data...</div> : null}
      {error ? <div className="errorBox">{error}</div> : null}

      <div className="queueSections">
        {sections.map((section) => (
          <div key={section.id} className="queueSection">
            <div className="sectionHeaderCompact">
              <h3 className="sectionTitleSmall">{section.title}</h3>
              <span className="badge">{section.items.length}</span>
            </div>

            {section.items.length === 0 ? (
              <div className="emptyBox">{section.emptyText}</div>
            ) : (
              <div className="queueList">
                {section.items.map((location) => (
                  <button
                    key={location.locationId}
                    type="button"
                    className={`queueItem ${selectedLocationId === location.locationId ? "queueItemActive" : ""}`}
                    onClick={() => onSelectLocation(location.locationId)}
                  >
                    <div className="queueItemHeader">
                      <div>
                        <div className="queueItemTitle">{location.label}</div>
                        <p className="mutedLine">{location.zone}</p>
                      </div>
                      <span className={locationTypeClass(location.type)}>{location.type.replace("_", " ")}</span>
                    </div>
                    <div className="queueItemMeta">
                      <span className={locationStatusClass(location.uiStatus)}>{location.uiStatus}</span>
                      <span>{location.counts.ordersTotal} orders</span>
                      <span>{formatMoneyValue(location.totals)}</span>
                    </div>
                    <div className="queueItemMeta mutedLine">
                      <span>Opened {formatTimestamp(location.openedAt)}</span>
                      <span>Last order {formatTimestamp(location.lastOrderAt)}</span>
                    </div>
                    {location.assignmentState === "UNASSIGNED" && mode === "SERVICE" ? (
                      <div className="inlineNote">Assignment is not persisted yet. Treat this as an unclaimed service session.</div>
                    ) : null}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
