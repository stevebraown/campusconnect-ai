# Docker Setup & Deployment Guide

This guide covers building, running, and deploying the CampusConnect AI Service using Docker.

## Quick Start

### Build the Image

```bash
docker build -t campusconnect-ai:latest .
```

### Run Locally

**Option 1: Using .env file**
```bash
docker run -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/config:/app/config:ro \
  campusconnect-ai:latest
```

**Option 2: Using environment variables directly**
```bash
docker run -p 8000:8000 \
  -e FIREBASE_PROJECT_ID=your-project-id \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/config/serviceAccountKey.json \
  -e PERPLEXITY_API_KEY=your-api-key \
  -e AI_SERVICE_TOKEN=your-service-token \
  -v $(pwd)/config:/app/config:ro \
  campusconnect-ai:latest
```

### Test the Service

```bash
# Health check
curl http://localhost:8000/health

# View API documentation
# Open in browser: http://localhost:8000/docs
```

---

## Dockerfile Overview

The Dockerfile uses a **multi-stage build** for optimal image size and security:

### Stage 1: Builder (`base`)
- Installs Python dependencies from `requirements.txt`
- Cached separately for faster rebuilds

### Stage 2: Runtime (`runtime`)
- Copies only compiled dependencies (not source deps)
- Includes application code (`src/`)
- Runs as non-root user `appuser` (UID 1000)
- Exposes port 8000
- Health check endpoint: `GET /health`

### Key Features
- **Security**: Runs as non-root user, no hardcoded secrets
- **Performance**: Multi-stage build keeps image small (~450MB)
- **Reliability**: Health check ensures container is responsive
- **Best Practices**: Layer caching, minimal base image, proper permissions

---

## Environment Variables

**Required at runtime**:

| Variable | Description | Example |
|----------|-------------|---------|
| `FIREBASE_PROJECT_ID` | GCP Firebase project ID | `campusconnect-prod` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON | `/app/config/serviceAccountKey.json` |
| `PERPLEXITY_API_KEY` | API key for Perplexity AI | `pplx-abc123...` |
| `AI_SERVICE_TOKEN` | Internal service token | `secret-token-xyz` |

**Optional**:

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `False` | Enable debug logging |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Passing Environment Variables

**Option 1: .env file (recommended for local development)**
```bash
docker run -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/config:/app/config:ro \
  campusconnect-ai:latest
```

**Option 2: Via docker run -e**
```bash
docker run -p 8000:8000 \
  -e FIREBASE_PROJECT_ID=my-project \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/config/serviceAccountKey.json \
  -v $(pwd)/config:/app/config:ro \
  campusconnect-ai:latest
```

**Option 3: Docker Compose**
```yaml
version: '3.8'
services:
  campusconnect:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - ./config:/app/config:ro
    environment:
      - FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID}
```

---

## Volume Mounts

### Credentials (Required)

```bash
-v $(pwd)/config:/app/config:ro
```

- Mounts local `config/` directory (contains `serviceAccountKey.json`)
- Read-only (`:ro`) for security
- Path inside container: `/app/config`

### Logs (Optional)

```bash
-v $(pwd)/logs:/app/logs
```

- Persist application logs outside container
- Useful for debugging in production

### Example: Full Setup

```bash
docker run -p 8000:8000 \
  --name campusconnect \
  --env-file .env \
  -v $(pwd)/config:/app/config:ro \
  -v $(pwd)/logs:/app/logs \
  campusconnect-ai:latest
```

---

## Development Workflow

### Build & Run for Testing

```bash
# Build
docker build -t campusconnect-ai:dev .

# Run with interactive terminal
docker run -it \
  --env-file .env \
  -v $(pwd)/config:/app/config:ro \
  campusconnect-ai:dev bash

# Inside container, run tests
python -m pytest tests/
```

### View Logs

```bash
# Real-time logs
docker logs -f <container-id>

# Last N lines
docker logs --tail=50 <container-id>
```

### Stop & Remove Container

```bash
docker stop <container-id>
docker rm <container-id>
```

---

## Image Optimization

### Build Arguments (Future Enhancement)

If needed for different environments:

```bash
docker build \
  --build-arg ENVIRONMENT=production \
  -t campusconnect-ai:latest .
```

### Image Size

Current multi-stage build produces ~450MB image:
- Base Python 3.12-slim: ~150MB
- Python dependencies: ~300MB
- Application code: <5MB

### Reduce Further (Advanced)

For even smaller images, consider:
1. **Alpine Linux** instead of Debian-slim (~50MB base vs 150MB)
   - Trade-off: Less compatibility, more compilation
   - Use only if you hit storage/bandwidth limits
2. **Distroless** Python images (~60MB base)
   - Trade-off: No shell, harder to debug
   - Use for final production deployments

---

## Pushing to Registry

### Docker Hub

```bash
# Login
docker login

# Tag image
docker tag campusconnect-ai:latest yourusername/campusconnect-ai:latest

# Push
docker push yourusername/campusconnect-ai:latest
```

### GitHub Container Registry (GHCR)

```bash
# Login with GitHub token
echo $GITHUB_TOKEN | docker login ghcr.io -u <github-username> --password-stdin

# Tag
docker tag campusconnect-ai:latest ghcr.io/yourusername/campusconnect-ai:latest

# Push
docker push ghcr.io/yourusername/campusconnect-ai:latest
```

---

## Deployment to Production

### Prerequisites

- Server with Docker installed (Linux recommended)
- Environment variables configured
- Firebase credentials (`serviceAccountKey.json`)
- Network access for API calls (Perplexity, Firebase, etc.)

### Deploy to DigitalOcean / AWS / GCP

#### 1. Pull & Run Image

```bash
# On server
docker pull yourusername/campusconnect-ai:latest

docker run -d \
  --name campusconnect \
  --restart=always \
  -p 8000:8000 \
  --env-file /etc/campusconnect/.env \
  -v /etc/campusconnect:/app/config:ro \
  -v /var/log/campusconnect:/app/logs \
  yourusername/campusconnect-ai:latest
```

**Flags explained**:
- `-d` — Run in background (daemonize)
- `--restart=always` — Restart on crash or reboot
- `-p 8000:8000` — Expose port 8000
- `--env-file` — Load environment variables
- `-v /etc/campusconnect:/app/config:ro` — Mount credentials
- `-v /var/log/campusconnect:/app/logs` — Persist logs

#### 2. Setup Reverse Proxy (Nginx)

```nginx
upstream campusconnect {
    server localhost:8000;
}

server {
    listen 80;
    server_name api.campusconnect.com;

    client_max_body_size 10M;

    location / {
        proxy_pass http://campusconnect;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 3. Enable HTTPS with Let's Encrypt

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d api.campusconnect.com
```

#### 4. Monitor Container Health

```bash
# Check status
docker ps | grep campusconnect

# Check logs
docker logs campusconnect

# Health endpoint (from server)
curl http://localhost:8000/health
```

---

## Troubleshooting

### Container exits immediately

```bash
docker logs <container-id>
```

Common causes:
- Missing environment variables
- Missing `serviceAccountKey.json`
- Port 8000 already in use

### Health check failing

```bash
# Enter container
docker exec -it <container-id> bash

# Test health endpoint
curl -v http://localhost:8000/health

# Check app logs
cat logs/campusconnect.log  # inside container
```

### Permission denied errors

Ensure `config/` directory is readable:
```bash
chmod -R 755 config/
```

### Port already in use

```bash
# Use different port
docker run -p 9000:8000 campusconnect-ai:latest

# Or kill existing container
docker stop <container-id>
```

---

## Security Best Practices

✅ **Implemented in Dockerfile**:
- Runs as non-root user (`appuser`, UID 1000)
- Secrets NOT baked into image
- Credentials mounted as read-only volumes
- `.dockerignore` excludes sensitive files

✅ **For Production**:
- Use secrets management (Docker Secrets, Kubernetes Secrets, Vault)
- Enable HTTPS with TLS certificates
- Use firewall rules to restrict access
- Regularly update base image (`python:3.12-slim`)
- Scan image for vulnerabilities: `docker scan campusconnect-ai:latest`

---

## Docker Compose (Optional)

For local development with multiple services:

```yaml
version: '3.8'

services:
  campusconnect:
    build: .
    container_name: campusconnect-ai
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
    environment:
      - DEBUG=True
      - LOG_LEVEL=DEBUG
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 5s
```

Run with:
```bash
docker-compose up -d
```

---

## Useful Commands

| Command | Description |
|---------|-------------|
| `docker build -t campusconnect-ai:latest .` | Build image |
| `docker run -p 8000:8000 campusconnect-ai:latest` | Run container |
| `docker ps` | List running containers |
| `docker logs <container-id>` | View logs |
| `docker exec -it <container-id> bash` | Access container shell |
| `docker stop <container-id>` | Stop container |
| `docker rm <container-id>` | Remove container |
| `docker images` | List images |
| `docker rmi <image-id>` | Remove image |
| `docker inspect <container-id>` | View container details |
| `docker stats <container-id>` | Real-time CPU/memory usage |

---

## Next Steps

1. **Test locally**: Run `docker build` and `docker run` commands above
2. **Push to registry**: Docker Hub or GHCR
3. **Deploy to server**: Follow production deployment section
4. **Setup monitoring**: Use Docker stats or Prometheus
5. **Enable CI/CD**: GitHub Actions to auto-build on push

---

## References

- [Docker Documentation](https://docs.docker.com/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Uvicorn](https://www.uvicorn.org/)
- [Python Docker Best Practices](https://docs.docker.com/language/python/build-images/)
