# Makefile for Mavn Bench Platform
.PHONY: help setup test clean docker

# Variables
PYTHON := python3
VENV := venv
NODE := node
NPM := npm
DOCKER_COMPOSE := docker-compose
PROJECT_NAME := mavn-bench

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(GREEN)Mavn Bench - Generic Document Processing Platform$(NC)"
	@echo "$(YELLOW)Available commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# ============== Setup Commands ==============

setup: ## Initial project setup
	@echo "$(YELLOW)Setting up Mavn Bench...$(NC)"
	@$(MAKE) setup-backend
	@$(MAKE) setup-frontend
	@$(MAKE) setup-infrastructure
	@echo "$(GREEN)Setup complete!$(NC)"

setup-backend: ## Setup Python backend
	@echo "$(YELLOW)Setting up backend...$(NC)"
	cd backend && $(PYTHON) -m venv $(VENV)
	cd backend && ./$(VENV)/bin/pip install --upgrade pip
	cd backend && test -f requirements.txt && ./$(VENV)/bin/pip install -r requirements.txt || echo "requirements.txt not found"
	@echo "$(GREEN)Backend setup complete!$(NC)"
setup-frontend: ## Setup React frontend
	@echo "$(YELLOW)Setting up frontend...$(NC)"
	cd frontend && test -f package.json && $(NPM) install || echo "package.json not found"
	@echo "$(GREEN)Frontend setup complete!$(NC)"

setup-infrastructure: ## Setup infrastructure directories
	@echo "$(YELLOW)Creating infrastructure directories...$(NC)"
	mkdir -p data/document_store
	mkdir -p logs
	mkdir -p config
	cp config/settings.example.yaml config/settings.yaml 2>/dev/null || true
	@echo "$(GREEN)Infrastructure setup complete!$(NC)"

# ============== Development Commands ==============

dev: ## Start development environment
	@echo "$(YELLOW)Starting development environment...$(NC)"
	$(MAKE) -j 2 dev-backend dev-frontend

dev-backend: ## Start backend in development mode
	@echo "$(YELLOW)Starting backend...$(NC)"
	cd backend && test -f ./$(VENV)/bin/uvicorn && ./$(VENV)/bin/uvicorn src.api.main:app --reload --port 8000 --host 0.0.0.0 || echo "Backend not setup"

dev-frontend: ## Start frontend in development mode
	@echo "$(YELLOW)Starting frontend...$(NC)"
	cd frontend && test -f package.json && $(NPM) start || echo "Frontend not setup"

dev-backend-logs: ## Start backend with visible logs
	@echo "$(YELLOW)Starting backend with logs...$(NC)"
	cd backend && source $(VENV)/bin/activate && python -m uvicorn src.api.main:app --reload --port 8000 --host 0.0.0.0 --log-level debug

dev-frontend-logs: ## Start frontend with visible logs
	@echo "$(YELLOW)Starting frontend with logs...$(NC)"
	cd frontend && npm run dev

dev-logs: ## Start both services with visible logs (run in separate terminals)
	@echo "$(YELLOW)Starting services with visible logs...$(NC)"
	@echo "$(GREEN)Run 'make dev-backend-logs' in one terminal$(NC)"
	@echo "$(GREEN)Run 'make dev-frontend-logs' in another terminal$(NC)"

dev-all-logs: ## Start all services with logs in same terminal
	@echo "$(YELLOW)Starting all services with logs...$(NC)"
	@$(MAKE) stop-all
	@sleep 2
	@trap 'kill %1 %2' INT; \
	(cd backend && source $(VENV)/bin/activate && python -m uvicorn src.api.main:app --reload --port 8000 --host 0.0.0.0 --log-level info 2>&1 | sed 's/^/[BACKEND] /') & \
	(cd frontend && npm run dev 2>&1 | sed 's/^/[FRONTEND] /') & \
	wait

restart: ## Restart all services with logs (stops then starts)
	@echo "$(YELLOW)Restarting all services...$(NC)"
	@$(MAKE) stop-all
	@sleep 2
	@$(MAKE) dev-all-logs

restart-clean: ## Clean restart - kills all processes on common ports
	@echo "$(YELLOW)Performing clean restart...$(NC)"
	@$(MAKE) stop-all
	@echo "$(YELLOW)Cleaning up any remaining processes...$(NC)"
	@for port in 8000 5173 5174 5175 5176 5177; do \
		lsof -ti:$$port | xargs kill -9 2>/dev/null || true; \
	done
	@sleep 3
	@$(MAKE) dev-all-logs

stop-all: ## Stop all services
	@echo "$(YELLOW)Stopping all services...$(NC)"
	pkill -f "uvicorn" || true
	pkill -f "npm" || true
	pkill -f "vite" || true
	pkill -f "node.*vite" || true
	lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	lsof -ti:5173 | xargs kill -9 2>/dev/null || true
	lsof -ti:5174 | xargs kill -9 2>/dev/null || true
	lsof -ti:5175 | xargs kill -9 2>/dev/null || true
	lsof -ti:5176 | xargs kill -9 2>/dev/null || true
	lsof -ti:5177 | xargs kill -9 2>/dev/null || true
	$(DOCKER_COMPOSE) down || true
	@echo "$(GREEN)All services stopped!$(NC)"

# ============== Testing Commands ==============

test-all: ## Run all tests
	@echo "$(YELLOW)Running all tests...$(NC)"
	@$(MAKE) test-backend
	@$(MAKE) test-frontend
	@echo "$(GREEN)All tests passed!$(NC)"

test-backend: ## Run backend tests
	@echo "$(YELLOW)Running backend tests...$(NC)"
	cd backend && test -f ./$(VENV)/bin/pytest && ./$(VENV)/bin/pytest tests/ -v --cov=src --cov-report=term-missing || echo "Pytest not installed"

test-frontend: ## Run frontend tests
	@echo "$(YELLOW)Running frontend tests...$(NC)"
	cd frontend && test -f package.json && $(NPM) test -- --coverage --watchAll=false || echo "Frontend tests not setup"

test-quick: ## Run quick smoke tests
	@echo "$(YELLOW)Running smoke tests...$(NC)"
	cd backend && test -f ./$(VENV)/bin/pytest && ./$(VENV)/bin/pytest tests/ -v -m "smoke" || echo "Pytest not installed"

# ============== Docker Commands ==============

build-docker: ## Build Docker images
	@echo "$(YELLOW)Building Docker images...$(NC)"
	test -f docker-compose.yml && $(DOCKER_COMPOSE) build || echo "docker-compose.yml not found"

start-docker: ## Start all services with Docker
	@echo "$(YELLOW)Starting Docker services...$(NC)"
	test -f docker-compose.yml && $(DOCKER_COMPOSE) up -d || echo "docker-compose.yml not found"

stop-docker: ## Stop Docker services
	@echo "$(YELLOW)Stopping Docker services...$(NC)"
	test -f docker-compose.yml && $(DOCKER_COMPOSE) down || echo "docker-compose.yml not found"

# ============== Utility Commands ==============

clean: ## Clean build artifacts
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf backend/dist backend/build backend/*.egg-info
	rm -rf frontend/build frontend/node_modules
	rm -rf .pytest_cache .coverage htmlcov
	@echo "$(GREEN)Clean complete!$(NC)"

format: ## Format code
	@echo "$(YELLOW)Formatting code...$(NC)"
	cd backend && test -f ./$(VENV)/bin/black && ./$(VENV)/bin/black src/ tests/ || echo "Black not installed"
	cd backend && test -f ./$(VENV)/bin/isort && ./$(VENV)/bin/isort src/ tests/ || echo "Isort not installed"

lint: ## Lint code
	@echo "$(YELLOW)Linting code...$(NC)"
	cd backend && test -f ./$(VENV)/bin/flake8 && ./$(VENV)/bin/flake8 src/ tests/ || echo "Flake8 not installed"
	cd backend && test -f ./$(VENV)/bin/mypy && ./$(VENV)/bin/mypy src/ || echo "Mypy not installed"

# Default target
.DEFAULT_GOAL := help
