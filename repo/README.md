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

## Run & Verify (ROP-004)

### Prereqs

- Docker + Docker Compose installed
- `pnpm` installed

### Terminal 1 - Infrastructure + Backend

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

### Terminal 2 - Web Ordering App

Open a new terminal and run in parallel:

```bash
cd repo/frontend
pnpm i
pnpm --filter web-ordering dev -- --port 5173
```

Web ordering UI runs on `http://localhost:5173`.

### Terminal 3 - Kitchen Dashboard

Open another terminal and run in parallel:

```bash
cd repo/frontend
pnpm --filter dashboard dev -- --port 5174
```

Dashboard UI runs on `http://localhost:5174`.

Dashboard env (`repo/frontend/apps/dashboard/.env` or `.env.local`):

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

### Verification Checklist

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

4. Realtime check in browser:

- Open dashboard at `http://localhost:5174`.
- Confirm it shows `Connection: Connected`.
- Run the place-order curl command again.
- Confirm a new order appears in the dashboard within 2 seconds.
- Run accept/ready curls and confirm status updates to `ACCEPTED` then `READY`.

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
