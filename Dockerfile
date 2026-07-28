# Smart Wardrobe Outfit System - Dockerfile
# Multi-stage build for production deployment
# Supports both x86_64 and ARM64 (Raspberry Pi)

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
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies
# Install torch CPU-first to avoid downloading CUDA wheels (saves ~1GB)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch torchvision && \
    pip install --no-cache-dir -e .[torch]

# ============================================================
# Runtime Stage
# ============================================================
FROM python:3.11-slim as runtime

# Install runtime dependencies
# - libopenblas0, libomp5: PyTorch/OpenMP
# - libjpeg62-turbo, zlib1g, libpng16-16: Pillow/image processing
# - sqlite3: database
# - libgomp1, libstdc++6: PyTorch C++ runtime
# - nginx: reverse proxy (only used in prod profile via compose)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas0 \
    libomp5 \
    libjpeg62-turbo \
    zlib1g \
    libpng16-16 \
    sqlite3 \
    libgomp1 \
    libstdc++6 \
    nginx \
    curl \
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
RUN mkdir -p data/db data/images/raw data/images/processed/garments data/images/processed/outfits data/models_cache && \
    chown -R appuser:appuser data

# Copy nginx config (container paths, not Pi paths)
COPY deploy/nginx/smart_wardrobe.container.conf /etc/nginx/sites-available/smart_wardrobe.conf
RUN ln -sf /etc/nginx/sites-available/smart_wardrobe.conf /etc/nginx/sites-enabled/ && \
    rm -f /etc/nginx/sites-enabled/default

# Switch to non-root user
USER appuser

# Expose ports (80 for nginx, 8000 for API)
EXPOSE 80 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:$PATH" \
    DATABASE_URL=sqlite:///data/db/smart_wardrobe.db \
    AI_PROVIDER=local \
    DEVICE=cpu

# Default command (overridden by docker-compose)
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]