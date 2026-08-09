set dotenv-load := true
set dotenv-filename := ".env"

backend := "backend"

default:
    @just --list

install:
    cd {{backend}} && uv sync --all-groups

up:
    docker compose up -d --wait

down:
    docker compose down

reset: down
    docker volume rm generate-admin_postgres-data || true
    @just up

dev:
    cd {{backend}} && uv run uvicorn generate_admin.main:app --reload --reload-dir src \
        --host ${APP_HOST:-0.0.0.0} --port ${APP_PORT:-8000}

migrate:
    cd {{backend}} && uv run alembic upgrade head

rollback:
    cd {{backend}} && uv run alembic downgrade -1

revision message:
    cd {{backend}} && uv run alembic revision -m "{{message}}"

test:
    cd {{backend}} && uv run pytest

lint:
    cd {{backend}} && uv run ruff check . && uv run ruff format --check .

fmt:
    cd {{backend}} && uv run ruff check --fix . && uv run ruff format .

typecheck:
    cd {{backend}} && uv run mypy src

check: lint typecheck test
