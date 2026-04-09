# FoodBiz

FoodBiz is now a backend-first restaurant commerce and operations platform.

ROP-201 intentionally removes the legacy frontend applications. The repository currently ships a single deployable FastAPI backend that models multi-channel restaurant commerce around four canonical order channels:

- `dine_in`
- `pickup`
- `delivery`
- `third_party`

Source classification is tracked separately with strong enum values such as `qr`, `business_website`, `waiter_entered`, `counter_entered`, `uber_eats`, and `doordash`.

## Repository Layout

```text
repo/
  backend/
    src/rop/
      api/
      application/
      domain/
      infrastructure/
  deploy/
  docs/
  infra/
  scripts/
```

The backend stays a single FastAPI monolith. There are no microservices in this phase.

## Backend Architecture

The service is organized by bounded context instead of UI surface:

- `domain/catalog`
- `domain/commerce`
- `domain/kitchen`
- `domain/staff`
- `domain/iam`
- `domain/inventory`
- `domain/integrations`

Matching `application/*` and grouped `api/routes/*` packages sit on top of those domain boundaries.

## Local Development

Run these commands from `repo/`.

### Docker workflow

```bash
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m rop.tools.seed
```

Service URLs:

- API: `http://localhost:8000`
- Jaeger: `http://localhost:16686`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

### Direct backend commands

```bash
python -m pip install -e "./backend[dev]"
cd backend
alembic upgrade head
python -m rop.tools.seed
uvicorn rop.api.main:app --reload
```

### Common verification commands

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
curl http://localhost:8000/metrics
curl http://localhost:8000/v1/restaurants
curl http://localhost:8000/v1/restaurants/rst_001/catalog
```

## Make Targets

If `make` is available:

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

## Database and Seed

The database schema was reset in ROP-201 around channel-aware commerce:

- restaurants
- locations
- tables
- categories
- menu_items
- sessions
- orders
- order_lines
- order_status_history

Run migrations from scratch with:

```bash
cd backend
alembic upgrade head
```

Load deterministic local data with:

```bash
python -m rop.tools.seed
```

The seed creates:

- `rst_001` restaurant
- `loc_001` dine-in capable location
- `loc_002` pickup and delivery location
- `tbl_001` and `tbl_002`
- starter menu categories and menu items

## Frontend Status

The previous frontend applications were intentionally removed in ROP-201.

No replacement UI is included yet. The next generation UI work will land in a later ROP against the reset backend contract.

## CI Scope

CI now validates backend quality only:

- lint
- typecheck
- dependency-boundary checks
- unit tests
- integration tests with Postgres and Redis

## Notes

- `health`, `metrics`, and websocket infrastructure remain available.
- Inventory remains a stub and is intentionally not expanded in this phase.
- Payment processing, courier dispatch, and live marketplace integrations are out of scope for ROP-201.
