set dotenv-load := true
set dotenv-filename := ".env"

backend := "backend"

default:
    @just --list

install:
    cd {{backend}} && uv sync --all-groups

hooks:
    cd {{backend}} && uv run pre-commit install

up:
    docker compose up -d --wait

down:
    docker compose down

reset: down
    docker volume rm generate-admin_postgres-data || true
    @just up

connect-db:
    docker compose exec postgres psql -U postgres -d generate_admin

dev:
    cd {{backend}} && uv run uvicorn admin.main:app --reload --reload-dir src \
        --host ${APP_HOST:-0.0.0.0} --port ${APP_PORT:-8000}

migrate:
    cd {{backend}} && uv run alembic upgrade head

rollback:
    cd {{backend}} && uv run alembic downgrade -1

revision message:
    cd {{backend}} && uv run alembic revision -m "{{message}}"

seed:
    cd {{backend}} && uv run python -m admin.cli seed

test:
    cd {{backend}} && uv run pytest

lint:
    cd {{backend}} && uv run ruff check . && uv run ruff format --check .

fmt:
    cd {{backend}} && uv run ruff check --fix . && uv run ruff format .

typecheck:
    cd {{backend}} && uv run mypy src

check: lint typecheck test
