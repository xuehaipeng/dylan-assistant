.PHONY: help install dev test lint format clean run

help:  ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -e .

dev:  ## Install development dependencies
	pip install -e ".[dev]"
	pre-commit install

test:  ## Run tests with coverage
	pytest tests/ -v --cov=src --cov-report=term-missing

test-unit:  ## Run unit tests only
	pytest tests/unit -v -m "not integration"

test-integration:  ## Run integration tests only
	pytest tests/integration -v -m integration

lint:  ## Run linters (ruff, mypy)
	ruff check src tests
	mypy src

format:  ## Format code with black and ruff
	black src tests
	ruff check --fix src tests

clean:  ## Clean up build artifacts and cache files
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .coverage htmlcov .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

run:  ## Run the API server
	python run_server.py

run-dev:  ## Run the API server in development mode with auto-reload
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

docker-build:  ## Build Docker image
	docker build -t dylan-assistant:latest .

docker-run:  ## Run Docker container
	docker run -p 8000:8000 --env-file .env dylan-assistant:latest

pre-commit:  ## Run pre-commit hooks on all files
	pre-commit run --all-files

setup-env:  ## Copy .env.example to .env
	cp .env.example .env
	@echo "Created .env file. Please update it with your API keys."

check:  ## Run all checks (lint, test, type check)
	$(MAKE) lint
	$(MAKE) test
	@echo "All checks passed!"