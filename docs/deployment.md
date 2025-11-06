# Deployment Guide

This guide covers how to deploy myfy applications to production environments.

---

## Quick Start

For a basic production deployment:

```bash
# 1. Build frontend assets (if using FrontendModule)
myfy frontend build

# 2. Start production server
myfy start --host 0.0.0.0 --port 8000 --workers 4
```

---

## Production Server

### myfy start

The `myfy start` command is optimized for production deployments:

- **Automatic production mode**: Sets `MYFY_FRONTEND_ENVIRONMENT=production`
- **No auto-reload**: Better performance and stability
- **Asset verification**: Ensures frontend assets are built before starting
- **Multi-worker support**: Uses gunicorn for horizontal scaling

### Single Worker

For simple deployments or development-like production:

```bash
myfy start --host 0.0.0.0 --port 8000
```

This uses uvicorn with a single worker process.

### Multiple Workers

For better performance and concurrency:

```bash
myfy start --host 0.0.0.0 --port 8000 --workers 4
```

This uses gunicorn with multiple uvicorn workers. Install gunicorn first:

```bash
pip install gunicorn
# or
uv add gunicorn
```

**Worker count recommendations:**
- CPU-bound apps: `(2 × CPU cores) + 1`
- I/O-bound apps: `(4 × CPU cores) + 1`
- Start with 4 workers and adjust based on monitoring

---

## Frontend Assets

If your application uses `FrontendModule`, you must build assets before deploying:

```bash
myfy frontend build
```

This generates:
- Minified JavaScript bundles
- Minified CSS files
- Asset manifest with content hashes
- Files in `frontend/static/dist/`

**Important:** The `myfy start` command will verify that assets are built and fail if missing.

---

## Environment Variables

### Core Settings

```bash
# Frontend environment (auto-set by myfy start)
MYFY_FRONTEND_ENVIRONMENT=production

# Web server settings
MYFY_WEB_HOST=0.0.0.0
MYFY_WEB_PORT=8000
```

### Frontend Settings

```bash
# Static file serving
MYFY_FRONTEND_STATIC_URL_PREFIX=/static

# Cache control
MYFY_FRONTEND_CACHE_MAX_AGE=31536000  # 1 year default
```

See [Configuration Reference](./api-reference/core.md) for all available settings.

---

## Deployment Options

### Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Install Python dependencies
RUN pip install -e .
RUN pip install gunicorn

# Build frontend assets
RUN myfy frontend build

# Expose port
EXPOSE 8000

# Start production server
CMD ["myfy", "start", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

Build and run:

```bash
docker build -t myfy-app .
docker run -p 8000:8000 myfy-app
```

### Docker Compose

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MYFY_FRONTEND_ENVIRONMENT=production
    restart: unless-stopped
```

Run:

```bash
docker-compose up -d
```


## Health Checks

Add a health check endpoint to your application:

```python
from myfy.web import route

@route.get("/health")
async def health_check():
    return {"status": "healthy"}
```

Configure your load balancer or orchestrator to check this endpoint.

---

## Monitoring

### Logging

myfy uses Python's standard logging. Configure it in your application:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```
---

## Troubleshooting

### Frontend assets not found

**Error:** "Frontend assets not built"

**Solution:** Run `myfy frontend build` before starting the server.

### Gunicorn not found

**Error:** "gunicorn not installed"

**Solution:** Install gunicorn:
```bash
pip install gunicorn
```

### Port already in use

**Error:** "Address already in use"

**Solution:** Change the port or stop the conflicting service:
```bash
myfy start --port 8080
```

### Worker timeout

If workers are timing out, increase the timeout:
```bash
gunicorn app:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout 120
```

---

## Next Steps

- [CLI Reference](./api-reference/cli.md) - Full CLI command reference
- [Configuration](./api-reference/core.md) - All configuration options
- [Frontend Module](./modules/frontend.md) - Frontend integration guide
