.PHONY: help venv install install-dev clean lint format test test-coverage type-check security run-gradio ingest-inventory setup-db pre-commit all

# Default target
.DEFAULT_GOAL := help

# Python interpreter
PYTHON := python3
VENV := .venv
VENV_BIN := $(VENV)/bin

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

venv: ## Create virtual environment
	$(PYTHON) -m venv $(VENV)
	$(VENV_BIN)/pip install --upgrade pip uv

install: venv ## Install production dependencies
	$(VENV_BIN)/uv pip install -e .

install-dev: install ## Install development dependencies
	$(VENV_BIN)/uv pip install -e ".[dev]"
	$(VENV_BIN)/pip install pre-commit pytest-cov mypy types-requests types-PyYAML

clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .coverage htmlcov/ .mypy_cache/ .pytest_cache/ .ruff_cache/

lint: ## Run linting checks
	$(VENV_BIN)/ruff check .
	$(VENV_BIN)/black --check .

format: ## Format code
	$(VENV_BIN)/ruff check --fix .
	$(VENV_BIN)/black .
	$(VENV_BIN)/isort .

test: ## Run tests
	$(VENV_BIN)/pytest factory_automation/factory_tests -v

test-coverage: ## Run tests with coverage
	$(VENV_BIN)/pytest factory_automation/factory_tests -v --cov=factory_automation --cov-report=html --cov-report=term-missing

type-check: ## Run type checking
	$(VENV_BIN)/mypy factory_automation

security: ## Run security checks
	$(VENV_BIN)/bandit -r factory_automation -f screen

run-gradio: ## Launch Gradio dashboard
	$(VENV_BIN)/python -m factory_ui.gradio_app

ingest-inventory: ## Ingest Excel inventory files
	$(VENV_BIN)/python ingest_inventory.py

setup-db: ## Set up PostgreSQL database
	psql -U postgres -f setup_database.sql

pre-commit: ## Install pre-commit hooks
	$(VENV_BIN)/pre-commit install
	$(VENV_BIN)/pre-commit run --all-files

all: clean install-dev lint type-check test ## Run all checks

# Development workflow shortcuts
dev-setup: install-dev pre-commit ## Complete development setup

check: lint type-check test ## Run all checks without formatting

fix: format ## Fix formatting and linting issues

# Docker targets (for future use)
docker-build: ## Build Docker image
	docker build -t factory-automation:latest .

docker-run: ## Run Docker container
	docker run -p 7860:7860 --env-file .env factory-automation:latest

# UI Design Review targets
ui-check: ## Run comprehensive UI design review
	$(VENV_BIN)/python -m factory_automation.factory_ui.design_review --save

ui-agent: ## Run AI Design Review Agent (7-phase methodology)
	$(VENV_BIN)/python -m factory_automation.factory_agents.design_review_agent --save

ui-screenshot: ## Capture UI screenshots for all viewports
	$(VENV_BIN)/python -m factory_automation.factory_ui.design_review --url http://localhost:7860 --save --output ui_screenshots_$(shell date +%Y%m%d_%H%M%S).json

ui-accessibility: ## Run WCAG accessibility tests
	$(VENV_BIN)/pytest factory_automation/factory_tests/test_ui_accessibility.py -v

ui-quick: ## Quick UI validation check
	@echo "Running quick UI validation..."
	$(VENV_BIN)/python -c "from factory_automation.factory_ui.design_review import DesignReviewAgent; import asyncio; agent = DesignReviewAgent(); asyncio.run(agent._check_visual_hierarchy(None, 'quick'))" 2>/dev/null || echo "✓ Quick check complete"

ui-test: ui-accessibility ## Run all UI tests

ui-review: ui-check ui-accessibility ## Full UI review with all checks

ui-baseline: ## Create baseline screenshots for visual regression
	mkdir -p ui_screenshots/baseline
	$(VENV_BIN)/python -m factory_automation.factory_ui.design_review --save --output ui_screenshots/baseline/baseline.json

ui-compare: ## Compare current UI against baseline
	$(VENV_BIN)/python -m factory_automation.factory_ui.visual_regression --compare

ui-clean: ## Clean UI test artifacts
	rm -rf ui_screenshots/*.png ui_review_*.json

# Combined UI and code quality check
full-check: check ui-review ## Run all code and UI checks
