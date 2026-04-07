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
require_command curl
require_command docker
require_docker_compose

APP_DIR="${STAGING_APP_DIR}"
COMPOSE_FILE="${APP_DIR}/deploy/staging/docker-compose.staging.yml"
RUNTIME_ENV_FILE="${APP_DIR}/.env"

if [[ ! -f "$RUNTIME_ENV_FILE" ]]; then
  echo "runtime env file not found: $RUNTIME_ENV_FILE" >&2
  exit 1
fi

set -a
source "$RUNTIME_ENV_FILE"
set +a

BASE_URL="${SMOKE_BASE_URL:-http://127.0.0.1:${BACKEND_PORT:-8000}}"
RESTAURANT_ID="${SMOKE_RESTAURANT_ID:-rst_001}"

echo "Smoke target: ${BASE_URL}"
echo "Expected menu restaurant: ${RESTAURANT_ID}"
echo "App version: ${APP_VERSION:-unknown}"
echo "Image tag: ${IMAGE_TAG:-unknown}"

check_status() {
  local name="$1"
  local url="$2"
  local expected="$3"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' "$url")"
  if [[ "$code" != "$expected" ]]; then
    echo "${name} failed: expected ${expected}, got ${code} (${url})" >&2
    return 1
  fi
  echo "${name} ok (${code})"
}

echo "Waiting for readiness"
for attempt in $(seq 1 30); do
  if curl -fsS "${BASE_URL}/health/ready" >/dev/null 2>&1; then
    break
  fi
  if [[ "$attempt" -eq 30 ]]; then
    echo "readiness endpoint did not become healthy in time" >&2
    exit 1
  fi
  sleep 2
done

check_status "liveness" "${BASE_URL}/health/live" "200"
check_status "readiness" "${BASE_URL}/health/ready" "200"
check_status "metrics" "${BASE_URL}/metrics" "200"
check_status "menu" "${BASE_URL}/v1/restaurants/${RESTAURANT_ID}/menu" "200"

docker compose --env-file "$RUNTIME_ENV_FILE" -f "$COMPOSE_FILE" ps

echo "Staging smoke checks passed"
