#!/bin/bash
set -e

echo "Running database migrations..."
uv run alembic upgrade head

echo "Starting server..."
exec uv run myfy start
