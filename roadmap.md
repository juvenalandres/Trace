# Trace — Development Roadmap

**Self-hosted activity tracking & training platform.** Import activities from GPX files or sync directly from Garmin. View all your stats on an interactive dashboard — distance, elevation, heart rate, power, calories. Explore your data with heatmaps, charts, and calendar views. Track personal records, Eddington number, volume trends, and gear maintenance. Plan future training on a calendar with weekly targets.

```
TWO PILLARS:

┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│  DATA STATISTICS & VIZ          │  │  TRAINING PLANNING              │
│  Dashboard, Activities, Monthly │  │  Calendar, past + future plans  │
│  View, Gear Stats, Eddington,   │  │  🔴 Not started                 │
│  Heatmap, Charts                │  │                                 │
└─────────────────────────────────┘  └─────────────────────────────────┘
```

## Planning Philosophy

- **Vertical slice first:** Get one complete flow (upload GPX → parse → store → display on map) working before building out features.
- **Frontend drives API design:** Build UI against mock data or stubs to discover actual API shapes before committing to backend responses.
- **Auth from day one:** Add `user_id` to all models immediately, even if login UI comes later. Retrofit multi-tenancy is painful.
- **Test as you go:** pytest for backend, Vitest for frontend. At least one integration test for the full GPX → DB → API → render pipeline.

## Phase 1a — Core Models & First Parse ✅

*Get to a working "upload GPX → see it on a map" demo as fast as possible.*

- [x] **Design core database models** (users, activities, activity_stats only)
  - `users`: minimal (id, email, created_at — no auth yet)
  - `activities`: core fields + `sport_type` enum (run/ride/swim/hike/walk/other) + `source` enum (manual/gpx/fit/garmin) + `raw_file_path`
  - `activity_stats`: computed fields + `simplified_time_series` (JSON, every Nth point) + `polyline` + `elevation_profile` + `bounds`
- [x] **Point storage strategy:** simplified JSON (every Nth point) in activity_stats + raw GPX file on disk for reprocessing
- [x] **Set up SQLAlchemy 2.0 async + Alembic** with initial migration
- [x] **Save sample GPX files** in a `testdata/` directory
- [x] **Write the GPX parser** to extract all available fields (lat, lng, ele, time, hr, cadence, power, temp)
- [x] **Write the FIT parser** (fitparse library) — extracts session summary (sport, distance, calories, avg/max speed, avg/max HR) + track points; sport enum mapping (cycling→ride, running→run, etc.); GPS semicircle→degree conversion; elevation forward-fill for sparse data
- [x] **Write the activity processor** that computes derived fields (distance, elevation gain, speed, pace, encoded polyline, simplified time series)
- [x] **Auto-lap generation:** ActivityProcessor generates laps from point data (configurable: every 1km or every 5min)
- [x] **Validate with real data:** upload test GPX files, verify every computed field + generated laps
- [x] **Define API contract** (OpenAPI stubs) for the vertical slice endpoints

## Phase 1b — Remaining Models & Full Schema ✅

*Expand the data model once the core pipeline is proven.*

- [x] **Gear model:** per-equipment tracking (name, type enum: bike/shoes/other, brand, model, maintenance interval, retired status)
- [x] **SyncSource model:** OAuth tokens, provider enum (garmin/fitbit/wahoo/polar), sync state
- [x] **UserZone model:** user-editable HR and power zone limits (zone_1_min/max ... zone_5_min/max, valid_from)
- [x] **TrainingPlan + TrainingSession models** (placeholder for Phase 7)
  - `training_plans`: user_id, name, description, start/end dates
  - `training_sessions`: plan_id, scheduled_date, sport_type, targets (JSON array of {type, value, unit}), intervals (JSON), links to completed activity
- [x] **User profile expansion:** physiology (weight, FTP, max HR, resting HR), preferred units, privacy settings, sport preferences
- [x] **Write all Pydantic schemas** for create/read/update operations
- [x] **Alembic migration** for new models

## Phase 2 — Core Backend API ✅

*Minimal, auth-aware API. Enough for the frontend to build against.*

- [x] **Auth scaffolding** (JWT): register, login, token refresh, auth middleware — no UI yet, but `user_id` enforced on all endpoints
- [x] CRUD API for activities (list with filters + pagination, detail, create, update, delete)
- [x] GPX upload endpoint
- [x] Manual activity create endpoint (for typed-in activities with no file)
- [x] CRUD API for gear
- [x] **StatsEngine:** dashboard aggregation (period stats, sport breakdown, recent activities)
- [x] **StatsEngine:** Eddington number computation
- [x] **StatsEngine:** personal records, volume over time, year-in-review
- [x] Aggregation API endpoints (`/api/stats/dashboard`, `/api/stats/eddington`, `/api/stats/year-review`)
- [x] **Integration test:** GPX upload → DB → stats API → JSON response

## Phase 3 — Frontend Scaffold & Vertical Slice ✅

*Prove the full pipeline end-to-end. Frontend drives API refinement.*

- [x] Scaffold Svelte 5 project with Vite + TypeScript
- [x] **Shared component library:** StatCard, StatRow, ActivityTable, SportBreakdown, PeriodNav, LineChart (uPlot wrapper), RouteChartPanel (Leaflet + synced charts), HRZones, PowerZones, HeatmapCalendar, Modal, Icon
- [x] **Dashboard page** (stat cards + heatmap calendar + sport breakdown + recent activities table)
- [x] **Activity detail page** (all stats + Leaflet map + charts with cross-highlighting + HR/Power zones)
- [x] **GPX/FIT upload page** (drag-and-drop zone, gear selection dropdown)
- [x] **Vertical slice test:** upload GPX → see activity on dashboard → open detail → map + charts render correctly
- [x] Refine API response shapes based on what the frontend actually needs

### Frontend Architecture
- **Layout:** Topbar (fixed, full width) + Sidebar (fixed, collapsible with icons) + Content area (only scrollable element); `body` and `.app` constrained to `100vh` with `overflow: hidden`
- **Routing:** Simple hash-based navigation (no SvelteKit)
- **API layer:** Fetch wrapper with auto JWT token refresh
- **Icons:** Custom SVG Icon component (no emojis)
- **Charts:** uPlot for all charts with synced cursor and transparent fill
- **Maps:** Leaflet.js with tile selector (5 providers: Topo Map, OpenTopoMap, Street Map, Voyager, Satellite); preference saved in localStorage
- **Styling:** CSS variables, no framework; global utility classes in `app.css` (`.page`, `.dash-card`, `.card-header h3`)
- **Typography:** Single font family (`var(--font-sans)`), two weights only (400 regular, 500 medium), sizes from 11px to 26px; hierarchy via size, weight, color tone, and letter-spacing
- **Card design:** Global `.dash-card` class (0.5px border, `var(--surface)` background, 10px radius, 16px padding, 20px margin-bottom); pages override only `margin-bottom` when needed
- **Card headers:** Global `.card-header h3` class (flex row, 14px/600 semibold); pages use it directly, no local CSS needed
- **Responsive:** 768px breakpoint, sidebar slides in as overlay on mobile, grids stack to 1-2 columns, charts/maps scale down

### UI Components
- **StatCard:** Square icon (32px, 8px radius, tinted bg), uppercase label (11px/500), large value (26px/500), unit suffix (13px/400); optional `color` and `bg` props override icon tint (e.g. `color="#3b82f6" bg="#3b82f620"` for distance metric)
- **StatRow:** Card style, title left gray, metric right bold, same font size
- **ActivityTable:** Rounded card, colored sport dot, two-line name (13px/500 + 11px/400), right-aligned metrics (13px/400), pace pill badge (11px/400)
- **HRZones:** Heart icon with blue bg, avg/max subcards, zone bars in red shades — uses user-configured zones from Profile
- **PowerZones:** Bolt icon with blue bg, avg/max watts subcards, zone bars in blue shades — uses user-configured zones from Profile
- **HeatmapCalendar:** 12-month grid (Mon–Sun × weeks), 3 metric toggles (Load/Moving time/Calories), 5 intensity levels (green shades), month labels (11px/400), legend
- **RouteChartPanel:** Map (400px) + metric toggles + synced uPlot charts with fill, speed in km/h, x-axis is cumulative distance (km) with numeric scale; single shared tooltip shows all metrics on hover (follows cursor with fixed positioning, auto-adjusts to stay in viewport)
- **LoadingSpinner:** Centered animated spinner with optional message, 3 sizes (sm/md/lg)
- **ErrorBanner:** Red alert with icon, message text, and optional retry button
- **EmptyState:** Centered icon + message + optional action button (e.g. "Upload", "Add Gear")

### Gear Management
- **Gear page:** Standalone page with grid of gear cards + stats table
- **CRUD:** Add/edit/delete gear via modal forms (name, type, brand, model, notes, maintenance interval)
- **Retire:** Toggle retired status; retired gear shown in collapsible section
- **Stats table:** Per-gear lifetime stats — workouts, total distance, total elevation, total time, avg speed, total calories (grid layout matching dashboard activities table)
- **Maintenance:** Progress bar showing distance since last service vs interval (green <75%, yellow 75-90%, red >90%)
- **Service tracking:** `last_service_date` and `last_service_distance_m` fields; "Mark as serviced" button auto-captures current date + total distance
- **Service endpoint:** `POST /api/gear/{id}/service` computes current total distance and stamps it
- **Gear assignment:** Upload page has gear dropdown (fetches active gear, "None" default); activity edit modal allows changing/clearing gear assignment; assigned gear's distance automatically counts toward maintenance progress

### Monthly View
- **Topbar:** Title ("Monthly Stats") + prev/next month nav arrows with pill-style month label
- **Summary cards:** 4 metric cards (distance, duration, elevation, activity count) in 4-column grid, using dashboard-standardized icon colors (`#3b82f6`, `#14b8a6`, `#f59e0b`, `#f97316`)
- **Calendar card:** CSS table-grid with 7 columns, 72px cells, today shown as filled blue circle, active days use `#185FA5` text, overflow days at 0.4 opacity; each cell shows colored sport badges with distance (e.g. `12.5 km` in a green pill for run)
- **Month/year picker:** Click month pill to open dropdown — year arrows flanking the year, 3×4 month grid, "Today" button to jump back
- **Day drill-down:** Click a day to show activities for that date in an ActivityTable below; click again to deselect

### Heatmap (Geographic)
- **Map:** Leaflet with tile selector (5 providers), 600px height
- **Routes:** All activity polylines rendered as colored lines (run=green, ride=blue, walk=yellow, hike=orange, swim=cyan, other=purple)
- **Filters:** Sport type dropdown + year dropdown (dynamically populated from available years)
- **Popups:** Click any route to see name, sport type, distance
- **Summary:** Total route count and total distance below the map
- **Backend:** `GET /api/routes` returns polylines + metadata, supports sport_type and year filters

### Eddington
- **Hero card:** Large Eddington number (80px/500, primary color) with explanation text, uses `.dash-card` class
- **Progress card:** `.card-header h3` title + count badge, progress bar with fill animation
- **Distribution chart:** `.card-header h3` title with subtitle, uPlot bar chart
- **Qualifying activities:** `.card-header h3` title + count badge, clickable list with sport, date, distance
- **Unit-aware:** Uses user's preferred_units (km or miles) for all thresholds, labels, and distances
- **Backend:** `GET /api/stats/eddington` returns distribution + qualifying_activities + unit_label

### Statistics
- **Topbar:** Year filter pills with 1.5px blue border (`#185FA5`) active state; wraps below title on mobile; "All" shows all-time data, specific year filters all sections (volume chart, by sport, personal records)
- **Volume over time card:** uPlot chart (220px height, `stroke=#378ADD`, `fill=#E6F1FB`, `spline=0.3`, padding `[10,40,15,0]` for y-axis labels, axis labels `stroke=#888`, grid `stroke=#eee`); ResizeObserver with `chart.setSize()` for responsive resizing; hover tooltip showing date + value; x-axis labels adapt to data: single year shows "Jan", "Feb", etc., multi-year shows "Jan '23", "Feb '23"; chart built reactively via `$effect` (not setTimeout), destroyed when switching to empty year
- **By sport card:** Horizontal bars matching dashboard SportBreakdown style (sport icons, colors, distance values)
- **Personal records grid:** 3-column grid with 6 custom cards — Distance (blue, `#3b82f6`), Duration (teal, `#14b8a6`), Elevation (amber, `#f59e0b`), Avg Speed (coral, `#f97316`), Top Speed (purple, `#a855f7`), Highest avg HR (pink, `#ec4899`); each card shows value + source activity link in `#185FA5`; filtered by selected year
- **Backend:** `GET /api/stats/personal-records` accepts optional `year` param; `GET /api/stats/volume` returns all-time data when no year specified (not last 2 years)

### Settings & Zones
- **Profile page:** Account (name, email), Physiology (units, weight, FTP, max HR, resting HR), HR Zones (Z1–Z5), Power Zones (Z1–Z5)
- **Zone cards:** Collapsible — both HR and Power zone cards start collapsed, click header to expand; chevron rotates on toggle; border-bottom only shows when expanded
- **Zone boundaries:** Z1 = only max (min is 0), Z2–Z4 = min + max, Z5 = only min (no upper limit)
- **Zone wiring:** User-configured zones fetched on activity detail page, passed to HRZones/PowerZones components for time-in-zone calculation
- **User sync:** Profile saves update parent App state via `onUserUpdated` callback

### Loading, Error & Empty States
- **Loading:** All pages use `LoadingSpinner` component (animated ring, centered, gray message text)
- **Errors:** `ErrorBanner` replaces bare `<p>` tags — red background, icon, message, optional retry button that re-calls the page's load function
- **Empty states:** `EmptyState` component with contextual icon, message, and action button (e.g. "Upload" on Activities, "Add Gear" on Gear)
- **Pattern:** Each page extracts a `load()` function from `onMount` so retry can re-invoke it; errors are caught and surfaced via `error` state
- **Coverage:** Dashboard, Activities, ActivityDetail, Gear, MonthlyStats, Statistics, Eddington, Heatmap, Profile, Upload

### Mobile-Friendly Responsive UI
- **Breakpoint:** 768px (tablet/mobile)
- **Sidebar:** Slides in as overlay from the left with semi-transparent backdrop; toggle button opens/closes mobile menu; brand name and user name hidden to save space
- **Sidebar text:** Inactive nav-links use `#475569` for better contrast (was `#64748b`)
- **Card headers:** All `.card-header h3` and `.chart-header h3` use `font-weight: 600` (semibold) globally for improved readability
- **Stat grids:** 4-column grids → 2 columns, 6-column grids → 2 columns
- **Gear cards:** Single column on mobile, stats table scrolls horizontally
- **Monthly calendar:** Compact cells (smaller fonts, smaller badges), 2-column month stats
- **Statistics:** 2-column PR grid, year picker wraps below title, single-column chart
- **Eddington:** Smaller hero number (56px), qualifying rows stack vertically
- **Heatmap:** Map 350px height (from 600px), filters stack below title
- **Profile:** Field rows stack vertically
- **Upload:** Reduced drop zone padding
- **RouteChartPanel:** Map 250px, charts auto-resize via ResizeObserver
- **SportBreakdown:** Rows wrap, bar spans full width
- **HeatmapCalendar:** Header stacks, metric toggles wrap, grid scrolls horizontally
- **ActivityTable:** Horizontal scroll on overflow (already had `overflow-x: auto`)

## Known Bugs

- [x] **Charts right margin clipping:** uPlot charts inside `.charts-card` appear cut off on the right edge. Fixed by using `requestAnimationFrame` to ensure wrapper has correct width before creating charts, and updating ResizeObserver to use per-chart wrapper width instead of container width.
- [x] **Chart auto-sizing:** Removed CSS `width: 100% !important` overrides that conflicted with uPlot canvas; replaced with ResizeObserver + `chart.setSize()` on Statistics and RouteChartPanel. Left padding 15px ensures y-axis labels are visible.
- [x] **HRZones card width:** Card not expanding to full width when no PowerZones present (standalone in `.section`). Fixed by adding explicit `width: 100%` to `.section` and `display: block; min-width: 0` to `.hr-card`.
- [x] **Statistics volume chart not plotting:** `buildChart()` called via `setTimeout` before DOM ready. Fixed by using reactive `$effect` that watches `volume`, `chartContainer`, `loading`, and `clientWidth > 0`.
- [x] **Statistics year selector:** "All" returned only last 2 years of data; personal records ignored year selection. Fixed: volume endpoint returns all-time when no year, personal-records accepts `year` param.
- [x] **Volume chart x-axis labels:** All labels showed "Jan 1" when data spanned multiple years. Fixed by detecting multi-year data and showing year suffix in axis labels (e.g. "Jan '23").
- [x] **CTL/ATL/TSB contaminated by old activities:** `recompute_ctl_atl_tsb` iterated daily records by array index, treating consecutive records as consecutive days. Uploading a 2018 activity caused stale CTL/ATL to carry directly into 2024 records. Fixed by computing actual day gaps between records and applying exponential decay: `value * (1 - decay)^gap_days`. Startup recomputation automatically fixes existing data.
- [x] **CTL/ATL/TSB flat during rest days:** `DailyTrainingLoad` records were only created on activity upload. Days with zero activity had no record, so the GET endpoint fed `prev_ctl`/`prev_atl` through unchanged — CTL/ATL showed flat lines instead of decaying. Fixed by adding `backfill_daily_loads()` that creates zero-load records for every gap day up to yesterday and recomputes CTL/ATL/TSB with proper exponential decay. Called on both activity upload and on page load (inside `GET /api/training/ctl`).

## Security & Performance Audit

*Prioritized findings. Checked items are resolved; unchecked are open.*

### Critical

- [x] **Hardcoded default JWT secret** (`config.py`): Removed default; `jwt_secret: str` has no default so app refuses to start without `TRACE_JWT_SECRET`. Startup check rejects placeholder values ("change-me-in-production", "change-me"). `.env.example` updated with generation command.
- [x] **No `.gitignore`**: Created root `.gitignore` covering `.env`, `data/`, `backups/`, `__pycache__/`, `node_modules/`, IDE files, OS files.
- [x] **No password strength validation** (`schemas/auth.py`): Added `@field_validator` on `RegisterRequest.password` — minimum 8 characters, at least one digit.

### High — Security

- [x] **Tokens in `localStorage`** (`frontend/src/lib/stores/auth.ts`): Refresh token moved to `httpOnly` + `Secure` + `SameSite=Strict` cookie. Backend sets cookie on login/register/refresh, reads it on refresh. Frontend only stores access token in localStorage. Logout endpoint (`POST /api/auth/logout`) clears the cookie. `credentials: 'same-origin'` on all fetch requests.
- [x] **Refresh endpoint has no rate limiting** (`routers/auth.py`): Added `@limiter.limit(rate_limit)` to `/api/auth/refresh`, matching login/register.
- [x] **No refresh token rotation/revocation** (`routers/auth.py`): Implemented token rotation with reuse detection. New `refresh_tokens` table stores hashed tokens with `family_id`. Each refresh revokes the old token and issues a new pair. If a revoked token is reused (indicating theft), the entire token family is invalidated and the user must re-login.
- [x] **`raw_file_path` leaked in API responses** (`schemas/activity.py`): Removed `raw_file_path` from `ActivityResponse`. Server filesystem path no longer exposed to clients.
- [ ] **CORS `*` with credentials** (`config.py`): Default `cors_origins: str = "*"` combined with `allow_credentials=True`. Fix: default to specific origin, add startup warning if `*` used.
- [x] **Health endpoint leaks DB errors** (`main.py`): Replaced `f"error: {str(e)}"` with generic `"error"` string. Full exception logged server-side only.

### High — Performance

- [x] **Dashboard makes 8 sequential queries** (`main.py`): All 9 queries (7 period_stats + sport + recent) now run in parallel via `asyncio.gather()`. Results processed after gather completes.
- [x] **Zero caching**: In-memory LRU cache (`trace_app/cache.py`) with 256 entries and 60s TTL. Applied to dashboard, volume, eddington, heatmap, personal records endpoints. Cache keyed by `user_id:endpoint:params`. Invalidated on activity create/update/delete.
- [x] **Missing composite index**: `activities(user_id, start_time)` composite index already exists (migration `c1a2b3c4d5e6`).
- [x] **Personal records: 6 sequential queries** (`main.py`): All 6 `best()` calls now run in parallel via `asyncio.gather()`.

### Medium — Security

- [x] **No input length limits on string fields** (all schemas): Added `max_length` constraints on all user-facing string fields. `name` (255), `sport_type`/`gear_type` (50), `timezone` (50), `brand`/`model` (255), `description`/`notes`/`intervals` (10000), `zone_type` (20), `status` (20), `unit` (20), `preferred_units` (20), `password` (128). `rpe` constrained with `ge=1, le=10`.
- [x] **No email format validation** (`schemas/auth.py`): Both `RegisterRequest` and `LoginRequest` now use `EmailStr` from Pydantic. Requires `email-validator>=2.0` (in `pyproject.toml`).
- [x] **GPX parser uses `xml.etree.ElementTree`** (`services/gpx_parser.py`): Switched to `defusedxml.ElementTree`. Added 50MB file size limit before parsing for both GPX and FIT parsers to prevent DoS via memory exhaustion. `defusedxml>=0.7` in `pyproject.toml`.
- [ ] **File type determined only by extension** (`main.py`): Upload endpoint checks filename extension, not content. Fix: validate magic bytes (GPX starts with `<?xml`, FIT has binary header).
- [x] **N+1 queries in activity listing** (`main.py`): Added `selectinload(Activity.stats)` to `list_activities` query and dashboard `recent_q` query. Removed `await db.refresh(a, ["stats"])` loops. Stats loaded in a single secondary query via SQLAlchemy eager loading.
- [x] **`page_size` has no upper bound** (`main.py`): Changed `page_size: int = 20` to `page_size: int = Query(20, le=100)` in `list_activities`. FastAPI now rejects requests with `page_size > 100`.

### Medium — Performance

- [x] **N+1 in `list_plans`** (`main.py`): Added `selectinload(TrainingPlan.sessions)` to all training plan queries (`list_plans`, `get_plan`, `update_plan`, `create_plan`). Removed all `await db.refresh(plan, ["sessions"])` calls. Sessions loaded in a single secondary query via eager loading. `list_routes` was not affected — Route model has no collection relationships.
- [x] **No code splitting in Vite config** (`frontend/vite.config.ts`): Added `manualChunks` to rollup output config — `leaflet`, `uplot`, and `vendor` chunks are split from the main bundle. Reduces initial JS load and improves caching for vendor libraries.
- [x] **No cache headers on static assets** (`main.py`): Created `CachedStaticFiles` subclass of `StaticFiles` that adds `Cache-Control: public, max-age=31536000, immutable` headers for all `/assets/*` requests. Vite-generated hashed asset filenames are safe for aggressive caching.

### Low

- [x] **`days`/`weeks` query params unbounded** (`main.py`): Changed `days: int = 90` to `days: int = Query(90, le=365)` in `training_ctl` and `weeks: int = 24` to `weeks: int = Query(24, le=104)` in `training_weekly_volume`. FastAPI rejects out-of-range requests.
- [x] **No security response headers**: Added security headers to the existing `request_middleware` in `main.py`: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security: max-age=63072000; includeSubDomains`, `Content-Security-Policy` (default-src 'self', script-src 'self' 'unsafe-inline' 'unsafe-eval', img-src allows map tile providers). Applied to all responses.
- [x] **Eddington loads all distances into memory** (`main.py`): Replaced `compute_eddington()` and `eddington_progress()` Python functions with SQL-based computation. E-number computed via `row_number() OVER (ORDER BY distance_m DESC)` window function; progress count via SQL `COUNT`. Distribution still computed in Python but uses the ordered SQL result instead of loading all distances into a list first.
- [x] **CTL endpoint iterates day-by-day in Python** (`main.py`): Replaced `while current_date <= today` loop with `for day_offset in range(days + 1)`. Records loaded into a dict for O(1) lookup instead of index-tracking. No longer nested DB calls inside the loop.
- [x] **Training insights loads all rows into Python** (`main.py`): Replaced Python aggregation with two SQL queries: (1) weekly volume grouped by `_week_start_expr(start_time)` — `SUM(distance_m)`, `SUM(duration_s)`, `SUM(moving_time_s)`, `COUNT(*)`, (2) pace trends grouped by week start + sport with `AVG(avg_speed)`. Added `_week_start_expr` helper (SQLite: `date(col, 'weekday 1', '-7 days')`, PostgreSQL: `date_trunc('week', col + '1 day') - '1 day'`). All aggregation pushed to database.

### Recommended Priority

1. **S1 + S2 + S3** — critical security, quick fixes
2. **S5 + S9 + S7** — easy hardening
3. **P1 + P4** — biggest performance wins
4. **S14 + S15 + P3 + P6 + P7** — query optimization
5. Everything else — defense in depth

## Phase 4 — Remaining Frontend Pages

*Build out the full feature set on the proven foundation.*

- [x] Activity list page (filtered + paginated table with sport badges)
- [x] Activity filters (sport, source, date range, distance, elevation)
- [x] User profile/settings page (units, physiology, HR/power zones)
- [x] Monthly view page (calendar grid + day drill-down to activity table)
- [x] Eddington page (big number + distribution chart + progress bar + qualifying list) — hidden from sidebar, accessible internally
- [x] Heatmap page (Leaflet density overlay)
- [x] Statistics page (volume over time chart + PRs grid with 3 columns + sport breakdown + year picker; "All" shows all-time data, year selection filters all sections; multi-year labels show year suffix)
- [ ] Year-in-Review page (full yearly report with monthly breakdown, PRs, favorite month/sport)
- [x] Gear management page (list + add/edit/retire + lifetime stats + maintenance reminders)
- [x] **Gear assignment** on upload page (dropdown) and activity edit modal (change/clear); distance auto-counts toward maintenance progress
- [x] **Mobile-friendly responsive UI** (768px breakpoint: sidebar overlay, stacked grids, compact calendar, responsive charts/maps)
- [x] **Loading states, error handling, empty states** across all pages
- [x] **StatCard colors:** `color` and `bg` props for metric-specific icon colors (distance=#3b82f6, duration=#14b8a6, speed=#f97316, elevation=#f59e0b)
- [x] **Profile page collapsible zones:** HR and Power zone cards start collapsed, click header to expand with chevron indicator

## Phase 5 — Garmin API Sync (Discontinued)

*One provider, done well. Others become stretch goals.*

- [ ] OAuth integration framework (generic provider pattern)
- [ ] **Garmin Connect sync connector** (richest data: activities, laps, routes, HR, power)
- [ ] Background scheduler (APScheduler) for periodic sync
- [ ] Deduplication logic (avoid importing the same activity twice)
- [ ] External API connections page (OAuth flow + sync status UI)

## Phase 6 — PostgreSQL & Production Infrastructure

*PostgreSQL as the sole database. Optimize storage for scale.*

### 6.1 — Docker Compose Setup
- [x] `docker-compose.yml` with PostgreSQL 16 + Trace app containers
- [x] Environment-based config (`.env` file for DB credentials, JWT secret, etc.)
- [x] Health checks for both containers (app waits for DB before starting)
- [x] Volume mounts for persistent data (PostgreSQL data dir, GPX file storage)
- [x] `Dockerfile` for the Trace app (Python 3.13 slim, uvicorn, no dev deps)
- [x] `docker-compose.dev.yml` override for local development (PostgreSQL, hot reload)

### 6.2 — SQLAlchemy Async + PostgreSQL Tuning
- [x] Connection pooling via `asyncpg` + SQLAlchemy `create_async_engine` with `pool_size=5`, `max_overflow=10`
- [x] `pool_pre_ping=True` to handle stale connections
- [x] Set `echo=False` in prod, configurable via `TRACE_DB_ECHO` env var
- [x] Index audit: ensure all `WHERE`/`JOIN`/`ORDER BY` columns have indexes
  - `activities(user_id, start_time)` — composite for dashboard time-range queries ✅
  - `activity_stats(activity_id)` — already indexed (unique)
  - `activity_stats(training_load)` — new index for sport load distribution queries ✅
  - `daily_training_load(user_id, date)` — already indexed (unique constraint)
  - `training_sessions(plan_id, scheduled_date)` — composite for calendar queries ✅
- [x] Date helper functions (`_year_expr`, `_year_month_expr`, `_date_expr`, `_week_start_expr`) for SQL date arithmetic across queries
- [ ] `EXPLAIN ANALYZE` profiling on slow queries (dashboard, eddington, volume)

### 6.3 — Alembic Migrations for PostgreSQL
- [x] Alembic env configured to use `TRACE_DATABASE_URL` (env.py reads from settings.database_url)
- [x] Initial migration creates all tables in PostgreSQL
- [x] Migrations run automatically on Docker startup (entrypoint.sh runs `alembic upgrade head`)
- [x] SQLite → PostgreSQL migration not needed (fully on PostgreSQL from the start)
- [ ] Test migration rollback works cleanly

### 6.4 — Time Series Normalization *(moved to Phase 8)*
- [ ] New `activity_time_series` table (see architecture note below)
- [ ] Migrate existing `simplified_time_series` JSON blobs → normalized rows
- [ ] Update GPX/FIT parsers to write to new table instead of JSON blob
- [ ] Update `GET /api/activities/{id}` to load time series from new table
- [ ] Keep `activity_stats.polyline` and `activity_stats.elevation_profile` as-is (small, used for maps)
- [ ] Remove `simplified_time_series` column from `activity_stats`
- [ ] Benchmark: activity detail page load time before/after normalization

### 6.5 — Data Migration Tool *(moot — fully on PostgreSQL, no SQLite migration needed)*
- [x] `python -m trace_app.tools.migrate_sqlite_to_pg` CLI command — not implemented, no longer needed
- [x] Reads from SQLite (`--source ./data/trace.db`) — not needed
- [x] Writes to PostgreSQL (`--target $TRACE_DATABASE_URL`) — not needed
- [x] Batched inserts (1000 rows per commit) for performance — not needed
- [x] Progress bar + ETA — not needed
- [x] Validates row counts match after migration — not needed
- [x] Handles time series JSON → normalized table conversion during migration — not needed

### 6.6 — Backup & Recovery
- [x] `pg_dump` cron job (daily at 2:00 AM, with 7-day rotation)
- [x] Backup script stores dumps in `./backups/` bind mount (`scripts/backup.sh`)
- [x] Restore script with `psql` (`scripts/restore.sh`)
- [x] Backup service added to `docker-compose.yml` (postgres:16-alpine + cron)
- [x] Document backup/restore procedure (see below)

### 6.7 — Production Hardening
- [x] Rate limiting on auth endpoints (login, register) — configurable via `TRACE_RATE_LIMIT_PER_MINUTE` (default: 10)
- [x] Request size limits (upload max 50MB) — configurable via `TRACE_MAX_UPLOAD_SIZE_MB`
- [x] CORS configuration via env var (`TRACE_CORS_ORIGINS`)
- [x] Structured logging (JSON format) with request ID, user ID, duration
- [x] Health endpoint returns DB connection status
- [x] Graceful shutdown (SIGTERM/SIGINT handlers)
- [x] Registration toggle — `TRACE_ALLOW_SIGNUP` env var (default: true, set to false to disable public registration)

### Backup & Restore Procedure

**Automatic backups:**
- Backup service runs daily at 2:00 AM
- Backups stored in `./backups/` directory (bind mount)
- Compressed SQL dumps (`trace_YYYYMMDD_HHMMSS.sql.gz`)
- 7-day rotation (old backups deleted automatically)
- Logs written to `./backups/backup.log`

**Manual backup:**
```powershell
docker compose exec backup /usr/local/bin/backup.sh
```

**List backups:**
```powershell
ls -la ./backups/
```

**Restore from backup:**
```powershell
# Stop the app (keep db running)
docker compose stop app

# Run restore script
docker compose exec backup /bin/sh
# Inside container:
/usr/local/bin/restore.sh /backups/trace_YYYYMMDD_HHMMSS.sql.gz

# Restart app
docker compose start app
```

**Or restore directly:**
```powershell
# Decompress and pipe to psql
gunzip -c ./backups/trace_YYYYMMDD_HHMMSS.sql.gz | docker compose exec -T db psql -U trace -d trace
```

## Phase 7 — Training Planning (Pillar 2)

*Second pillar. Calendar-based planning with flexible session targets.*

- [x] Training plan CRUD API (`/api/training/plans` — create, list, detail, update, delete)
- [x] Training session CRUD API (`/api/training/plans/{id}/sessions`, `/api/training/sessions/{id}`)
- [x] Training block CRUD API (`/api/training/plans/{id}/blocks`, `/api/training/blocks/{id}`) — mesocycle grouping between plan and session
- [x] Session assignment to blocks (optional `block_id` FK, sessions without a block display as ungrouped)
- [x] Dynamic block colors computed from sort order and total block count (HSL evenly spaced hues)
- [x] Session targets: support multiple targets per session (distance, duration, pace, HR zone, power zone, free) stored as JSON array
- [x] Structured workouts: intervals field (text/JSON) per session
- [x] Rest day markers, notes per session
- [x] Training Plans page (plan list with cards, plan detail with session grid, full CRUD via modals)
- [x] Calendar view (month layout, sessions as sport chips on dates, day detail modal with session cards)
- [x] Link planned sessions to completed activities (auto-match on upload by date + sport type; unlink on activity delete)
- [x] Training Insights page (weekly volume chart, speed trends by sport, consistency streak)
- [x] Advanced training metrics: CTL (Fitness), ATL (Fatigue), TSB (Form), ACWR (Acute:Chronic Workload Ratio)
- [x] Weekly volume targets (planned vs actual distance/time per sport, derived from session targets)

### Training Plans
- **Plan list:** Card grid showing name, description, session count, date range
- **Plan detail:** Sessions displayed in 3-column grid (1 on mobile)
- **Session cards:** Sport badge (color-coded matching map colors), target badges (multiple, color-coded: distance=blue, duration=gray, pace=green, hr_zone=red, power_zone=blue, free=purple), rest day dashed border, status badges (done/skipped)
- **Session form:** Date, sport dropdown, name, rest day toggle, multiple targets (add/remove, each with type/value/unit), intervals text, description, notes
- **Model:** TrainingPlan (name, description, start/end date) → TrainingSession (scheduled_date, sport_type, targets JSON array, intervals, rest_day, activity_id, status)
- **Sidebar:** Separate "Training" section with Plans and Calendar entries
- **Calendar:** Month/Week view toggle (pill-style buttons in header); month view shows sport chips per day (colored badge + session name), plan selector, weekly progress bars (distance/activities per sport), today highlighted with circle on day number only, day detail modal reuses session card style; linked sessions show "View Activity →" link that navigates to activity detail
- **Week view:** Shows Mon–Sun of current week with larger day cells; each session card shows sport type (color-coded left border), session name, target badges, completion status (Done/Skipped), and "View Activity" link; prev/next week navigation, click date label to jump to "this week"; responsive: stacks to single column on mobile
- **Auto-link:** On activity upload, backend queries for planned sessions matching the activity's date and sport_type; links first match (sets `activity_id`, marks `status = "completed"`). Sessions with no sport_type set match any activity. On activity delete, linked sessions are reset to plans (cleared `activity_id`, `status = "planned"`)
- **Weekly Volume:** `GET /api/training/weekly-volume?plan_id=X&weeks=24` returns per-week breakdown of planned (from session targets) vs actual (from activities) volume per sport; planned volume computed by summing distance/duration targets from sessions
- **Insights page:** Organized into 4 sections: Overview (stat cards + CTL/ATL/TSB/ACWR metric cards), Performance Management (PMC chart, weekly load bars, ACWR trend), Volume & Trends (weekly volume with target reference lines, speed trends, sport load distribution), Recovery Status (TSB zone indicator with visual bar and guidance)
- **Performance Management Chart (PMC):** CTL (Fitness, blue line), ATL (Fatigue, red line), TSB (Form, green area) over 90 days; shared cursor tooltip shows date, CTL, ATL, TSB, daily load; ACWR badge in header with color-coded status and guidance based on Gabbett (2016)
- **Training Load (TRIMP):** Per-session training load computed on activity upload using Banister HR-based formula (`duration × %HRmax × 0.64 × e^(1.92 × %HRmax)`); fallback to duration × intensity when HR data unavailable; stored in `activity_stats.training_load`
- **Daily Training Load:** New `daily_training_load` table stores per-day aggregated load with CTL/ATL/TSB; recomputed from activity date forward on each upload. On app startup, CTL/ATL/TSB is automatically recomputed for all users to fix stale gap data.
- **CTL (Fitness):** 42-day exponentially weighted average of training load. Decay across date gaps: `value * (1 - decay)^gap_days`.
- **ATL (Fatigue):** 7-day exponentially weighted average of training load. Decay across date gaps: `value * (1 - decay)^gap_days`.
- **TSB (Form):** CTL − ATL. Positive = fresh, negative = fatigued
- **ACWR (Acute:Chronic Workload Ratio):** Acute load (7-day sum) / Chronic load (28-day weekly average). Status zones based on Gabbett (2016): <0.8 = Undertrained (blue), 0.8–1.0 = Well-managed (green), 1.0–1.3 = Sweet spot (green), 1.3–1.5 = Caution (amber), >1.5 = Danger (red)
- **API:** `GET /api/training/ctl?days=90` returns daily CTL/ATL/TSB data + ACWR with status and guidance
- **Sidebar:** "Training" section with Plans, Calendar, Insights, and Route Planner entries; sidebar is fixed (only content area scrolls)

## Phase 8 — Stretch Goals

- [ ] Additional API sync providers (Fitbit, Wahoo, Polar)
- [x] **Segments v2** — user-defined route segments with PR tracking (rebuilt from scratch)
  - **Model:** `segments` table (id, user_id, name, description, sport_type, start_lat, start_lng, end_lat, end_lng, polyline, distance_m, elevation_gain_m, created_at)
  - **Model:** `segment_efforts` table (id, segment_id, activity_id, user_id, elapsed_time_s, avg_speed, avg_hr, avg_power, start_time, created_at)
  - **Backend:** CRUD API for segments; new uploads scan all segments automatically; manual "Match Activities" button reparses recent raw files (500 limit) to back-fill efforts for old activities via `POST /api/segments/{id}/match`; segment leaderboard (user's PRs)
  - **Frontend:** Segments page (list with search/filter, click to navigate to dedicated detail page); SegmentDetail page (interactive map with elevation profile and synced cursor tooltip via RouteChartPanel, PR card, leaderboard table, paginated effort history with 10 entries per page, edit/delete/match actions in top bar)
  - **Two creation modes:**
    1. **From Activity Detail:** "Create Segment" button opens `SegmentCreateModal` inline (no navigation) showing the activity's single route on the map
    2. **From Segments page:** "Create Segment" fetches all user's routes via `GET /api/stats/activity-routes` and opens the modal showing ALL routes as thin overlay lines — pick start/end on any route
  - **Map component:** `SegmentPickerMap.svelte` — self-contained Leaflet component using `onMount`/`onDestroy` for reliable lifecycle (no `bind:this` + `$effect` inside modal snippets); accepts optional `routes: {polyline, color?}[]` prop for background route overlay; renders inside `SegmentCreateModal`
  - **Detail page:** `SegmentDetail.svelte` — decodes segment polyline, samples ≤100 points, fetches elevation via `routeApi.elevation()`, constructs `TimePoint[]` for `RouteChartPanel`; handles all CRUD and match operations
  - **API:** `POST/GET/PUT/DELETE /api/segments`, `GET /api/segments/{id}/efforts`, `GET /api/segments/{id}/pr`, `GET /api/segments/{id}/leaderboard`, `DELETE /api/segments/{id}/efforts/{effort_id}`
  - **Multi-user:** Any user can create segments; only creator or admin can delete; efforts visible across all users; leaderboard shows all users' best times
  - **Security:** `is_admin` field on User; auth + authorization on all endpoints; only effort owner can delete efforts; unique constraint prevents duplicate efforts
- [x] Segment efforts tracking (per-activity segment attempts)
- [x] **Admin role management** — first registered user is admin by default; admin can promote/revoke admin status for other users
  - Backend: `GET /api/users` (admin-only), `PUT /api/users/{id}/admin` (admin-only, cannot self-modify)
  - Frontend: Profile page shows user list with role badges and toggle buttons (admin-only section)
- [x] **Route planner / route creation tool** — interactive map-based route builder with road/path snapping and elevation profiles
  - **Sidebar:** "Route Planner" entry under Training section (after Insights)
  - **Map:** Leaflet map with tile selector (5 providers); click to add waypoint markers (draggable); route polyline snaps to roads via OSRM routing engine
  - **Routing engine:** OSRM (Open Source Routing Machine) — dev uses public demo server (`router.project-osrm.org`), prod uses self-hosted OSRM Docker container (outside Trace image); sport-independent (foot/cycling/driving profiles)
  - **Known limitation:** OSRM foot profile routes only on paved/pathed surfaces; does not route on trails, dirt paths, or unpaved tracks. Need to evaluate alternatives (GraphHopper, Valhalla, or OSRM with custom profile) for trail routing.
  - **Elevation:** Open-Meteo Elevation API (free, no key, 90m resolution worldwide) — called for each route point to build elevation profile; elevation gain computed from profile
  - **Elevation chart:** uPlot chart below map showing elevation over distance (same pattern as activity detail charts); synced cursor with map marker
  - **Route info panel:** Total distance, elevation gain/loss, estimated duration (configurable pace/speed)
  - **Save/load:** Routes stored in `routes` table (id, user_id, name, waypoints JSON, route_polyline encoded, distance_m, elevation_gain_m, elevation_profile JSON, sport_type, created_at); list saved routes, load to edit, delete
  - **Export:** Download route as GPX file (generate from waypoints + elevation)
  - **API:** `POST /api/routes/plan` (waypoints → OSRM → snapped polyline + distance), `POST /api/routes/elevation` (polyline points → Open-Meteo → elevation profile), CRUD `/api/routes`
  - **Frontend:** New `RoutePlanner.svelte` page — map area (70%), sidebar panel (30%) with waypoint list, elevation chart, route info, save form, saved routes list
- [ ] Power curve (best efforts over standard durations)
- [ ] Webhook support (notify on new activity)
- [ ] PWA (offline support, installable)

## Phase 9 — AI Training Coach

*Conversational AI coach that knows your training history, fitness status, and existing plans. Can suggest new plans, modify existing ones, and answer training questions through a chat interface.*

### Architecture

- **Provider abstraction** (`trace_app/services/ai_provider.py`): abstract `AIProvider` base with `chat(messages, tools)` method; `OpenAIProvider` (uses `openai` SDK, key from `AI_OPENAI_API_KEY` env var) and `OllamaProvider` (calls Ollama `/v1/chat/completions`, URL from `AI_OLLAMA_BASE_URL` env var, default `http://localhost:11434`)
- **Tool definitions** (`trace_app/services/ai_tools.py`): function-calling tools the AI can invoke — `get_user_profile`, `get_recent_activities`, `get_training_status`, `get_current_plans`, `suggest_plan` (capture-only, does not save), `suggest_session` (capture-only)
- **System prompt** (`trace_app/services/ai_prompt.py`): expert coach persona with periodization, progressive overload, CTL targets (30-60 low, 60-90 moderate, 90-120 high per sport), ACWR guidelines (<0.8 de-training, 0.8-1.3 sweet spot, >1.5 danger), 10%/week ramp rate limit
- **Orchestrator** (`trace_app/services/ai_coach.py`): context building (injects profile + recent activities + fitness status into system prompt), tool execution, response formatting
- **Chat models**: new `chat_conversations` and `chat_messages` DB tables for conversation continuity

### API

- `POST /api/ai/chat` — accepts `{ messages: [{ role, content }] }`, returns `{ reply: string, suggestions: PlanSuggestion[] | null }`; `suggest_plan`/`suggest_session` tool calls are captured and returned as structured JSON alongside the text reply (not saved to DB until user confirms)

### Frontend

- **New page** `AiCoach.svelte` — chat message list with markdown rendering, text input, typing indicator
- **Plan suggestion cards**: when AI returns `suggestions`, render as rich cards with inline preview (sessions, targets, weekly breakdown), **"Save to My Plans"** button (calls `POST /api/training/plans` with proposal data, navigates to training plans), **"Refine"** button (pre-fills chat with refinement request)
- **Existing plan modification**: user requests changes → AI calls `get_current_plans` → returns modified suggestion → **"Update Plan"** button calls `PUT /api/training/plans/{id}`
- **Conversation management**: auto-create conversation on first visit, "New Chat" button, recent conversation list (sidebar or dropdown)
- **Routing**: `'ai-coach'` page type in `App.svelte`, navigation button in Training section
- **Configuration**: settings to select provider (OpenAI / Ollama), API key / base URL input, model selection

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Provider abstraction | OpenAI + Ollama | User can choose cloud or fully local |
| Tool calling vs raw JSON | OpenAI tool/function calling | Structured, validated output; works with Ollama too |
| Save flow | Preview → user confirms → save | Prevents AI from cluttering plans without consent |
| Conversation storage | New DB table | Continuity across page refreshes; user can revisit |

### Files

| File | Action |
|------|--------|
| `trace_app/services/ai_provider.py` | Create |
| `trace_app/services/ai_tools.py` | Create |
| `trace_app/services/ai_prompt.py` | Create |
| `trace_app/services/ai_coach.py` | Create |
| `trace_app/models/chat_conversation.py` | Create |
| `trace_app/models/chat_message.py` | Create |
| `trace_app/schemas/ai.py` | Create |
| `trace_app/main.py` | Modify — add `POST /api/ai/chat` |
| `trace_app/config.py` | Modify — add AI config vars |
| `.env.example` | Modify — add AI env vars |
| `frontend/src/pages/AiCoach.svelte` | Create |
| `frontend/src/App.svelte` | Modify — add routing |
| `frontend/src/lib/api/types.ts` | Modify — add AI API methods |
| `migrations/versions/` | Create — chat tables |
