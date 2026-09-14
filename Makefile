.PHONY: help install dev test lint format migrate migration docker-up docker-down validate-benchmark verify-all check-release

PYTHON ?= python
VENV_BIN ?= .venv/bin
ifeq ($(OS),Windows_NT)
	VENV_BIN := .venv/Scripts
endif

help:
	@echo "CodeGuard AI - Production Release & Developer Commands"
	@echo "  make install            Install backend, MCP server, and frontend dependencies"
	@echo "  make dev                Start development servers (API & Web)"
	@echo "  make test               Run backend and MCP test suites with pytest"
	@echo "  make lint               Run Ruff linter and TypeScript type check"
	@echo "  make format             Format codebase using Ruff"
	@echo "  make validate-benchmark Validate empirical benchmarking scenarios"
	@echo "  make verify-all         Run all end-to-end phase verification suites"
	@echo "  make check-release      Run complete pre-release validation pipeline"
	@echo "  make migrate            Apply Alembic database migrations"
	@echo "  make docker-up          Start full container stack with Docker Compose"
	@echo "  make docker-down        Stop all running Docker Compose containers"

install:
	$(PYTHON) -m venv .venv
	$(VENV_BIN)/pip install --upgrade pip
	$(VENV_BIN)/pip install -e "./packages/code-intelligence" -e "./apps/api[dev]" -e "./apps/mcp-server"
	cd apps/web && npm install

dev:
	@echo "Starting API on http://localhost:8000 and Web on http://localhost:3000..."
	$(VENV_BIN)/uvicorn app.main:app --app-dir apps/api --reload --port 8000

test:
	$(VENV_BIN)/pytest apps/api/tests -v
	$(VENV_BIN)/pytest apps/mcp-server/tests -o pythonpath=apps/mcp-server -v

lint:
	$(VENV_BIN)/ruff check apps/api apps/mcp-server packages/code-intelligence scripts
	cd apps/web && npm run lint

format:
	$(VENV_BIN)/ruff check --fix apps/api apps/mcp-server packages/code-intelligence scripts

validate-benchmark:
	$(VENV_BIN)/python benchmark.py validate

verify-all:
	$(VENV_BIN)/python verify_phase1.py
	$(VENV_BIN)/python verify_phase2.py
	$(VENV_BIN)/python verify_phase3.py
	$(VENV_BIN)/python verify_phase4.py
	$(VENV_BIN)/python verify_phase5.py
	$(VENV_BIN)/python verify_phase7.py

check-release: lint test validate-benchmark
	cd apps/web && npm run build
	@echo "All pre-release quality gates passed successfully."

migrate:
	cd apps/api && ../../$(VENV_BIN)/alembic upgrade head

migration:
	@if [ -z "$(MSG)" ]; then echo "Error: Specify MSG parameter (e.g. make migration MSG='create_table')"; exit 1; fi
	cd apps/api && ../../$(VENV_BIN)/alembic revision --autogenerate -m "$(MSG)"

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down -v
