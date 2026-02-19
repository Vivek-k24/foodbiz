# FoodBiz

FoodBiz is a domain-first Restaurant Operating Platform monorepo.

## Architecture Layers

Backend follows strict clean boundaries:

- `domain/`: pure business logic and invariants only.
- `application/`: use cases, ports, DTOs, and mapping.
- `infrastructure/`: adapters for Postgres, Redis, observability.
- `api/`: FastAPI HTTP/WS routes that orchestrate use cases only.

Domain dependency policy is enforced by `make depcheck`.

## Core Local Commands

From `repo/`:

- `make up`
- `make down`
- `make logs`
- `make migrate`
- `make seed`
- `make lint`
- `make typecheck`
- `make test`
- `make test-integration`
- `make depcheck`

## Service URLs

- Backend API: `http://localhost:8000`
- Jaeger: `http://localhost:16686`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (`admin/admin`)

## Run & Verify (ROP-006)

### Prereqs

- Docker + Docker Compose installed
- `pnpm` installed

### Terminal A - Infrastructure + Backend

Run in `repo/`:

```bash
cd repo
make up
make migrate
make seed
```

`make up` starts `postgres`, `redis`, `jaeger`, `prometheus`, `grafana`, and `backend` (`uvicorn --reload`).

Backend should be reachable at `http://localhost:8000`.

Quick health checks:

```bash
curl -s http://localhost:8000/health/live
curl -s http://localhost:8000/health/ready
curl -s http://localhost:8000/metrics | head
```

### Terminal B - Kitchen Dashboard

Open a new terminal and run in parallel:

```bash
cd repo/frontend
pnpm i
pnpm --filter dashboard dev -- --port 5174
```

Dashboard runs on `http://localhost:5174`.

### Terminal C (Optional) - Web Ordering App

Open another terminal and run in parallel if you want to place orders from UI:

```bash
cd repo/frontend
pnpm --filter web-ordering dev -- --port 5173
```

Web ordering runs on `http://localhost:5173`.

Dashboard env (`repo/frontend/apps/dashboard/.env` or `.env.local`):

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

Web ordering env (`repo/frontend/apps/web-ordering/.env` or `.env.local`):

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

### Verification Checklist (ROP-006)

1. Open table (idempotent):

```bash
curl -i -X POST http://localhost:8000/v1/restaurants/rst_001/tables/tbl_001/open
```

2. Place order and capture `orderId` from response:

```bash
curl -i -X POST http://localhost:8000/v1/restaurants/rst_001/tables/tbl_001/orders \
  -H 'Content-Type: application/json' \
  -d '{"lines":[{"itemId":"itm_001","quantity":1}]}'
```

3. Accept and mark ready (replace `<ORDER_ID>`):

```bash
curl -i -X POST http://localhost:8000/v1/orders/<ORDER_ID>/accept
curl -i -X POST http://localhost:8000/v1/orders/<ORDER_ID>/ready
curl -i http://localhost:8000/v1/orders/<ORDER_ID>
```

4. Verify table order history re-hydration endpoint:

```bash
curl -i "http://localhost:8000/v1/restaurants/rst_001/tables/tbl_001/orders?status=ALL&limit=10"
```

5. Close table guardrail (blocked while non-ready orders exist):

```bash
curl -i -X POST http://localhost:8000/v1/restaurants/rst_001/tables/tbl_001/close
```

Expected while non-ready orders exist: `409` with `TABLE_CLOSE_BLOCKED`.

6. After all orders are `READY`, close table:

```bash
curl -i -X POST http://localhost:8000/v1/restaurants/rst_001/tables/tbl_001/close
```

7. Verify receipt-style summary:

```bash
curl -i http://localhost:8000/v1/restaurants/rst_001/tables/tbl_001/summary
```

8. Realtime + UI re-hydration checks in browser:

- Open dashboard at `http://localhost:5174`.
- Confirm it shows `Connection: Connected`.
- Place a new order (curl or web-ordering UI).
- Confirm the order appears in dashboard within 2 seconds.
- Run accept/ready curls and confirm status transitions update live.
- Refresh the dashboard page and verify queue + table orders re-hydrate from REST.
- Click `Close Table` in dashboard after orders are READY and verify summary/status update.

### Observability Quick Checks

- Jaeger traces: `http://localhost:16686` (service `rop-backend`)
- Prometheus targets: `http://localhost:9090`
- Grafana: `http://localhost:3000` (`admin/admin`)

### Troubleshooting

- If dashboard connects but no events arrive:
  - verify Redis is up: `docker compose ps`
  - verify WS endpoint: `ws://localhost:8000/ws?restaurant_id=rst_001&role=KITCHEN`
  - inspect backend logs: `make logs`
- If `/health/ready` returns `503`:
  - confirm Postgres and Redis containers are running: `docker compose ps`
- If frontend ports conflict:
  - run web-ordering on `5173` and dashboard on `5174` explicitly using `--port`.

## Run & Verify (ROP-007)

### Terminal A - Infrastructure + Backend

```bash
cd repo
make up
make migrate
make seed
```

### Terminal B - Dashboard

Run in parallel:

```bash
cd repo/frontend
pnpm i
pnpm --filter dashboard dev -- --port 5174
```

Dashboard URL: `http://localhost:5174`

### Verification Checklist (Copy/Paste)

1. Open a new table:

```bash
curl -i -X POST http://localhost:8000/v1/restaurants/rst_001/tables/tbl_002/open
```

2. List OPEN tables:

```bash
curl -s "http://localhost:8000/v1/restaurants/rst_001/tables?status=OPEN&limit=50"
```

3. Place an order on `tbl_002`:

```bash
curl -i -X POST "http://localhost:8000/v1/restaurants/rst_001/tables/tbl_002/orders" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: rop007-smoke-001" \
  -d '{"lines":[{"itemId":"itm_001","quantity":1}],"note":"rop-007 smoke"}'
```

4. Accept and mark ready (replace `<ORDER_ID>`):

```bash
curl -i -X POST http://localhost:8000/v1/orders/<ORDER_ID>/accept
curl -i -X POST http://localhost:8000/v1/orders/<ORDER_ID>/ready
```

5. List OPEN tables again and confirm `tbl_002` has `lastOrderAt`:

```bash
curl -s "http://localhost:8000/v1/restaurants/rst_001/tables?status=OPEN&limit=50"
```

6. Close `tbl_002` and list CLOSED tables:

```bash
curl -i -X POST http://localhost:8000/v1/restaurants/rst_001/tables/tbl_002/close
curl -s "http://localhost:8000/v1/restaurants/rst_001/tables?status=CLOSED&limit=50"
```

7. Dashboard sanity checks:

- Open `http://localhost:5174` and switch to `TABLES`.
- Confirm `tbl_002` appears and updates as events arrive.
- Refresh the page and confirm tables are re-hydrated from REST.
- Click a table row and confirm selected table orders/summary hydrate.
