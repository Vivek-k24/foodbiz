#!/usr/bin/env bash

set -euo pipefail

require_var() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "missing required environment variable: $name" >&2
    exit 1
  fi
}

require_command() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "required command not found: $name" >&2
    exit 1
  fi
}

require_docker_compose() {
  if ! docker compose version >/dev/null 2>&1; then
    echo "docker compose v2 plugin is required on the staging host" >&2
    exit 1
  fi
}

require_var STAGING_APP_DIR
require_var GHCR_USERNAME
require_var GHCR_TOKEN
require_var BACKEND_IMAGE
require_var IMAGE_TAG
require_var GIT_SHA

require_command docker
require_docker_compose

APP_DIR="${STAGING_APP_DIR}"
COMPOSE_FILE="${APP_DIR}/deploy/staging/docker-compose.staging.yml"
BASE_ENV_FILE="${APP_DIR}/.env.staging.base"
RUNTIME_ENV_FILE="${APP_DIR}/.env"
PREVIOUS_ENV_FILE="${APP_DIR}/.env.previous"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "staging compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi

if [[ ! -f "$BASE_ENV_FILE" ]]; then
  echo "staging env base file not found: $BASE_ENV_FILE" >&2
  exit 1
fi

mkdir -p "$APP_DIR"

if [[ -f "$RUNTIME_ENV_FILE" ]]; then
  cp "$RUNTIME_ENV_FILE" "$PREVIOUS_ENV_FILE"
fi

cp "$BASE_ENV_FILE" "$RUNTIME_ENV_FILE"
{
  printf "\n"
  printf "BACKEND_IMAGE=%s\n" "$BACKEND_IMAGE"
  printf "IMAGE_TAG=%s\n" "$IMAGE_TAG"
  printf "APP_VERSION=%s\n" "$GIT_SHA"
} >> "$RUNTIME_ENV_FILE"

set -a
source "$RUNTIME_ENV_FILE"
set +a

printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin >/dev/null
trap 'docker logout ghcr.io >/dev/null 2>&1 || true' EXIT

compose() {
  docker compose --env-file "$RUNTIME_ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

wait_for_postgres() {
  local attempt
  for attempt in $(seq 1 30); do
    if compose exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  echo "postgres did not become ready in time" >&2
  return 1
}

wait_for_redis() {
  local attempt
  for attempt in $(seq 1 30); do
    if compose exec -T redis redis-cli ping >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  echo "redis did not become ready in time" >&2
  return 1
}

echo "Deploying ${BACKEND_IMAGE}:${IMAGE_TAG} to ${APP_DIR}"
echo "Git SHA: ${GIT_SHA}"

compose pull backend
compose up -d postgres redis

wait_for_postgres
wait_for_redis

echo "Running migrations"
compose run --rm backend alembic upgrade head

if [[ "${STAGING_RUN_SEED:-false}" == "true" ]]; then
  echo "Running deterministic staging seed"
  compose run --rm backend python -m rop.tools.seed
else
  echo "Skipping staging seed"
fi

echo "Starting backend container"
compose up -d backend
compose ps

echo "Staging deploy completed for image tag ${IMAGE_TAG}"
