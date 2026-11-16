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
