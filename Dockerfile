# Multi-stage build for smaller runtime image.
FROM python:3.12-slim as base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime image keeps only installed deps and app code.
FROM python:3.12-slim as runtime
WORKDIR /app
COPY --from=base /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY src/ ./src
COPY .env.example .env

EXPOSE 8000
# Healthcheck ensures the container is responsive.
HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:8000/health || exit 1

# Entrypoint runs the FastAPI app via Uvicorn.
CMD ["python", "-m", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]
