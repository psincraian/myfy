# Multi-stage Dockerfile for production

# Stage 1: Build frontend assets
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Copy frontend files
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci

COPY frontend ./frontend
RUN cd frontend && npm run build

# Stage 2: Python application
FROM python:3.12-slim

WORKDIR /app

# Install uv for faster dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy Python project files
COPY pyproject.toml uv.lock ./
COPY packages ./packages

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY app.py ./
COPY frontend ./frontend
COPY --from=frontend-builder /app/frontend/static/dist ./frontend/static/dist

# Set environment variables
ENV MYFY_FRONTEND_ENVIRONMENT=production
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "gunicorn", "app:app.asgi_app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
