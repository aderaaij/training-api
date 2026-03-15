.PHONY: up down build logs migrate create_migration

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

migrate:
	docker compose exec app alembic upgrade head

create_migration:
	docker compose exec app alembic revision --autogenerate -m "$(m)"
