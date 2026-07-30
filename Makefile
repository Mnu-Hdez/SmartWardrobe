# Smart Wardrobe Outfit System - Makefile
# Common development and deployment commands

.PHONY: help install dev test lint format clean db-init db-migrate run run-dev docker-build docker-run deploy-pi

# Default target
help:
	@echo "Smart Wardrobe Outfit System - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  install       Install Python dependencies"
	@echo "  dev           Run development server with auto-reload"
	@echo "  run           Run production server"
	@echo "  test          Run all tests"
	@echo "  test-unit     Run unit tests only"
	@echo "  test-integration  Run integration tests only"
	@echo "  lint          Run linting (ruff, mypy)"
	@echo "  format        Format code (ruff format)"
	@echo "  clean         Clean cache and build files"
	@echo ""
	@echo "Database:"
	@echo "  db-init       Initialize database with tables and default data"
	@echo "  db-migrate    Run database migrations"
	@echo "  db-reset      Reset database (WARNING: destroys data)"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build  Build Docker image"
	@echo "  docker-dev    Run development with docker-compose"
	@echo "  docker-prod   Run production with docker-compose"
	@echo "  docker-stop   Stop all docker containers"
	@echo "  docker-logs   View docker logs"
	@echo "  docker-clean  Remove containers and volumes"
	@echo ""
	@echo "Deployment (Raspberry Pi):"
	@echo "  deploy-pi     Deploy to Raspberry Pi via SSH"
	@echo "  setup-pi      Initial Raspberry Pi setup"

# Python & Dependencies
install:
	pip install --upgrade pip
	pip install -e ".[dev]"
	pip install segment-anything --no-deps || true

# Install with specific PyTorch for CUDA
install-cuda:
	pip install --upgrade pip
	pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
	pip install -e ".[dev]"
	pip install segment-anything --no-deps || true

# Install PyTorch CPU (for ARM64 / Raspberry Pi)
install-cpu:
	pip install --upgrade pip
	pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
	pip install -e ".[dev]"
	pip install segment-anything --no-deps || true

# Development server
dev:
	uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend --reload-dir frontend

# Production server
run:
	uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --workers 4

# Run with gunicorn (production)
run-gunicorn:
	gunicorn backend.api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Testing
test:
	pytest tests/ -v --cov=backend --cov-report=term-missing

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-contract:
	pytest tests/contract/ -v

test-watch:
	pytest tests/ -v --watch

# Linting & Formatting
lint:
	ruff check backend/ tests/
	mypy backend/

format:
	ruff format backend/ tests/
	ruff check --fix backend/ tests/

# Type checking
typecheck:
	mypy backend/ --strict

# Clean
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true

# Database
db-init:
	python -m backend.scripts.init_db

db-migrate:
	alembic upgrade head

db-reset:
	rm -f data/db/smart_wardrobe.db
	make db-init

# Docker
docker-build:
	docker compose build

docker-dev:
	docker compose --profile dev up --build

docker-prod:
	docker compose --profile prod up --build -d

docker-stop:
	docker compose down

docker-logs:
	docker compose logs -f

docker-clean:
	docker compose down -v
	docker system prune -f

# Deployment (Raspberry Pi)
deploy-pi:
	@echo "Deploying to Raspberry Pi..."
	@echo "Usage: make deploy-pi PI_HOST=pi@raspberrypi.local PI_DIR=/home/pi/smart-wardrobe"
	rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='data' --exclude='venv' --exclude='.env' . $(PI_HOST):$(PI_DIR)/
	ssh $(PI_HOST) "cd $(PI_DIR) && docker compose --profile prod up --build -d"

setup-pi:
	@echo "Setting up Raspberry Pi..."
	@echo "Usage: make setup-pi PI_HOST=pi@raspberrypi.local"
	ssh $(PI_HOST) "curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $$USER && newgrp docker"