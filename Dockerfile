# Smart Wardrobe Outfit System - Dockerfile
# Multi-stage build for production deployment

# ============================================================
# Build Stage
# ============================================================
FROM python:3.11-slim as builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    libopenblas-dev \
    libomp-dev \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -e .

# Download AI models (optional, can be done at runtime)
# RUN python -c "
# from backend.vision.segmenter import SAMSegmenter
# from backend.vision.classifier import CLIPClassifier
# SAMSegmenter()
# CLIPClassifier()
# print('Models downloaded!')
# "

# ============================================================
# Runtime Stage
# ============================================================
FROM python:3.11-slim as runtime

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas0 \
    libomp5 \
    libjpeg62-turbo \
    zlib1g \
    libpng16-16 \
    sqlite3 \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Create data directories
RUN mkdir -p data/db data/images/original data/images/processed/garments data/images/processed/outfits data/models_cache && \
    chown -R appuser:appuser data

# Copy nginx config
COPY deploy/nginx/smart_wardrobe.conf /etc/nginx/sites-available/smart_wardrobe.conf
RUN ln -sf /etc/nginx/sites-available/smart_wardrobe.conf /etc/nginx/sites-enabled/ && \
    rm -f /etc/nginx/sites-enabled/default

# Copy systemd service (for reference, not used in container)
COPY deploy/systemd/smart_wardrobe.service /etc/systemd/system/

# Switch to non-root user
USER appuser

# Expose ports
EXPOSE 80 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:$PATH" \
    DATABASE_URL=sqlite:///data/db/smart_wardrobe.db \
    AI_PROVIDER=local \
    DEVICE=cpu

# Default command (will be overridden by docker-compose)
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]