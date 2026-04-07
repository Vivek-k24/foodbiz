# Staging Deployment

FoodBiz staging is intentionally simple:

- GitHub Actions builds and publishes the backend image to GHCR.
- A single Linux Docker host pulls the selected image tag.
- Docker Compose runs `postgres`, `redis`, and the FastAPI backend.
- Post-deploy smoke checks validate the current backend surface area.

There is no Azure, Kubernetes, Terraform, or production workflow in this repository.

## Command Scope

- GitHub Actions workflow steps run on GitHub-hosted Ubuntu runners.
- `repo/scripts/deploy_staging.sh` and `repo/scripts/smoke_staging.sh` are for the Linux staging host only.
- Local Windows PowerShell development should not run the staging Bash scripts directly.
- Local application verification still happens from `repo/` with Docker Compose, Python, and `pnpm`.

## Workflow Layout

GitHub only reads workflow files from repository root `.github/workflows/`.
This monorepo lives under `repo/`, so the workflows target `repo/` paths explicitly.

- `.github/workflows/ci.yml`
  - backend lint, typecheck, depcheck
  - backend unit tests
  - backend integration tests against GitHub Actions service containers
  - frontend install + build checks
- `.github/workflows/release-staging.yml`
  - automatic release after `CI` succeeds on `main`
  - manual `workflow_dispatch` for redeploy / rollback by image tag
  - backend image publish to GHCR
  - SSH deploy to staging host
  - post-deploy smoke checks

## Required GitHub Environment

Create a GitHub Environment named `staging`.

### Environment variables

- `STAGING_HOST`
- `STAGING_USER`
- `STAGING_PORT` (optional, defaults to `22`)
- `STAGING_APP_DIR`
- `STAGING_BASE_URL` (optional, used for GitHub environment link)
- `STAGING_RUN_SEED` (optional, default `true`)

### Environment secrets

- `STAGING_SSH_PRIVATE_KEY`
- `STAGING_ENV_FILE`

`STAGING_ENV_FILE` should contain the contents of a staging `.env` base file matching `repo/deploy/staging/.env.staging.example`.

## Host Prerequisites

The staging host must already provide:

- Docker Engine
- Docker Compose v2 plugin
- a non-root deploy user with Docker access
- SSH access for the configured `STAGING_USER`

Recommended first-time host bootstrap, run on the Linux staging host as the staging user:

```bash
export STAGING_APP_DIR=/srv/foodbiz-staging
mkdir -p "$STAGING_APP_DIR/deploy/staging" "$STAGING_APP_DIR/scripts"
docker --version
docker compose version
```

## Deploy Flow

Automatic staging deploy:

1. Push to `main`.
2. `CI` runs first.
3. `Release Staging` starts only after `CI` succeeds.
4. The workflow builds and pushes `ghcr.io/<owner>/foodbiz-backend:<short_sha>`, `:main`, and `:staging`.
5. Deployment assets and the staging env file are copied to the host.
6. `deploy_staging.sh` pulls the backend image, runs migrations, optionally runs deterministic seed data, and restarts the backend.
7. `smoke_staging.sh` verifies health, metrics, and the seeded menu read path.

Manual staging deploy / rollback from GitHub Actions:

1. Open `Release Staging` in GitHub Actions.
2. Click `Run workflow`.
3. Leave `image_tag` blank to build and deploy current `main`, or set `image_tag` to an existing published tag such as a previous short SHA.
4. Set `run_seed` only if you want the deterministic seed applied during that deploy.

## Rollback

This repo uses the smallest real rollback path:

- every release publishes immutable short-SHA tags
- the release workflow accepts a manual `image_tag`
- redeploying a previous short SHA is the rollback mechanism

Example rollback tag:

```text
ghcr.io/<owner>/foodbiz-backend:1a2b3c4
```

You can also inspect the host-side backup env file after a deployment:

- `${STAGING_APP_DIR}/.env.previous`

That file records the previous runtime image reference and is useful for manual host debugging, but the supported rollback path is the manual GitHub Actions redeploy.

## Smoke Scope

Current smoke coverage is intentionally limited to implemented functionality:

- `GET /health/live`
- `GET /health/ready`
- `GET /metrics`
- `GET /v1/restaurants/rst_001/menu`

This is deliberate. Payments and auth are unfinished and are not part of staging smoke tests.

## Failure Modes

The staging pipeline fails clearly for:

- missing GitHub environment variables or secrets
- GHCR auth or image pull failures
- SSH connection failures
- migration failures
- backend readiness failures
- smoke test failures

The deploy does not silently continue after any of these conditions.

## Logs and Troubleshooting

GitHub Actions:

- inspect the failed step directly in Actions
- CI uploads logs on failure for backend quality, unit, integration, and frontend build jobs

Linux staging host:

```bash
cd "$STAGING_APP_DIR"
docker compose --env-file .env -f deploy/staging/docker-compose.staging.yml ps
docker compose --env-file .env -f deploy/staging/docker-compose.staging.yml logs --tail=200 backend
docker compose --env-file .env -f deploy/staging/docker-compose.staging.yml logs --tail=200 postgres
docker compose --env-file .env -f deploy/staging/docker-compose.staging.yml logs --tail=200 redis
```

## Current Scope Boundary

Only the backend is published and deployed in staging.

That is intentional:

- backend is already Dockerized and deploy-ready
- frontend apps currently build in CI but are not yet containerized for staging deployment
- this keeps staging honest and avoids fake deployment plumbing for assets that are not yet operationalized
