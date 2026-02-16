.PHONY: up down logs lint fmt typecheck test test-integration depcheck migrate seed

up:
	docker compose up -d --build

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

lint:
	ruff check backend && ruff format --check backend

fmt:
	ruff format backend

typecheck:
	mypy backend

test:
	pytest -q backend/tests/unit

test-integration:
	pytest -q backend/tests/integration

depcheck:
	python backend/tools/depcheck.py

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python -m rop.tools.seed
