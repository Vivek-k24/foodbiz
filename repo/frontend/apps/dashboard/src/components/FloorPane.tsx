import { formatMoneyValue, formatTimestamp } from "../lib/formatting";
import type { StaffLocation } from "../lib/types";
import { locationStatusClass, locationTypeClass } from "./StatusBadge";

type FloorPaneProps = {
  groupedLocations: Array<{
    zone: string;
    items: StaffLocation[];
  }>;
  selectedLocationId: string;
  onSelectLocation: (locationId: string) => void;
  loading: boolean;
  error: string | null;
};

export function FloorPane({
  groupedLocations,
  selectedLocationId,
  onSelectLocation,
  loading,
  error,
}: FloorPaneProps) {
  return (
    <section className="shellPane cardSurface floorPane">
      <div className="paneHeader stickyPaneHeader">
        <div>
          <p className="eyebrow">Live floor</p>
          <h2 className="paneTitle">Location map</h2>
          <p className="paneHint">
            Dining tables, manual bar seats, and off-premise lanes share one browser floor model
            without pretending they all run the same workflow.
          </p>
        </div>
      </div>

      <div className="paneScroll">
        {loading ? <div className="infoBox">Refreshing venue state...</div> : null}
        {error ? <div className="errorBox">{error}</div> : null}
        {groupedLocations.length === 0 ? <div className="emptyBox">No locations match the current filters.</div> : null}

        <div className="zoneStack">
          {groupedLocations.map((group) => (
            <section key={group.zone} className="zoneSection">
              <div className="sectionHeaderCompact">
                <h3 className="sectionTitleSmall">{group.zone}</h3>
                <span className="badge">{group.items.length}</span>
              </div>
              <div className={`locationGrid ${group.zone === "Bar Counter" ? "locationGridBar" : ""}`}>
                {group.items.map((location) => (
                  <button
                    key={location.locationId}
                    type="button"
                    className={`locationTile locationTile${location.uiStatus} ${
                      selectedLocationId === location.locationId ? "locationTileActive" : ""
                    }`}
                    onClick={() => onSelectLocation(location.locationId)}
                  >
                    <div className={`locationStatusRail locationStatusRail${location.uiStatus}`} aria-hidden="true" />
                    <div className="locationTileHeader">
                      <div>
                        <div className="locationTileTitle">{location.label}</div>
                        <p className="mutedLine monoLine">{location.locationId}</p>
                      </div>
                      <span className={locationTypeClass(location.type)}>{location.type.replace("_", " ")}</span>
                    </div>

                    <div className="locationTileMeta">
                      <span className={locationStatusClass(location.uiStatus)}>{location.uiStatus}</span>
                      <span>{location.seatCount > 0 ? `${location.seatCount} seats` : "No seating"}</span>
                    </div>

                    <div className="tileStats">
                      <div>
                        <span className="tileLabel">Session</span>
                        <strong>
                          {location.manualOnly
                            ? "Manual"
                            : location.sessionOpen
                              ? "Open"
                              : location.type === "TABLE"
                                ? "Closed"
                                : "N/A"}
                        </strong>
                      </div>
                      <div>
                        <span className="tileLabel">Orders</span>
                        <strong>{location.counts.ordersTotal}</strong>
                      </div>
                      <div>
                        <span className="tileLabel">Total</span>
                        <strong>{formatMoneyValue(location.totals)}</strong>
                      </div>
                    </div>

                    <div className="tileTimestamps mutedLine">
                      <span>Opened {formatTimestamp(location.openedAt)}</span>
                      <span>Last order {formatTimestamp(location.lastOrderAt)}</span>
                    </div>

                    {location.scanEnabled ? (
                      <div className="inlineNote">Scan-enabled table entry is supported through web ordering, not kiosk hardware.</div>
                    ) : null}
                  </button>
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </section>
  );
}
