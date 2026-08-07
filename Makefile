# Helios Makefile (Windows / Unix compatible helper)

.PHONY: install dev test lint format db-up db-down migrate seed

install:
	pip install -e .[dev,backend,intelligence]

dev:
	uvicorn backend.src.main:app --reload --host 127.0.0.1 --port 8000

test:
	python -m pytest

lint:
	ruff check .

format:
	ruff format .

db-up:
	docker compose up -d

db-down:
	docker compose down

migrate:
	alembic upgrade head

seed:
	python -m database.seed
