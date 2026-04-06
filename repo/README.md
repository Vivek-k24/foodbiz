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

## CI/CD and Staging

GitHub Actions workflows live at repository root `.github/workflows/` because GitHub only loads workflows from the repository root. Those workflows target this monorepo under `repo/`.

### Workflow Purpose

- `CI`:
  - runs on pull requests to `main`
  - runs on pushes to branches, including `main`
  - checks backend lint, typecheck, depcheck, unit tests, integration tests
  - installs and builds frontend apps
- `Release Staging`:
  - runs automatically only after `CI` succeeds on `main`
  - also supports manual `workflow_dispatch`
  - builds and publishes the backend image to GHCR
  - deploys only to the `staging` GitHub Environment over SSH
  - runs post-deploy smoke checks

### Current Deployment Scope

- deployed image: backend only
- image registry: GHCR
- staging runtime: one Linux Docker host reachable by SSH
- deployment method: pull published image + restart with `repo/deploy/staging/docker-compose.staging.yml`

Frontend apps are built in CI but intentionally not deployed in staging yet because they are not containerized for staging runtime.

### Required GitHub Environment

Create a GitHub Environment named `staging`.

Environment variables:

- `STAGING_HOST`
- `STAGING_USER`
- `STAGING_PORT` (optional, default `22`)
- `STAGING_APP_DIR`
- `STAGING_BASE_URL` (optional)
- `STAGING_RUN_SEED` (optional, default `true`)

Environment secrets:

- `STAGING_SSH_PRIVATE_KEY`
- `STAGING_ENV_FILE`

`STAGING_ENV_FILE` should contain the values described in `repo/deploy/staging/.env.staging.example`.

### Staging Deploy Flow

Automatic deploy:

1. Push to `main`.
2. `CI` completes successfully.
3. `Release Staging` builds `ghcr.io/<owner>/foodbiz-backend:<short_sha>`, `:main`, and `:staging`.
4. The workflow copies:
   - `repo/deploy/staging/docker-compose.staging.yml`
   - `repo/scripts/deploy_staging.sh`
   - `repo/scripts/smoke_staging.sh`
   - the secret-backed staging env file
5. The host runs migrations, optional deterministic seed, backend restart, and smoke checks.

Manual deploy:

1. Open `Release Staging` in GitHub Actions.
2. Click `Run workflow`.
3. Leave `image_tag` empty to build and deploy current `main`.
4. Set `image_tag` to a previously published short SHA to redeploy an older backend image.

### Rollback Flow

Rollback is intentionally simple and real:

1. Open `Release Staging`.
2. Run it manually.
3. Supply a previously published short-SHA image tag in `image_tag`.
4. The workflow redeploys that exact image to staging.

The host also keeps the previous runtime env snapshot at `${STAGING_APP_DIR}/.env.previous`, which is useful for debugging, but the supported rollback path is the manual GitHub Actions redeploy.

### Host Inspection

On the staging host:

```bash
cd "$STAGING_APP_DIR"
docker compose --env-file .env -f deploy/staging/docker-compose.staging.yml ps
docker compose --env-file .env -f deploy/staging/docker-compose.staging.yml logs --tail=200 backend
docker compose --env-file .env -f deploy/staging/docker-compose.staging.yml logs --tail=200 postgres
docker compose --env-file .env -f deploy/staging/docker-compose.staging.yml logs --tail=200 redis
```

### Failed Run Inspection

- GitHub Actions job logs show the exact failed step.
- CI uploads failure artifacts for backend quality, backend unit tests, backend integration tests, and frontend builds.
- Staging deploy and smoke logs are emitted directly in the workflow output.

### More Detail

See `repo/docs/staging.md` for host prerequisites, smoke scope, rollback, and troubleshooting detail.

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

## Run & Verify (ROP-008)

### Terminal A - Infrastructure + Backend

```bash
cd repo
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m rop.tools.seed
```

### Terminal B - Dashboard

```bash
cd repo/frontend
pnpm i
pnpm --filter dashboard dev -- --port 5174
```

Dashboard URL: `http://localhost:5174`

### Terminal C - Web Ordering

```bash
cd repo/frontend
pnpm --filter web-ordering dev -- --port 5173
```

Web ordering URL: `http://localhost:5173`

### Verification Checklist (UI Only)

1. Open dashboard at `http://localhost:5174` and switch to `TABLES`.
2. Enter `tbl_002` in the table input and click `Open Table`.
3. Confirm `tbl_002` appears as `OPEN` in the tables list.
4. Open web ordering at `http://localhost:5173`, enter `tbl_002`, and click `Place test order`.
5. Confirm `My Table Orders` in web ordering shows the new order for `tbl_002`.
6. Return to dashboard, switch to `KITCHEN`, and in the `PLACED` tab click `Accept`.
7. Switch to the `ACCEPTED` tab and click `Mark Ready` for the same order.
8. Switch back to `TABLES`, select `tbl_002`, and click `Close Table`.
9. Refresh both UIs and confirm:
- Dashboard tables still hydrate from REST and show the current table state.
- Web ordering still hydrates `My Table Orders` for the selected table from local storage.
