# admin

## Requirements

- [uv](https://docs.astral.sh/uv/) (Python 3.12+)
- Docker, for Postgres / Redis / LocalStack
- [just](https://github.com/casey/just)

## Quickstart

```bash
cp .env.template .env    # defaults already match docker-compose
just install
just up                  # postgres + redis + localstack
just migrate
just seed                # roles, permissions, first owner invitation
just dev                 # http://localhost:8000
```

Check it with `curl localhost:8000/health`. API docs are at `/docs`.

## Services

Docker compose uses offset host ports so it does not collide with anything already running.

| Service    | Host port | Notes                                        |
| ---------- | --------- | -------------------------------------------- |
| Postgres   | `55532`   | db `generate_admin`, user/password `postgres` |
| Redis      | `56479`   | cache only, no persistence                    |
| LocalStack | `4576`    | S3 only, bucket `generate-admin-local`        |

## Commands

| Recipe             | What it does                     |
| ------------------ | -------------------------------- |
| `just up` / `down` | start / stop docker services     |
| `just reset`       | drop the Postgres volume, restart |
| `just dev`         | run the API with reload          |
| `just migrate`     | apply migrations                 |
| `just rollback`    | undo the last migration          |
| `just revision m`  | create a migration               |
| `just seed`        | sync roles and permissions       |
| `just test`        | pytest                           |
| `just lint`        | ruff check + format check        |
| `just fmt`         | ruff autofix + format            |
| `just typecheck`   | mypy over `src`                  |
| `just check`       | lint + typecheck + test          |

## Tests

`just test` needs Postgres and Redis running, since the suite boots the real app lifespan and
uses a real Redis.

## CI

`.github/workflows/backend-ci.yml` runs on pushes to `main` and on every PR:

- lint and typecheck: ruff and mypy
- test: Postgres and Redis service containers, migrations, then pytest

It mirrors `just check`.
