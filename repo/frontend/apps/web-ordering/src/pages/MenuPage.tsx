import { useEffect, useMemo, useState } from "react";

type Money = {
  amountCents: number;
  currency: string;
};

type MenuItem = {
  itemId: string;
  name: string;
  description?: string | null;
  priceMoney: Money;
  isAvailable: boolean;
  categoryId?: string | null;
};

type MenuResponse = {
  menuId: string;
  restaurantId: string;
  menuVersion: number;
  items: MenuItem[];
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function formatMoney(money: Money): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: money.currency
  }).format(money.amountCents / 100);
}

export function MenuPage() {
  const [menu, setMenu] = useState<MenuResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [placingOrder, setPlacingOrder] = useState(false);
  const [orderResult, setOrderResult] = useState<string | null>(null);

  const endpoint = useMemo(
    () => `${apiBaseUrl}/v1/restaurants/rst_001/menu`,
    []
  );
  const placeOrderEndpoint = useMemo(
    () => `${apiBaseUrl}/v1/restaurants/rst_001/tables/tbl_001/orders`,
    []
  );

  useEffect(() => {
    let active = true;
    async function loadMenu() {
      setLoading(true);
      try {
        const response = await fetch(endpoint);
        if (!response.ok) {
          throw new Error(`menu request failed (${response.status})`);
        }
        const payload = (await response.json()) as MenuResponse;
        if (active) {
          setMenu(payload);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "unknown error");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }
    void loadMenu();
    return () => {
      active = false;
    };
  }, [endpoint]);

  async function placeTestOrder(): Promise<void> {
    setPlacingOrder(true);
    setOrderResult(null);
    try {
      const response = await fetch(placeOrderEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lines: [{ itemId: "itm_001", quantity: 1 }] })
      });
      if (!response.ok) {
        throw new Error(`order request failed (${response.status})`);
      }
      const payload = (await response.json()) as { orderId: string };
      setOrderResult(`Created order ${payload.orderId}`);
    } catch (err) {
      setOrderResult(err instanceof Error ? err.message : "order failed");
    } finally {
      setPlacingOrder(false);
    }
  }

  if (loading) {
    return <main><p>Loading menu...</p></main>;
  }
  if (error) {
    return <main><p>Failed to load menu: {error}</p></main>;
  }
  if (!menu) {
    return <main><p>No menu available.</p></main>;
  }

  return (
    <main>
      <h1>Restaurant Menu</h1>
      <p>Restaurant: {menu.restaurantId}</p>
      <p>Version: {menu.menuVersion}</p>
      <button type="button" onClick={() => void placeTestOrder()} disabled={placingOrder}>
        {placingOrder ? "Placing..." : "Place test order"}
      </button>
      {orderResult ? <p>{orderResult}</p> : null}
      <ul>
        {menu.items.map((item) => (
          <li key={item.itemId}>
            <strong>{item.name}</strong>{" "}
            <span>{formatMoney(item.priceMoney)}</span>
            {!item.isAvailable ? <em> (unavailable)</em> : null}
          </li>
        ))}
      </ul>
    </main>
  );
}
