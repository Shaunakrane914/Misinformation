# ==============================================================================
# Aegis Protocol — Multi-Stage Production Container Specification
# ==============================================================================

FROM python:3.13-slim-bookworm AS builder

WORKDIR /app

# Install build essentials if needed for wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime Stage ─────────────────────────────────────────────────────────────
FROM python:3.13-slim-bookworm AS runtime

WORKDIR /app

# Install runtime curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Create unprivileged application user
RUN groupadd -g 1000 aegis && \
    useradd -u 1000 -g aegis -s /bin/bash -m aegis && \
    mkdir -p /app/data /app/logs && \
    chown -R aegis:aegis /app

# Copy application code
COPY --chown=aegis:aegis . /app

USER aegis

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    ENVIRONMENT=production

EXPOSE 8000

# Container Healthcheck probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/healthz || exit 1

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
