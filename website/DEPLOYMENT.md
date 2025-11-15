# Website Deployment Guide

This guide explains how to deploy the myfy website to Coolify using Docker and GitHub Actions.

## Overview

The deployment setup includes:
- **Docker**: Multi-stage build with security best practices (non-root user, health checks)
- **GitHub Actions**: Automated CI/CD pipeline that tests, builds, and deploys
- **Coolify**: Production hosting platform with webhook-based deployments

## Files Created

1. **`Dockerfile`** - Multi-stage Docker build configuration
2. **`entrypoint.sh`** - Entrypoint script that runs migrations and starts the server
3. **`.github/workflows/deploy-website.yml`** - GitHub Actions workflow for CI/CD

## Prerequisites

### 1. Coolify Setup

You need to have a Coolify application set up for the myfy website. To get your deployment UUID:

1. Go to your Coolify dashboard
2. Navigate to your website application
3. Go to "Webhooks" or "API" settings
4. Copy the deployment UUID (format: `uuid=XXXXXXXX`)

### 2. GitHub Secrets

Add the following secrets to your GitHub repository (`Settings > Secrets and variables > Actions`):

| Secret Name | Description | Required |
|-------------|-------------|----------|
| `COOLIFY` | Coolify API bearer token | Yes |
| `COOLIFY_WEBSITE_UUID` | Your Coolify application deployment UUID | Yes |

To get your Coolify API token:
1. Go to Coolify dashboard > Settings > API Tokens
2. Create a new token
3. Copy and save it as the `COOLIFY` secret

## Environment Variables in Coolify

Configure these environment variables in your Coolify application settings:

```bash
# Database (required)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# Security (required)
SECURITY_SECRET_KEY=<generate-a-long-random-string-at-least-32-characters>
SECURITY_HTTPS_ONLY=true
SECURITY_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Application
LOG_LEVEL=INFO
MYFY_FRONTEND_ENVIRONMENT=production

# External URLs
DOCS_URL=https://docs.myfy.dev
GITHUB_URL=https://github.com/psincraian/myfy
```

### Generating a Secret Key

Generate a secure secret key using Python:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Docker Build

The Dockerfile is designed to be built from the **repository root** (not the website directory).

### Local Testing

Build the Docker image locally:

```bash
# From the repository root
docker build -f website/Dockerfile -t myfy-website:test .
```

Run the container locally:

```bash
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://..." \
  -e SECURITY_SECRET_KEY="your-secret-key" \
  -e SECURITY_HTTPS_ONLY="false" \
  -e SECURITY_ALLOWED_HOSTS="localhost,127.0.0.1" \
  myfy-website:test
```

Visit http://localhost:8000 to test the application.

## GitHub Actions Workflow

The deployment workflow (`.github/workflows/deploy-website.yml`) runs automatically on every push to the `main` branch.

### Workflow Steps

1. **Test Job**
   - Sets up PostgreSQL service
   - Installs Python dependencies
   - Builds frontend assets
   - Runs linting and type checking

2. **Build and Push Job** (only on main branch)
   - Builds Docker image for `linux/amd64` platform
   - Pushes to GitHub Container Registry (ghcr.io)
   - Tags as `latest` and commit SHA
   - Uses caching for faster builds

3. **Deploy Job**
   - Triggers Coolify deployment via webhook
   - Only runs after successful build

### Manual Deployment

You can trigger a deployment manually from GitHub:

1. Go to `Actions` tab in your repository
2. Select "Deploy Website" workflow
3. Click "Run workflow"
4. Select the `main` branch
5. Click "Run workflow"

## Docker Image Registry

Images are pushed to GitHub Container Registry:

```
ghcr.io/psincraian/myfy-website:latest
ghcr.io/psincraian/myfy-website:<commit-sha>
```

### Pulling Images

To pull the latest image:

```bash
docker pull ghcr.io/psincraian/myfy-website:latest
```

## Coolify Configuration

### Docker Image

In your Coolify application settings, configure:

- **Image**: `ghcr.io/psincraian/myfy-website:latest`
- **Registry**: GitHub Container Registry (ghcr.io)
- **Pull on Deploy**: Enabled

### Health Check

The Docker image includes a built-in health check that pings the `/health` endpoint:

- Interval: 30 seconds
- Timeout: 10 seconds
- Start period: 5 seconds
- Retries: 3

Coolify will use this to monitor the application health.

### Database Setup

Ensure you have a PostgreSQL 16 database set up in Coolify or external service:

1. Create the database
2. Update the `DATABASE_URL` environment variable
3. The entrypoint script will automatically run migrations on startup

## Architecture

### Multi-Stage Build

The Dockerfile uses a multi-stage build for efficiency:

1. **Frontend Builder Stage** (Node.js)
   - Installs npm dependencies
   - Builds Vite assets (CSS, JS)
   - Outputs to `frontend/static/dist/`

2. **Production Stage** (Python)
   - Installs system dependencies (libpq5, curl)
   - Installs uv and Python dependencies
   - Copies application code
   - Copies built frontend assets
   - Runs as non-root `appuser` for security

### Security Features

- Non-root user (`appuser`)
- Minimal system dependencies
- Health check endpoint
- HTTPS enforcement (in production)
- Secret key for session security
- Allowed hosts validation

## Troubleshooting

### Build Failures

If the Docker build fails:

1. Check that you're building from the repository root
2. Ensure all workspace packages are present in `packages/`
3. Verify `uv.lock` is up to date

### Deployment Failures

If Coolify deployment fails:

1. Check GitHub Actions logs for build errors
2. Verify Coolify secrets are correct
3. Check Coolify application logs
4. Ensure database is accessible

### Database Connection Issues

If the application can't connect to the database:

1. Verify `DATABASE_URL` format is correct
2. Check database credentials
3. Ensure database host is accessible from Coolify
4. Check database firewall rules

### Health Check Failures

If health checks fail:

1. Check application logs for startup errors
2. Verify database migrations completed successfully
3. Ensure port 8000 is exposed and accessible
4. Check if application is actually running

## Rollback

To rollback to a previous version:

1. Find the commit SHA of the working version
2. In Coolify, change the image tag from `latest` to the specific commit SHA
3. Redeploy the application

Example:
```
ghcr.io/psincraian/myfy-website:abc1234
```

## Monitoring

### Application Logs

View logs in Coolify dashboard:
- Application > Logs
- Shows stdout/stderr from the container

### Health Endpoint

The `/health` endpoint returns:
```json
{"status": "healthy", "database": "connected"}
```

You can monitor this externally or use it for uptime monitoring services.

## Development Workflow

1. Make changes to the website code
2. Test locally with `uv run python app.py`
3. Commit and push to `main` branch
4. GitHub Actions automatically:
   - Runs tests and linting
   - Builds Docker image
   - Pushes to registry
   - Triggers Coolify deployment
5. Coolify pulls new image and redeploys

## Support

For issues or questions:
- GitHub Issues: https://github.com/psincraian/myfy/issues
- Documentation: https://docs.myfy.dev
