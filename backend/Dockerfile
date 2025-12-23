# Backend Dockerfile (FastAPI + uvicorn)
FROM python:3.13-slim-bookworm AS base

WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN pip install --no-cache-dir -e .

# Copy application code
COPY app/ ./app/
COPY tests/ ./tests/

# Default command: run with hot-reload for dev (single process for WebSocket events)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production target (no reload, optimized)
FROM base AS production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Note: For RPA/Playwright, use Dockerfile.rpa instead (separate container)

