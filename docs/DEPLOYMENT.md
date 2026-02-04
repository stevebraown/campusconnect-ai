# Deployment

Production deployment guidance for the CampusConnect AI Service.

## Environment Variables Checklist

**Required**
- FIREBASE_PROJECT_ID
- GOOGLE_APPLICATION_CREDENTIALS
- PERPLEXITY_API_KEY or OPENAI_API_KEY

**Recommended**
- AI_SERVICE_TOKEN (protects /run-graph)
- GRAPH_TIMEOUT (default 30)
- MAX_CANDIDATES (default 100)

**Optional**
- LANGSMITH_API_KEY (LLM tracing)
- DEBUG (set false in prod)
- HOST / PORT
- ALLOWED_ORIGINS (if CORS is configured via env)

## Security Considerations

- **API authentication:** enable AI_SERVICE_TOKEN and require `Authorization: Bearer <token>`.
- **CORS:** restrict to your frontend/backend domains only.
- **Secrets management:** never commit .env or serviceAccountKey.json; use a secrets manager.
- **TLS:** terminate SSL at a reverse proxy or managed platform.

## Deployment Options

Choose what matches your stack:

- **Docker** (containerized deployment)
- **Systemd** (Linux VM)
- **PaaS** (Render, Railway, Heroku)
- **Cloud** (AWS ECS/Fargate, GCP Cloud Run, Azure Container Apps)

## Running in Production

### Recommended (Uvicorn with workers)

```bash
uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 2
```

### Example systemd service (Linux)

```ini
[Unit]
Description=CampusConnect AI Service
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/campusconnect-ai
Environment="PYTHONUNBUFFERED=1"
ExecStart=/opt/campusconnect-ai/venv/bin/uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

## Monitoring & Logging

- Monitor HTTP error rates (4xx, 5xx).
- Track graph latency (LLM calls are the main bottleneck).
- Ship logs to a centralized system (CloudWatch, Stackdriver, Datadog, etc.).

## Scaling Notes

- LLM latency is the primary scaling constraint.
- Firestore read/write limits apply (batch reads recommended).
- Use caching for static prompts or repeated lookups if needed.

## Docker (Coming Soon)

A Dockerfile exists in the repo but will be configured in a separate phase.
Once ready, you'll be able to run:

```bash
docker build -t campusconnect-ai .
docker run -p 8000:8000 --env-file .env campusconnect-ai
```
