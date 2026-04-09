# Staging Deployment

FoodBiz staging is backend-only after ROP-201.

The current staging flow is intentionally simple:

- GitHub Actions builds and validates the backend.
- A single Linux Docker host runs `postgres`, `redis`, and the FastAPI service.
- Smoke checks validate backend health and the channel-aware commerce surface.

## Command Scope

- GitHub Actions workflow steps run on GitHub-hosted Ubuntu runners.
- `repo/scripts/deploy_staging.sh` and `repo/scripts/smoke_staging.sh` are Linux-host deployment scripts.
- Local verification uses Docker Compose plus Python only. There is no frontend build or deploy path in staging anymore.

## Workflow Layout

- `.github/workflows/ci.yml`
  - backend lint, typecheck, depcheck
  - backend unit tests
  - backend integration tests with Postgres and Redis service containers
- `.github/workflows/release-staging.yml`
  - backend image publish to GHCR
  - SSH deploy to the staging host
  - backend smoke checks

## Smoke Scope

Current smoke coverage is limited to the backend:

- `GET /health/live`
- `GET /health/ready`
- `GET /metrics`
- `GET /v1/restaurants`
- `GET /v1/restaurants/rst_001/catalog`

## Current Scope Boundary

Only the backend is built and deployed in staging.

That is deliberate:

- the frontend was removed in ROP-201
- the new UI work has not started yet
- the staging environment is validating the backend reset and migration flow only
