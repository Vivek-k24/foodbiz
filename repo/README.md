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

## Endpoints
- Live health: `GET http://localhost:8000/health/live`
- Ready health: `GET http://localhost:8000/health/ready`
- Metrics: `GET http://localhost:8000/metrics`

## Observability UIs
- Jaeger: http://localhost:16686
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (`admin` / `admin`)
