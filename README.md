# UniWare Backend

The architecture context is in [ERD.md](docs/ERD.md) (schema), [STATE_MACHINES.md](docs/STATE_MACHINES.md)

## Stack

- Python 3.12
- uv
- Django 5.2
- Django REST Framework
- PostgreSQL 16
- pytest + pytest-django + factory_boy
- drf-spectacular
- Ruff
- Docker Compose.

## Quickstart

```bash
docker compose up --build
```

no `.env` required. `docker-compose.yml`; copy `.env.example` to `.env` only if you want to override something

Seed demo data (safe to re-run):

```bash
make seed
# or: docker compose exec api python manage.py seed
```
## Common tasks

| Command | Does |
|---|---|
| `make up` | `docker compose up --build` |
| `make down` | `docker compose down` |
| `make test` | brings up `db`, runs the full suite locally via `uv run pytest` (coverage gate enforced) |
| `make lint` | `ruff check` + `ruff format --check` |
| `make format` | `ruff format` + `ruff check --fix` |
| `make seed` | runs the seed command inside the running `api` container |
| `make shell` | Django shell inside the running `api` container |
| `make migrate` | applies migrations inside the running `api` container |
| `make makemigrations` | generates new migrations locally via `uv run` |

## Borrower catalog filters

`GET /api/equipment` accepts optional `category` and `location` UUIDs, available
from `/api/categories` and `/api/locations`, plus `availability=available` or
`availability=unavailable`. Multiple filters are combined with AND. `available`
matches `AVAILABLE`; `unavailable` matches the other borrower-visible statuses
(`RESERVED`, `CHECKED_OUT`, and `MAINTENANCE`). Omit all filter parameters to
reset to the full borrower-visible catalog. Malformed UUIDs and unsupported
availability values return HTTP 400; a valid UUID with no matching equipment
returns an empty result set.
