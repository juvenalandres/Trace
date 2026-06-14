# Stage 1: Build frontend
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci 2>/dev/null || npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Run backend
FROM python:3.13-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY trace_app/ ./trace_app/
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY alembic/ ./alembic/
COPY alembic.ini ./

COPY --from=frontend-build /app/frontend/dist ./static

COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

RUN mkdir -p /app/data/gpx

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

ENTRYPOINT ["./entrypoint.sh"]
