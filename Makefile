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
	@echo "  docker-run    Run Docker container"
	@echo ""
	@echo "Deployment (Raspberry Pi):"
	@echo "  deploy-pi     Deploy to Raspberry Pi via SSH"
	@echo "  setup-pi      Initial Raspberry Pi setup"
	@echo ""

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
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage dist/ build/ *.egg-info/ 2>/dev/null || true

# Database
db-init:
	python -c "from backend.database.connection import init_db; init_db()"

db-migrate:
	alembic upgrade head

db-migrate-create:
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

db-reset:
	rm -f data/db/smart_wardrobe.db
	$(MAKE) db-init

# Download AI models
download-models:
	python -c "
	from backend.vision.segmenter import SAMSegmenter
	from backend.vision.classifier import CLIPClassifier
	print('Downloading SAM...')
	SAMSegmenter()
	print('Downloading CLIP...')
	CLIPClassifier()
	print('Models downloaded successfully!')
	"

# Docker
docker-build:
	docker build -t smart-wardrobe:latest .

docker-run:
	docker run -d \
		--name smart-wardrobe \
		-p 8000:8000 \
		-v $(PWD)/data:/app/data \
		-v $(PWD)/.env:/app/.env \
		--restart unless-stopped \
		smart-wardrobe:latest

docker-stop:
	docker stop smart-wardrobe && docker rm smart-wardrobe

docker-logs:
	docker logs -f smart-wardrobe

# Raspberry Pi Deployment
PI_HOST?=pi@raspberrypi.local
PI_PATH?=/home/pi/smart-wardrobe

deploy-pi:
	rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='data/db/*.db' \
		--exclude='data/images' --exclude='.env' \
		./ $(PI_HOST):$(PI_PATH)/
	ssh $(PI_HOST) "cd $(PI_PATH) && pip install -e . && sudo systemctl restart smart-wardrobe"

setup-pi:
	ssh $(PI_HOST) "bash -s" < deploy/scripts/setup_pi.sh

pi-logs:
	ssh $(PI_HOST) "sudo journalctl -u smart-wardrobe -f"

pi-status:
	ssh $(PI_HOST) "sudo systemctl status smart-wardrobe"

# Development utilities
shell:
	python -c "import backend; print('Backend loaded')"

check-imports:
	python -c "from backend.api.main import app; print('App imports OK')"

# Generate requirements.txt for environments without Poetry
requirements:
	pip freeze > requirements.txt

# Pre-commit hooks
pre-commit-install:
	pre-commit install

pre-commit-run:
	pre-commit run --all-files

# Security audit
security-audit:
	pip-audit
	bandit -r backend/

# Performance profiling
profile:
	python -m cProfile -o profile.stats -m backend.api.main

# Documentation
docs-serve:
	cd docs && python -m http.server 8080