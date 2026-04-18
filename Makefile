.PHONY: setup setup-api setup-web dev dev-api dev-web test test-unit test-integration test-golden lint docker-build health

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

setup: setup-api setup-web docker-build ## Full first-time setup

setup-api: ## Install Python deps via uv
	cd api && uv sync --dev

setup-web: ## Install Node deps
	cd web && npm install

# ---------------------------------------------------------------------------
# Development servers
# ---------------------------------------------------------------------------

dev: ## Run API + Web concurrently (Ctrl-C stops both)
	@trap 'kill 0' INT; \
	$(MAKE) dev-api & \
	$(MAKE) dev-web & \
	wait

dev-api: ## Start FastAPI (port 8000)
	cd api && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-web: ## Start Next.js dev server (port 3000)
	cd web && npm run dev

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

test: ## Run all tests
	cd api && uv run pytest ../tests

test-unit: ## Unit tests only
	cd api && uv run pytest ../tests/unit

test-integration: ## Integration tests only
	cd api && uv run pytest ../tests/integration

test-golden: ## Golden / regression tests only
	cd api && uv run pytest ../tests/golden

# ---------------------------------------------------------------------------
# Linting
# ---------------------------------------------------------------------------

lint: ## Lint frontend (ESLint)
	cd web && npm run lint

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

docker-build: ## Build TeX Live Docker image
	docker compose build texlive

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

health: ## Check API health endpoint
	@curl -s http://127.0.0.1:8000/health | python3 -m json.tool

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
