import { formatModifierValue, formatMoneyValue, formatTimestamp, getOrderMoney } from "../lib/formatting";
import type { OrderAction, OrderPayload, StaffLocation, StaffMode, TableSummaryResponse } from "../lib/types";
import { locationStatusClass, locationTypeClass, orderStatusClass } from "./StatusBadge";

function orderActionForStatus(status: string): { action: OrderAction; label: string } | null {
  switch (status) {
    case "PLACED":
      return { action: "accept", label: "Accept" };
    case "ACCEPTED":
      return { action: "ready", label: "Mark Ready" };
    case "READY":
      return { action: "served", label: "Mark Served" };
    case "SERVED":
      return { action: "settled", label: "Mark Settled" };
    default:
      return null;
  }
}

type DetailPaneProps = {
  mode: StaffMode;
  location: StaffLocation | null;
  summary: TableSummaryResponse | null;
  orders: OrderPayload[];
  loading: boolean;
  error: string | null;
  message: string | null;
  locationActionPending: "open" | "close" | null;
  orderActionPending: Record<string, boolean>;
  orderActionError: Record<string, string>;
  onOpenLocation: () => void;
  onCloseLocation: () => void;
  onOrderAction: (order: OrderPayload, action: OrderAction) => void;
};

export function DetailPane({
  mode,
  location,
  summary,
  orders,
  loading,
  error,
  message,
  locationActionPending,
  orderActionPending,
  orderActionError,
  onOpenLocation,
  onCloseLocation,
  onOrderAction,
}: DetailPaneProps) {
  if (!location) {
    return (
      <aside className="shellPane cardSurface detailPane">
        <div className="paneHeader">
          <div>
            <p className="eyebrow">Detail pane</p>
            <h2 className="paneTitle">No location selected</h2>
          </div>
        </div>
        <div className="emptyBox">Choose a location from the queue or floor pane to inspect its session, order history, and supported actions.</div>
      </aside>
    );
  }

  const actionCopy =
    mode === "ENTRANCE"
      ? "Entrance mode prioritizes seating, occupancy, and quick session handling."
      : "Service mode prioritizes live order progress, attention items, and session follow-through.";

  return (
    <aside className="shellPane cardSurface detailPane">
      <div className="paneHeader">
        <div>
          <p className="eyebrow">Detail pane</p>
          <h2 className="paneTitle">{location.label}</h2>
          <p className="paneHint">{actionCopy}</p>
        </div>
      </div>

      {loading ? <div className="infoBox">Loading location detail...</div> : null}
      {message ? <div className="infoBox">{message}</div> : null}
      {error ? <div className="errorBox">{error}</div> : null}

      <div className="detailHeaderCard">
        <div className="detailHeaderRow">
          <div>
            <div className="detailLocationName">{location.label}</div>
            <p className="mutedLine monoLine">{location.locationId}</p>
          </div>
          <div className="badgeRow">
            <span className={locationTypeClass(location.type)}>{location.type.replace("_", " ")}</span>
            <span className={locationStatusClass(location.uiStatus)}>{location.uiStatus}</span>
          </div>
        </div>

        <div className="detailStatsGrid">
          <div className="detailStat">
            <span className="tileLabel">Zone</span>
            <strong>{location.zone}</strong>
          </div>
          <div className="detailStat">
            <span className="tileLabel">Seats</span>
            <strong>{location.seatCount}</strong>
          </div>
          <div className="detailStat">
            <span className="tileLabel">Session</span>
            <strong>{location.sessionOpen ? "Open" : location.manualOnly ? "Manual" : "Closed"}</strong>
          </div>
          <div className="detailStat">
            <span className="tileLabel">Assignment</span>
            <strong>
              {location.assignmentState === "UNASSIGNED"
                ? "Unassigned"
                : location.assignmentState === "MANUAL_ONLY"
                  ? "Manual"
                  : "Not applicable"}
            </strong>
          </div>
          <div className="detailStat">
            <span className="tileLabel">Opened</span>
            <strong>{formatTimestamp(summary?.openedAt ?? location.openedAt)}</strong>
          </div>
          <div className="detailStat">
            <span className="tileLabel">Last order</span>
            <strong>{formatTimestamp(summary?.lastOrderAt ?? location.lastOrderAt)}</strong>
          </div>
        </div>
      </div>

      {location.manualOnly ? (
        <div className="infoBox">
          Bar seats are represented in the floor model, but backend session/order persistence for bar service has not been introduced yet. Treat this as a manual visibility surface for now.
        </div>
      ) : null}

      {location.kioskLinked ? (
        <div className="infoBox">
          This location is marked as kiosk-capable. No kiosk client ships in this ROP, but the console keeps the session/location model compatible with one later.
        </div>
      ) : null}

      {location.assignmentState === "UNASSIGNED" ? (
        <div className="inlineNote">
          Waiter ownership is not persisted in the backend yet. Service mode surfaces these sessions as unassigned so future assignment logic can attach here cleanly.
        </div>
      ) : null}

      <div className="detailActionsRow">
        <button
          type="button"
          className="primaryButton"
          disabled={location.manualOnly || location.sessionOpen || locationActionPending !== null}
          onClick={onOpenLocation}
        >
          {locationActionPending === "open" ? "Opening..." : "Open Session"}
        </button>
        <button
          type="button"
          className="secondaryButton"
          disabled={location.manualOnly || !location.sessionOpen || locationActionPending !== null}
          onClick={onCloseLocation}
        >
          {locationActionPending === "close" ? "Closing..." : "Close Session"}
        </button>
      </div>

      <div className="detailSection">
        <div className="sectionHeaderCompact">
          <h3 className="sectionTitleSmall">Session summary</h3>
          <span className="badge">{summary?.counts.ordersTotal ?? location.counts.ordersTotal} orders</span>
        </div>

        <div className="detailStatsGrid">
          <div className="detailStat">
            <span className="tileLabel">Gross total</span>
            <strong>{formatMoneyValue(summary?.totals ?? location.totals)}</strong>
          </div>
          <div className="detailStat">
            <span className="tileLabel">Placed</span>
            <strong>{summary?.counts.placed ?? location.counts.placed}</strong>
          </div>
          <div className="detailStat">
            <span className="tileLabel">Accepted</span>
            <strong>{summary?.counts.accepted ?? location.counts.accepted}</strong>
          </div>
          <div className="detailStat">
            <span className="tileLabel">Ready</span>
            <strong>{summary?.counts.ready ?? location.counts.ready}</strong>
          </div>
          <div className="detailStat">
            <span className="tileLabel">Served</span>
            <strong>{location.counts.served}</strong>
          </div>
          <div className="detailStat">
            <span className="tileLabel">Settled</span>
            <strong>{location.counts.settled}</strong>
          </div>
        </div>
      </div>

      <div className="detailSection">
        <div className="sectionHeaderCompact">
          <h3 className="sectionTitleSmall">Recent orders</h3>
          <span className="badge">{orders.length}</span>
        </div>

        {orders.length === 0 ? (
          <div className="emptyBox">
            {location.manualOnly
              ? "No backend-managed order history is available for manual bar seats."
              : "No orders have been recorded for this location yet."}
          </div>
        ) : (
          <div className="detailOrderList">
            {orders.map((order) => {
              const action = orderActionForStatus(order.status);
              const pending = orderActionPending[order.orderId] === true;
              const actionError = orderActionError[order.orderId];

              return (
                <article key={order.orderId} className="detailOrderCard">
                  <div className="detailHeaderRow">
                    <div>
                      <div className="detailLocationName monoLine">{order.orderId}</div>
                      <p className="mutedLine">Created {formatTimestamp(order.createdAt)}</p>
                    </div>
                    <span className={orderStatusClass(order.status)}>{order.status}</span>
                  </div>

                  <div className="orderSummaryRow mutedLine">
                    <span>Total {formatMoneyValue(getOrderMoney(order))}</span>
                    <span>{order.lines.length} line items</span>
                  </div>

                  <ul className="orderLineList">
                    {order.lines.map((line) => (
                      <li key={line.lineId} className="orderLineItem">
                        <div>
                          <span className="monoLine">{line.quantity}x</span> {line.name}
                        </div>
                        {Array.isArray(line.modifiers) && line.modifiers.length > 0 ? (
                          <div className="chipGroup">
                            {line.modifiers.map((modifier) => (
                              <span
                                key={`${line.lineId}-${modifier.code}-${modifier.value}`}
                                className="miniChip"
                              >
                                {formatModifierValue(modifier)}
                              </span>
                            ))}
                          </div>
                        ) : null}
                        {typeof line.notes === "string" && line.notes.trim() ? (
                          <p className="mutedLine">Notes: {line.notes}</p>
                        ) : null}
                      </li>
                    ))}
                  </ul>

                  {action ? (
                    <div className="detailActionsRow">
                      <button
                        type="button"
                        className="secondaryButton"
                        disabled={pending}
                        onClick={() => onOrderAction(order, action.action)}
                      >
                        {pending ? "Updating..." : action.label}
                      </button>
                    </div>
                  ) : null}

                  {actionError ? <div className="errorBox">{actionError}</div> : null}
                </article>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
}
