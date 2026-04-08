import { useEffect, useState } from "react";

import { buildOrderingHref } from "./lib/routing";

type Restaurant = {
  restaurantId: string;
  name: string;
  timezone: string;
  currency: string;
  createdAt: string;
};

type RestaurantsResponse = {
  restaurants: Restaurant[];
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const webOrderingBaseUrl = import.meta.env.VITE_WEB_ORDERING_URL ?? "http://localhost:5173";

function App() {
  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadRestaurant(): Promise<void> {
      try {
        const response = await fetch(`${apiBaseUrl}/v1/restaurants`);
        if (!response.ok) {
          throw new Error(`request failed (${response.status})`);
        }
        const payload = (await response.json()) as RestaurantsResponse;
        if (active) {
          setRestaurant(payload.restaurants[0] ?? null);
        }
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "failed to load restaurant");
        }
      }
    }

    void loadRestaurant();
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="siteRoot">
      <section className="hero card">
        <div>
          <p className="eyebrow">FoodBiz Restaurant</p>
          <h1 className="title">{restaurant?.name ?? "FoodBiz Restaurant"}</h1>
          <p className="subtitle">
            Fresh kitchen service, casual hospitality, and a clear path to order online for pickup
            or delivery.
          </p>
          {error ? <div className="infoBox">Live restaurant metadata is unavailable: {error}</div> : null}
        </div>
        <div className="heroMeta">
          <div className="metaCard">
            <span className="label">Timezone</span>
            <strong>{restaurant?.timezone ?? "America/Chicago"}</strong>
          </div>
          <div className="metaCard">
            <span className="label">Currency</span>
            <strong>{restaurant?.currency ?? "USD"}</strong>
          </div>
          <div className="metaCard">
            <span className="label">Cuisine</span>
            <strong>Italian, Greek, French, Mexican, Western</strong>
          </div>
        </div>
      </section>

      <section className="grid">
        <article className="card panel">
          <p className="eyebrow">Welcome</p>
          <h2 className="sectionTitle">A customer-facing restaurant website</h2>
          <p className="bodyText">
            Explore the menu, plan a pickup, or place a delivery order without touching any internal
            staff or kitchen workflows.
          </p>
        </article>

        <article className="card panel">
          <p className="eyebrow">Order online</p>
          <h2 className="sectionTitle">Choose how you want to order</h2>
          <div className="buttonGroup">
            <a className="primaryButton" href={buildOrderingHref(webOrderingBaseUrl, "pickup")}>
              Order Pickup
            </a>
            <a className="secondaryButton" href={buildOrderingHref(webOrderingBaseUrl, "delivery")}>
              Order Delivery
            </a>
          </div>
          <p className="bodyText">
            Dining-room QR codes should land in the same ordering flow with table context already attached.
          </p>
        </article>

        <article className="card panel">
          <p className="eyebrow">Visit</p>
          <h2 className="sectionTitle">Simple public details</h2>
          <ul className="list">
            <li>123 Service Lane, Chicago, IL</li>
            <li>Open daily, 11:00 AM to 10:00 PM</li>
            <li>Call (555) 010-0140 for group dining or large pickup orders</li>
            <li>Internal staff and kitchen tools stay on separate browser surfaces</li>
          </ul>
        </article>
      </section>
    </main>
  );
}

export default App;
