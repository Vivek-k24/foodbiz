import { formatMoneyValue, formatTimestamp } from "../lib/formatting";
import type { QueueSection, StaffMode } from "../lib/types";
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
      <div className="paneHeader stickyPaneHeader">
        <div>
          <p className="eyebrow">Operational queue</p>
          <h2 className="paneTitle">{mode === "ENTRANCE" ? "Arrivals and occupancy" : "Service follow-through"}</h2>
          <p className="paneHint">
            {mode === "ENTRANCE"
              ? "Seat guests quickly, spot open sessions, and keep turnover visible without crossing into kitchen prep controls."
              : "Spot ready handoff points, served tables, and unclaimed sessions without taking ownership of kitchen Accept or Ready steps."}
          </p>
        </div>
      </div>

      <div className="paneScroll">
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
                      className={`queueItem queueItem${location.uiStatus} ${selectedLocationId === location.locationId ? "queueItemActive" : ""}`}
                      onClick={() => onSelectLocation(location.locationId)}
                    >
                      <div className={`queueStatusRail queueStatusRail${location.uiStatus}`} aria-hidden="true" />
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
                        <div className="inlineNote">
                          Waiter ownership is not persisted yet. Treat this as an unclaimed service session.
                        </div>
                      ) : null}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
