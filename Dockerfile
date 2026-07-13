# ═══════════════════════════════════════════════════════════════
# Dockerfile — UV Surface Contamination Detection System
# Multi-stage build: slim Python 3.11 base, production Gunicorn
# ═══════════════════════════════════════════════════════════════

# ── Stage 1: Base image ─────────────────────────────────────────
FROM python:3.11-slim AS base

# Metadata
LABEL maintainer="KAMI-PIERRE"
LABEL description="UV Surface Contamination Detection System"
LABEL version="1.0.0"

# Prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ── Stage 2: Dependencies ────────────────────────────────────────
FROM base AS builder

WORKDIR /app

# Install system dependencies needed by psycopg2-binary and scikit-learn
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker layer caching
COPY requirements.txt .

# Install Python dependencies into /install prefix
RUN pip install --prefix=/install -r requirements.txt


# ── Stage 3: Runtime ─────────────────────────────────────────────
FROM base AS runtime

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source code
COPY . .

# Create models directory (persisted via volume)
RUN mkdir -p models

# Create non-root user for security
RUN groupadd -r uvapp && useradd -r -g uvapp uvapp \
    && chown -R uvapp:uvapp /app

USER uvapp

# Expose Flask/Gunicorn port
EXPOSE 5000

# Health check — Docker will restart container if this fails
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" \
    || exit 1

# ── Default command — Gunicorn production server ──────────────────
CMD ["gunicorn", \
     "app:create_app()", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--timeout", "120", \
     "--log-level", "info", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
