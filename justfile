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

invite *args:
    cd {{backend}} && uv run python -m admin.cli invite {{args}}

openapi:
    cd {{backend}} && uv run python -m admin.cli openapi

gen: openapi
    npm run gen

test:
    cd {{backend}} && uv run pytest

docker-test:
    docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from backend-test
    docker compose -f docker-compose.test.yml down -v

docker-build:
    docker build --target runtime -t generate-admin-backend {{backend}}

lint:
    cd {{backend}} && uv run ruff check . && uv run ruff format --check .

fmt:
    cd {{backend}} && uv run ruff check --fix . && uv run ruff format .

typecheck:
    cd {{backend}} && uv run mypy src

check: lint typecheck test

frontend-install:
    npm install

frontend-dev:
    npm run dev --workspace frontend

frontend-build:
    npm run build --workspace frontend

frontend-lint:
    npm run lint --workspace frontend
