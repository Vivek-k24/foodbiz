import { useEffect, useState } from "react";

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
          <p className="eyebrow">Public Restaurant Surface</p>
          <h1 className="title">{restaurant?.name ?? "FoodBiz Restaurant"}</h1>
          <p className="subtitle">
            Lightweight public shell for the restaurant website boundary. Ordering remains its own
            browser surface, while staff and kitchen stay operationally separate.
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
            <span className="label">Surface status</span>
            <strong>Boundary shell</strong>
          </div>
        </div>
      </section>

      <section className="grid">
        <article className="card panel">
          <p className="eyebrow">About</p>
          <h2 className="sectionTitle">Public-facing homepage shell</h2>
          <p className="bodyText">
            This app establishes the product boundary for the eventual restaurant website. It should
            hold branding, business information, and public calls to action, not staff or kitchen workflows.
          </p>
        </article>

        <article className="card panel">
          <p className="eyebrow">Order online</p>
          <h2 className="sectionTitle">Customer ordering entry points</h2>
          <div className="buttonGroup">
            <a className="primaryButton" href={`${webOrderingBaseUrl}?mode=pickup`}>
              Start pickup order
            </a>
            <a className="secondaryButton" href={`${webOrderingBaseUrl}?mode=delivery`}>
              Start delivery order
            </a>
          </div>
          <p className="bodyText">
            Dine-in scan links should point to the same web-ordering app with table or location context.
          </p>
        </article>

        <article className="card panel">
          <p className="eyebrow">Deferred</p>
          <h2 className="sectionTitle">What is intentionally not here yet</h2>
          <ul className="list">
            <li>Marketing-heavy branding and hero content</li>
            <li>Hours, address, and specials management</li>
            <li>Reservation or CRM workflows</li>
            <li>Any staff, kitchen, or operational controls</li>
          </ul>
        </article>
      </section>
    </main>
  );
}

export default App;
