# Multi-stage/reproducible production Dockerfile for Code Lore
FROM python:3.11-slim as runtime

# Prevent Python from writing .pyc files and enable unbuffered logging output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies (curl for healthchecks and build-essential if needed for tree-sitter)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install production dependencies first (layer caching)
COPY requirements-prod.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-prod.txt

# Copy application source code and runtime assets
COPY backend /app/backend
COPY frontend /app/frontend
COPY data /app/data
COPY scripts /app/scripts
COPY docker-entrypoint.sh /app/


# Ensure entrypoint is executable and data directory exists
RUN chmod +x /app/docker-entrypoint.sh && mkdir -p /app/data

# Create dedicated non-root application user for hardened security
RUN useradd -u 10001 -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000 8501

ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default container command: start FastAPI with Uvicorn
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
