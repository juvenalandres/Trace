<p align="center">
  <img src="frontend/public/favicon.svg" width="80" alt="Trace logo">
</p>

<h1 align="center">Trace</h1>

**Self-hosted activity tracking and training planning platform.**

Upload GPX/FIT files or log activities manually. Visualize volume, pace, elevation, and heart rate trends over time. Plan and schedule training sessions with structured targets.

---

> **Disclaimer:** This application was built with extensive use of AI-assisted development. The models used include MiMo V2.5 Pro, Kimi 2.6, and DeepSeek V4 Flash. The architecture, code, and design were produced through iterative collaboration with these tools.

---

## Features

- **Activity tracking** -- GPX and FIT upload, manual entry, gear assignment
- **Data visualization** -- volume charts, personal records, sport breakdown, heatmap (uPlot + Leaflet)
- **Zone analysis** -- configurable HR and power zones with collapsible cards
- **Training load** -- CTL, ATL, TSB with exponential decay across gap days
- **Training plans** -- calendar-based planning with structured session targets (distance, duration, pace, HR, RPE)
- **Eddington number** -- SQL-computed E-number with distribution chart and qualifying rides/runs
- **Year-in-review** -- monthly breakdown, PRs, favorite month/sport
- **Segments** -- user-defined route segments with PR tracking, leaderboard, auto-matching on new uploads, and manual back-match for existing activities; inline creation modal with elevation profile chart; dedicated detail page with interactive map, elevation profile with synced cursor, PR card, leaderboard, and paginated effort history
- **Route planner** -- interactive map-based route builder with road snapping and elevation profiles
- **Admin** -- first user is admin by default; admin can manage other users' roles
- **Auth** -- JWT with refresh token rotation and httpOnly cookies

## Stack

| Layer          | Technology                                        |
|----------------|---------------------------------------------------|
| Frontend       | Svelte 5 + Vite + TypeScript                      |
| Charts         | uPlot                                             |
| Maps           | Leaflet.js (5 tile provider options)              |
| Backend        | FastAPI (async)                                   |
| ORM            | SQLAlchemy 2.0 (async)                            |
| Database       | PostgreSQL 16                                     |
| Migrations     | Alembic                                           |
| Auth           | JWT + rotation + httpOnly cookie                  |
| Caching        | TTLCache (256 entries, 60s TTL)                   |
| Admin          | First user auto-promoted to admin                   |
| Container      | Docker Compose                                    |

## Quick Start

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/trace.git
cd trace

# Copy and edit configuration
cp .env.example .env

# Generate a secure JWT secret (required)
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Edit .env and set TRACE_JWT_SECRET, then start everything
docker compose up
```

Open [http://localhost:8000](http://localhost:8000).

The stack includes a PostgreSQL 16 database, the Trace API + frontend (served from the same process), and a scheduled backup service.

## Configuration

Set via environment variables in `.env`:

| Variable                     | Default             | Description                                      |
|------------------------------|---------------------|--------------------------------------------------|
| `TRACE_JWT_SECRET`           | -- (required)       | JWT signing key (`secrets.token_urlsafe(64)`)    |
| `POSTGRES_PASSWORD`          | `trace_password`    | PostgreSQL password                              |
| `PORT`                       | `8000`              | App port                                         |
| `TRACE_CORS_ORIGINS`         | `*`                 | Allowed CORS origins (comma-separated)           |
| `TRACE_ALLOW_SIGNUP`         | `true`              | Set to `false` to disable registration           |
| `TRACE_RATE_LIMIT_PER_MINUTE`| `10`                | Auth endpoint rate limit per IP                  |
| `TRACE_MAX_UPLOAD_SIZE_MB`   | `50`                | Max GPX/FIT upload size                          |
| `TRACE_DB_POOL_SIZE`         | `5`                 | SQLAlchemy connection pool size                  |
| `TRACE_DB_MAX_OVERFLOW`      | `10`                | Max pool overflow connections                    |
| `TRACE_SEGMENT_MATCH_RADIUS` | `50`                | Segment auto-match radius in meters                |
| `TRACE_SEGMENT_MATCH_MAX`    | `5000`              | Max segments to check per upload                   |

## Development

```bash
# Dev mode with hot reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Run tests
docker compose exec app pytest

# Lint
docker compose exec app ruff check trace_app/
```

The dev override mounts source directories for live reload. No local Python or Node installation required.

## Project Structure

```
trace/
|
+-- trace_app/               FastAPI application
|   +-- routers/             API endpoints
|   +-- services/            Business logic (auth, parsing, training load)
|   +-- models.py            SQLAlchemy models
|   +-- schemas/             Pydantic request/response schemas
|   +-- cache.py             In-memory TTLCache
|   +-- main.py              App factory, middleware, route registration
|
+-- frontend/                Svelte 5 + Vite + TypeScript
|   +-- src/lib/             Components, stores, API client
|   +-- src/pages/           Page components
|
+-- alembic/                 Database migrations
+-- scripts/                 Backup and restore scripts
+-- docker-compose.yml       Production stack
+-- docker-compose.dev.yml   Dev override with hot reload
+-- Dockerfile               Production image
+-- Dockerfile.dev           Dev image
```

## License

MIT
