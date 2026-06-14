#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting Trace on port 8000..."
exec uvicorn trace_app.main:app --host 0.0.0.0 --port 8000
