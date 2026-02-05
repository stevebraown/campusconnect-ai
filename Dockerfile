# Multi-stage build: base stage installs dependencies
FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies for any compiled Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies (leverages layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage: minimal image with only runtime deps and app code
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install curl for health checks (lightweight)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security (runs as 'appuser' not 'root')
RUN useradd -m -u 1000 appuser

# Copy dependencies from base stage
COPY --from=base /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy source code
COPY src/ ./src/

# Set permissions for appuser
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose FastAPI port
EXPOSE 8000

# Health check: ensures container is responsive
# Checks if FastAPI /health endpoint returns 200
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI app via Uvicorn
# .env and config/serviceAccountKey.json must be provided at runtime via:
#   - Environment variables (docker run -e VAR=value)
#   - Volume mounts (docker run -v path:/app/config)
#   - .env file (docker run --env-file .env)
CMD ["python", "-m", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]
