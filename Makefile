.PHONY: up down build test lint format seed shell migrate makemigrations logs

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

test:
	docker compose up -d db
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

seed:
	docker compose exec api python manage.py seed

shell:
	docker compose exec api python manage.py shell

migrate:
	docker compose exec api python manage.py migrate

makemigrations:
	uv run python manage.py makemigrations

logs:
	docker compose logs -f api
