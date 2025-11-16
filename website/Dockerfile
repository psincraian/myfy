# Multi-stage Dockerfile for production
# Build context should be the repository root (not website/)

# Stage 1: Build frontend assets
FROM node:20-slim AS frontend-builder

WORKDIR /app

# Copy package files from website directory
COPY website/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source files needed for build
COPY website/vite.config.js ./
COPY website/frontend/ ./frontend/

# Build frontend assets
RUN npm run build

# Stage 2: Python application
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MYFY_FRONTEND_ENVIRONMENT=production

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser -m appuser

# Install system dependencies in a single layer
# Use --no-install-recommends and clean up in same layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set work directory
WORKDIR /app

# Copy workspace configuration and dependency files first for better caching
COPY pyproject.toml uv.lock ./
COPY packages/ ./packages/
COPY website/pyproject.toml ./website/pyproject.toml
COPY website/README.md ./website/README.md

# Install dependencies (website and workspace packages)
RUN uv sync --frozen --no-dev

# Copy application code (this will be the layer that changes most often)
COPY website/app.py ./website/app.py
COPY website/website/ ./website/website/
COPY website/alembic/ ./website/alembic/
COPY website/alembic.ini ./website/alembic.ini

# Copy frontend templates and static files
COPY website/frontend/ ./website/frontend/

# Copy and set up entrypoint script
COPY website/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Copy built assets from frontend stage
COPY --from=frontend-builder /app/frontend/static/dist/ ./website/frontend/static/dist/

# Copy images directory to dist for static serving
COPY --from=frontend-builder /app/frontend/static/images/ ./website/frontend/static/dist/images/

# Create cache directory and change ownership in single layer
RUN mkdir -p /home/appuser/.cache && \
    chown -R appuser:appuser /app /home/appuser/.cache

# Switch to non-root user
USER appuser

# Set working directory to website
WORKDIR /app/website

# Expose port
EXPOSE 8000

# Health check using the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application with entrypoint
ENTRYPOINT ["/entrypoint.sh"]
