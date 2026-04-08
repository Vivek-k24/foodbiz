import type { MoneyPayload, OrderLineModifierPayload, OrderPayload } from "./types";

export function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

export function formatMoneyValue(money: MoneyPayload | null | undefined): string {
  if (!money || typeof money.amountCents !== "number" || typeof money.currency !== "string") {
    return "-";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: money.currency,
  }).format(money.amountCents / 100);
}

export function normalizeOrder(order: OrderPayload): OrderPayload {
  return {
    ...order,
    lines: Array.isArray(order.lines) ? order.lines : [],
    totalMoney: order.totalMoney ?? order.total ?? null,
  };
}

export function getOrderMoney(order: OrderPayload): MoneyPayload | null | undefined {
  return order.totalMoney ?? order.total;
}

export function formatModifierValue(modifier: OrderLineModifierPayload): string {
  return modifier.value === "true" ? modifier.label : `${modifier.label}: ${modifier.value}`;
}

export function maxTimestamp(
  left: string | null | undefined,
  right: string | null | undefined
): string | null {
  if (!left && !right) {
    return null;
  }
  if (!left) {
    return right ?? null;
  }
  if (!right) {
    return left;
  }
  return new Date(left).getTime() >= new Date(right).getTime() ? left : right;
}
