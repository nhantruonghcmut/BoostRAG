# =============================================================================
# BoostRAG backend — multi-stage Dockerfile
# =============================================================================

# ── Base ──────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=100

# System deps cho python-magic, psycopg, bcrypt, libmagic, build
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libmagic1 \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Deps install ──────────────────────────────────────────────────────────────
FROM base AS deps
COPY pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install -e ".[dev]"

# ── Dev target ────────────────────────────────────────────────────────────────
FROM deps AS dev
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Prod target ───────────────────────────────────────────────────────────────
FROM base AS prod
COPY pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install -e "."
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
