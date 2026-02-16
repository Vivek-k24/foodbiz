# Restaurant Operating Platform (ROP)

## Architecture Layers
- `backend/src/rop/domain`: pure business rules. No framework, transport, persistence, or observability imports.
- `backend/src/rop/application`: use-case orchestration and ports (`backend/src/rop/application/ports`).
- `backend/src/rop/infrastructure`: adapters for DB, cache, logging, telemetry.
- `backend/src/rop/api`: HTTP transport only (thin routes that call application/use-case code).

## Local Workflow
```bash
cd repo
make up
make down
make lint
make typecheck
make test
make depcheck
```

## Run & Verify (ROP-003)
Prereqs:
- docker + docker compose installed
- pnpm installed (or npm/yarn if project uses them)

### Terminal 1 — Infrastructure + Backend
```bash
cd repo
make up
make migrate
make seed
```
Explain:
- `make up` starts postgres/redis/jaeger/prometheus/grafana AND the backend container (uvicorn --reload)
- Backend should be reachable at http://localhost:8000
Verify (copy/paste):
```bash
curl -s http://localhost:8000/health/live
curl -s http://localhost:8000/health/ready
curl -s http://localhost:8000/metrics | head
```

### Terminal 2 — Kitchen Dashboard (Frontend)
Open a new terminal window/tab and run in parallel:
```bash
cd repo/frontend
pnpm i
pnpm --filter dashboard dev
```
Explain:
- Dashboard dev server URL (Vite prints it; typically http://localhost:5173)
- Ensure .env is set:
  - VITE_API_BASE_URL=http://localhost:8000
  - VITE_WS_BASE_URL=ws://localhost:8000

### Verification — Place Order → Dashboard receives realtime event
Option A (HTTP only quick check):
```bash
curl -i -X POST http://localhost:8000/v1/restaurants/rst_001/tables/tbl_001/open
curl -i -X POST http://localhost:8000/v1/restaurants/rst_001/tables/tbl_001/orders \
  -H 'Content-Type: application/json' \
  -d '{"lines":[{"itemId":"itm_001","quantity":1}]}'
```

Option B (Realtime check in browser):
- Open dashboard in browser
- Confirm it shows “Connected” (add a simple status indicator in UI if not already)
- Run the place-order curl above
- Confirm a new order appears in the dashboard within 2 seconds

### Observability quick checks
- Jaeger traces: http://localhost:16686 (service name rop-backend)
- Prometheus: http://localhost:9090 (targets show backend UP)
- Grafana: http://localhost:3000 (admin/admin)

### Troubleshooting notes
- If dashboard connects but no events arrive:
  - confirm Redis is up in docker compose
  - confirm backend WS endpoint: ws://localhost:8000/ws?restaurant_id=rst_001&role=KITCHEN
  - check backend logs: make logs
- If /health/ready is 503:
  - confirm postgres/redis containers are healthy: docker compose ps

## Endpoints
- Live health: `GET http://localhost:8000/health/live`
- Ready health: `GET http://localhost:8000/health/ready`
- Metrics: `GET http://localhost:8000/metrics`

## Observability UIs
- Jaeger: http://localhost:16686
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (`admin` / `admin`)
