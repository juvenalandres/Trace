```text
┌──────────────────────────────────────────────────────────────────────────┐
│                              TRACE                         │
│                       Architecture Overview                              │
│                                                                          │
│               TWO PILLARS: Stats & Viz  +  Training Planning            │
│               Current focus: Both pillars active                        │
└──────────────────────────────────────────────────────────────────────────┘

                                ┌─────────────────┐
                                │   Web Browser   │
                                └────────┬────────┘
                                         │ HTTP/JSON
                                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     BACKEND — Python (FastAPI)                       │
│                                                                     │
│  ┌────────────┐  ┌────────────────────┐  ┌──────────────────────┐  │
│  │  Auth      │  │  REST API          │  │  Background Tasks    │  │
│  │  JWT +     │  │                    │  │  Startup:            │  │
│  │  refresh   │  │  /api/activities   │  │   CTL/ATL/TSB        │  │
│  │  token     │  │  /api/gear         │  │   recomputation      │  │
│  │  rotation  │  │  /api/gear/stats   │  │                      │  │
│  │  httpOnly  │  │  /api/gear/:id/svc │  │                      │  │
│  │  cookie    │  │  /api/routes       │  │                      │  │
│  │            │  │  /api/segments     │  │                      │  │
│  │            │  │  /api/segments/:id/│  │                      │  │
│  │            │  │  match (manual     │  │                      │  │
│  │            │  │  back-fill)        │  │                      │  │
│  │            │  │  /api/stats        │  │                      │  │
│  │            │  │  /api/stats/heatmap│  │                      │  │
│  │            │  │  /api/stats/years  │  │                      │  │
│  │            │  │  /api/training/*   │  │                      │  │
│  │            │  │  /api/users        │  │                      │  │
│  └────────────┘  └────────┬───────────┘  └──────────────────────┘  │
│                           │  uses                                  │
│                  ┌────────▼───────────┐                            │
│                  │  SERVICES LAYER    │                            │
│                  │                    │                            │
│                  │  StatsEngine       │  aggregation queries      │
│                  │  ActivityProcessor │  GPX parse + compute      │
│                  │  EddingtonService  │  E-number computation     │
│                  │  SegmentMatcher    │  Auto-match efforts on    │
│                  │                    │  activity upload          │
│                  │  TrainingLoad      │  TRIMP, CTL/ATL/TSB,     │
│                  │                    │  ACWR computation         │
│                  │  TTLCache          │  in-memory LRU cache      │
│                  │                    │  (256 entries, 60s TTL)   │
│                  └────────────────────┘                            │
└──────────────────────────────────┬─────────────────────────────────┘
                                   │
              ┌────────────────────┼─────────────────────┐
              ▼                    ▼                     ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────────┐
│   GPX Importer   │   │  API Sync       │   │  Manual Entry        │
│  (custom ET      │   │  Connectors     │   │  Form                │
│   parser)        │   │  (planned)      │   │  (activity via JSON) │
│  Extracts any    │   │  ┌────────┐    │   │                      │
│  per-point field │   │  │Garmin │    │   │                      │
│  present in GPX: │   │  │Fitbit │    │   │                      │
│  lat, lng, ele,  │   │  │Wahoo  │    │   │                      │
│  time, hr, cad,  │   │  │Polar  │    │   │                      │
│  power, temp     │   │  └────────┘    │   │                      │
└──────────────────┘   │  │Polar  │    │   └──────────────────────┘
                        │  └────────┘    │
                        └────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────────┐
│                           DATABASE LAYER                               │
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  PostgreSQL 16 (dev + prod)                                     │    │
│  │  ORM: SQLAlchemy 2.0 (async) + Alembic migrations             │    │
│  │                                                                │    │
│  │  Tables:                 Key columns:                          │    │
│  │  ──────────              ────────────────────────────────      │    │
  │  │  users                   email, name, preferred_units,         │    │
│  │                           weight_kg, ftp_watts, max_hr,        │    │
│  │                           resting_hr, is_admin, created_at   │    │
│  │                                                                │    │
│  │  activities              user_id (FK), name, sport_type        │    │
│  │                           (enum: run/ride/swim/hike/walk/      │    │
│  │                           other), start_time, timezone,        │    │
│  │                           source (enum: manual/gpx/fit/garmin),    │    │
│  │                           raw_file_path, gear_id (FK),         │    │
│  │                           notes, rpe, created_at               │    │
│  │                                                                │    │
│  │  activity_stats          activity_id (FK, 1:1), distance_m,   │    │
│  │                           duration_s, moving_time_s,           │    │
│  │                           elevation_gain, elevation_loss,      │    │
│  │                           avg_speed, max_speed, avg_hr,        │    │
│  │                           max_hr, avg_power, max_power,        │    │
│  │                           normalized_power, avg_cadence,       │    │
│  │                           calories, avg_temp, training_load    │    │
│  │                           (TRIMP), polyline,                   │    │
│  │                           simplified_time_series (JSON —       │    │
│  │                           every Nth point), elevation_profile  │    │
│  │                           (JSON), bounds (JSON — min/max       │    │
│  │                           lat/lng)                             │    │
│  │                                                                │    │
│  │  laps                    activity_id (FK), lap_index,          │    │
│  │                           sport_type (enum), distance_m,       │    │
│  │                           duration_s, avg_speed, max_speed,    │    │
│  │                           avg_hr, max_hr, avg_power,           │    │
│  │                           max_power, avg_cadence, calories,    │    │
│  │                           notes                                │    │
│  │                                                                │    │
│  │  gear                    user_id (FK), name, type              │    │
│  │                           (enum: bike/shoes/other), brand,     │    │
│  │                           model, notes, retired, retired_at,   │    │
│  │                           maintenance_interval_km,             │    │
│  │                           last_service_date,                   │    │
│  │                           last_service_distance_m, created_at  │    │
│  │                                                                │    │
│  │  user_zones              user_id (FK), zone_type               │    │
│  │                           (enum: hr/power), zone_1_min,        │    │
│  │                           zone_1_max ... zone_5_min,           │    │
│  │                           zone_5_max, valid_from, created_at   │    │
│  │                                                                │    │
│  │  sync_sources            user_id (FK), provider                │    │
│  │                           (enum: garmin/fitbit/wahoo/polar),   │    │
│  │                           access_token, refresh_token,         │    │
│  │                           token_expires_at, last_sync_at,      │    │
│  │                           sync_state (JSON), created_at        │    │
│  │                                                                │    │
│  │  training_plans          user_id (FK), name, description,      │    │
│  │                           start_date, end_date, created_at     │    │
│  │                                                                │    │
│  │  training_sessions       plan_id (FK), scheduled_date,         │    │
│  │                           sport_type (enum), name,             │    │
│  │                           description, targets (JSON —        │    │
│  │                           array of {type, value, unit}        │    │
│  │                           for distance/duration/pace/         │    │
│  │                           hr_zone/power_zone/free),           │    │
│  │                           intervals (JSON — structured         │    │
│  │                           workout), notes, rest_day,           │    │
│  │                           activity_id                          │    │
│  │                           (FK, nullable), status               │    │
│  │                           (planned/completed/skipped),         │    │
│  │                           created_at                           │    │
│  │                                                                │    │
│  │  daily_training_load     user_id (FK), date, training_load,    │    │
│  │                           ctl (fitness), atl (fatigue),         │    │
│  │                           tsb (form), created_at                │    │
│  │                           Unique constraint on (user_id, date)  │    │
│  │                           Zero-load days backfilled on activity │    │
│  │                           upload and on Insights page load so   │    │
│  │                           CTL/ATL/TSB decay is reflected daily  │    │
│  │                                                                │    │
│  │  refresh_tokens           user_id (FK), token_hash              │    │
│  │                           (SHA-256, unique), family_id          │    │
│  │                           (UUID), revoked (bool),               │    │
│  │                           expires_at, created_at                │    │
│  │                           Indexed on user_id, family_id         │    │
│  │                           Token rotation with reuse detection   │    │
│  │                                                                │    │
│  │  routes                   user_id (FK), name, description,     │    │
│  │                           waypoints (JSON — array of           │    │
│  │                           [lat,lng] pairs), route_polyline     │    │
│  │                           (encoded), distance_m,               │    │
│  │                           elevation_gain_m, elevation_profile  │    │
│  │                           (JSON — array of {distance, elev}),  │    │
│  │                           sport_type (nullable), created_at    │    │
│  │                                                                │    │
│  │  segments                 user_id (FK), name, description,     │    │
│  │                           sport_type (nullable), start_lat,    │    │
│  │                           start_lng, end_lat, end_lng,         │    │
│  │                           polyline (encoded), distance_m,      │    │
│  │                           elevation_gain_m, created_at         │    │
│  │                                                                │    │
│  │  segment_efforts          segment_id (FK), activity_id (FK),   │    │
│  │                           user_id (FK), elapsed_time_s,        │    │
│  │                           avg_speed, avg_hr, avg_power,        │    │
│  │                           start_time, created_at               │    │
│  │                           Unique on (segment_id, activity_id)  │    │
│  │                                                                │    │
│  │  Indexes:                                                      │    │
│  │  ────────                                                      │    │
│  │  activities(user_id, start_time) — dashboard time-range        │    │
│  │  activity_stats(activity_id) — unique (1:1 join)               │    │
│  │  activity_stats(training_load) — sport load distribution       │    │
│  │  training_sessions(plan_id, scheduled_date) — calendar         │    │
│  │  daily_training_load(user_id, date) — unique constraint        │    │
│  │  segments(user_id) — user's segments                           │    │
│  │  segment_efforts(segment_id) — segment history                 │    │
│  │  segment_efforts(activity_id) — activity efforts               │    │
│  │  segment_efforts(user_id) — user's efforts                     │    │
│  │                                                                │    │
│  │  Date helpers: _year_expr, _year_month_expr, _date_expr,       │    │
│  │  _week_start_expr for SQL date arithmetic across queries       │    │
│  │                                                                │    │
│  │  Point storage: simplified JSON (every Nth point) in           │    │
│  │  activity_stats + raw GPX file on disk for reprocessing        │    │
│  └────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────┘

  PostgreSQL Configuration:
  ─────────────────────────
  Connection pooling: asyncpg + SQLAlchemy create_async_engine
    pool_size=5, max_overflow=10, pool_pre_ping=True
  Configurable via env vars:
    TRACE_DATABASE_URL — async connection string
    TRACE_DB_POOL_SIZE — pool size (default 5)
    TRACE_DB_MAX_OVERFLOW — max overflow connections (default 10)
    TRACE_DB_ECHO — log SQL queries (default False)
  Indexes: composite indexes on high-traffic query patterns
  Date helpers: _year_expr, _year_month_expr, _date_expr, _week_start_expr
    for cross-DB date arithmetic (currently PostgreSQL, portable pattern)


┌──────────────────────────────────────────────────────────────────────────┐
│                   FRONTEND — Svelte 5 + Vite                             │
│                                                                          │
│  Build tool: Vite (HMR, TypeScript, bundle splitting)                    │
│  Framework:  Svelte 5 ($state, $derived, $effect — no virtual DOM)      │
│  HTTP layer: fetch wrappers or tanstack-query for caching               │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  PILLAR 1: DATA STATISTICS & VISUALIZATION                      │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │                                                                 │    │
│  │  Dashboard          Activities        Monthly View              │    │
│  │  (stat cards,       (filterable       (4 metric cards,          │    │
│  │   heatmap calendar,  list, detail      calendar grid with       │    │
│  │   sport breakdown,   view with map)    72px cells, today        │    │
│  │   recent feed)                         circle, activity         │    │
│  │                                        sport badges with dist,   │    │
│  │                                        month/year picker        │    │
│  │                                        dropdown, day            │    │
│  │                                        drill-down table)        │    │
│  │                                                                 │    │
│  │  Eddington          Heatmap            Gear Stats               │    │
│  │  (E-number, distri- (Leaflet density   (per-gear distance,      │    │
│  │   bution chart,      overlay, tile      lifetime stats,         │    │
│  │   progress bar,      selector)          maintenance reminders)  │    │
│  │   qualifying list)                                              │    │
│  │                                                                 │    │
│  │  Statistics         Year-in-Review                              │    │
│  │  (year picker,       (full yearly                               │    │
│  │   uPlot volume over   report with monthly                        │    │
│  │   time chart with     breakdown, PRs)                            │    │
│  │   tooltip, sport                                                 │    │
│  │   breakdown, 6-PR                                                │    │
│  │   grid: distance,                                                │    │
│  │   duration, elev,                                                │    │
│  │   avg/top speed,                                                 │    │
│  │   highest avg HR)                                                │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  PILLAR 2: TRAINING PLANNING                                    │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │                                                                 │    │
│  │  Training Plans       Training Calendar      Training Insights  │    │
│  │  (plan list cards,    (month/week toggle,     (4 sections:       │    │
│  │   plan detail with     month: sport chips     Overview,        │    │
│  │   3-col session grid,  on dates; week:        Performance      │    │
│  │   CRUD modals,         larger session cards   Management,      │    │
│  │   sport/target badges, with sport, name,      Volume & Trends, │    │
│  │   multi-target per     targets, status;       Recovery Status; │    │
│  │   session)             day detail modal,       PMC chart, CTL/  │    │
│  │                          weekly progress       ATL/TSB, ACWR,   │    │
│  │                          bars, "View           sport load,      │    │
│  │                          Activity →")          TSB zones,       │    │
│  │                                                weekly volume    │    │
│  │                                                with target      │    │
│  │                                                reference lines) │    │
│  │                                                                 │    │
│  │  Route Planner                                                │    │
│  │  (Leaflet map,        (draggable waypoint   (uPlot elevation    │    │
│  │   click-to-add         markers, OSRM         chart, distance,  │    │
│  │   waypoints,           road snapping,        elevation gain,   │    │
│  │   Esri tiles)          polyline update)      GPX export,       │    │
│  │                                                save/load routes)│    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  SHARED COMPONENTS                                              │    │
│  │                                                                 │    │
│  │  StatCard        StatRow          ActivityTable                 │    │
│  │  (icon top-right, (card style,    (rounded card, sport icon,   │    │
│  │   title uppercase, title left,    two-line name, right-aligned │    │
│  │   metric bold,    metric right,   metrics, units gray small)   │    │
│  │   unit gray,      same font)                                    │    │
│  │   optional color/                                               │    │
│  │   bg props for                                                  │    │
│  │   metric colors)                                                │    │
│  │                                                                 │    │
│  │  HRZones         PowerZones       HeatmapCalendar              │    │
│  │  (heart icon,    (bolt icon,      (12-month SVG grid,          │    │
│  │   avg/max cards,  avg/max watts,   Mon–Sun rows × week cols,   │    │
│  │   zone bars in    zone bars in     3 metric toggles,           │    │
│  │   red shades,     blue shades,     5 green intensity levels)   │    │
│  │   collapsible     collapsible                                  │    │
│  │   on Profile)     on Profile)                                  │    │
│  │                                                                 │    │
│  │  RouteChartPanel  Modal            Icon                         │    │
│  │  (shared tiles,   (generic overlay (SVG icons, no emojis)       │    │
│  │   metric toggles,  dialog)                                      │    │
│  │   synced uPlot                                                 │    │
│  │   charts with                                                  │    │
│  │   shared cursor                                                │    │
│  │   tooltip)                                                     │    │
│  │                                                                 │    │
│  │  TileSelector    LoadingSpinner  ErrorBanner       EmptyState   │    │
│  │  (dropdown in    (animated ring, (red bg + icon,   (icon + msg  │    │
│  │   map corner,     3 sizes,        message +         + action    │    │
│  │   5 tile          gray msg)       retry btn)        btn)        │    │
│  │   providers,                                                  │    │
│  │   localStorage)                                               │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Key libraries:                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Leaflet.js  │  Map rendering (Esri World TopoMap tiles)       │    │
│  │  uPlot       │  Charts with synced cursor, transparent fill    │    │
│  │  polyline    │  Encoded polyline decode for route paths         │    │
│  │  simplifica- │  Douglas-Peucker line simplification             │    │
│  │  tion        │                                                   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Global CSS classes (app.css):                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  .page          │  max-width: 900px, margin auto, padding 24px │    │
│  │  .dash-card     │  surface bg, 0.5px border, 10px radius,     │    │
│  │                 │  16px padding, 20px margin-bottom            │    │
│  │  .card-header   │  flex row, space-between, margin-bottom 14px│    │
│  │  .card-header h3│  14px, weight 600, color text               │    │
│  │  .nav-link      │  (#App.svelte) flex row, gap 10px,          │    │
│  │  (sidebar)      │  color #475569, 14px, 8px radius,           │    │
│  │                 │  active: var(--primary), hover: var(--text)  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│  Pages override only what differs (e.g. margin-bottom: 0 for grid       │
│  layouts, 24px for wider spacing). Profile uses its own .card-header    │
│  pattern for form section headers.                                       │
└──────────────────────────────────────────────────────────────────────────┘


┌──────────────────────────────────────────────────────────────────────────┐
│                       FULL TECHNOLOGY STACK                               │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  LAYER            TECHNOLOGY          STATUS                     │    │
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │  Frontend         Svelte 5 + Vite    Scaffolded, pages built  │    │
│  │  Responsive       CSS @media 768px    Mobile-first done       │    │
│  │  Charts           uPlot                Wrapper component done │    │
│  │  Maps             Leaflet.js          Tile selector (5 providers) │    │
│  │  Backend API      FastAPI (async)     Endpoints implemented  │    │
│  │  ORM              SQLAlchemy 2.0      Models + migrations done│    │
│  │  DB (dev)         PostgreSQL 16       Active                   │    │
│  │  DB (prod)        PostgreSQL 16       Docker Compose active    │    │
│  │  Migrations       Alembic             Migrations active        │    │
│  │  Auth             JWT + rotation       httpOnly cookie,         │    │
│  │                                        reuse detection          │    │
│  │  Caching          TTLCache (in-memory) 256 entries, 60s TTL   │    │
│  │  Background       Activity upload, page load   CTL/ATL/TSB recomputation, │    │
│  │                                        zero-load day backfill  │    │
│  │  Container        Docker Compose      PostgreSQL + app active  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘


                      EXTERNAL INTEGRATIONS (Planned)
┌──────────────────────────────────────────────────────────────────────────┐
│  ┌───────────────────────────────────────────────────────────────┐      │
│  │  Tile Providers (5)   (configurable via TileSelector component) │      │
│  │  Esri TopoMap, OpenTopoMap, OSM Street, CARTO Voyager,         │      │
│  │  Esri Imagery — all free, no API key, localStorage preference  │      │
│  └───────────────────────────────────────────────────────────────┘      │
│  ┌───────────────────────────────────────────────────────────────┐      │
│  │  OSRM (Open Source Routing Machine)                           │      │
│  │  (road snapping for route planner — dev: public demo server,  │      │
│  │   prod: self-hosted Docker container)                          │      │
│  └───────────────────────────────────────────────────────────────┘      │
│  ┌───────────────────────────────────────────────────────────────┐      │
│  │  Open-Meteo Elevation API                                     │      │
│  │  (free, no key, 90m resolution worldwide — elevation          │      │
│  │   profiles for route planner)                                  │      │
│  └───────────────────────────────────────────────────────────────┘      │
│  ┌───────────────────────────────────────────────────────────────┐      │
│  │  Garmin Connect / Fitbit / Wahoo / Polar                       │      │
│  │  (OAuth-based activity sync — Phase 6)                         │      │
│  └───────────────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────────────┘


              ┌──────────────────────────────────────────────┐
              │              DATA FLOW EXAMPLES              │
              │                                              │
               │  GPX / FIT Upload:                             │
               │  Svelte form → /api/activities/upload →     │
               │  ActivityProcessor → activity_stats +        │
               │    polyline + simplified_time_series → DB    │
               │  Raw file saved to disk (raw_file_path)      │
               │  Optional gear_id links activity to gear     │
               │    → distance counts toward maintenance      │
              │                                              │
               │  Dashboard Load:                             │
               │  Svelte onMount → /api/stats/dashboard →    │
               │  Check TTLCache (60s) → if hit, return      │
               │  If miss → 9 queries via asyncio.gather()   │
               │    → cache + return JSON                     │
               │  Cache invalidated on activity mutation      │
              │                                              │
               │  Eddington Load:                             │
               │  Svelte onMount → /api/stats/eddington →    │
               │  StatsEngine.eddington() →                   │
               │    E-number + distribution + qualifying list │
               │    → uPlot line chart + progress bar           │
               │                                              │
                │  Heatmap Load:                               │
                │  Svelte onMount → /api/stats/heatmap →      │
                │  grouped daily aggregates →                  │
                │    SVG grid (53w × 7d) with 3 metric modes  │
                │    (Load / Moving time / Calories)           │
                │                                              │
                │  Available Years:                            │
                │  Svelte onMount → /api/stats/available-years│
                │  → distinct years from user's activities     │
                │  → year picker / year dropdown populated     │
                │  (Statistics, Heatmap pages)                 │
                │                                              │
                │  Route Chart Panel:                          │
                │  Activity detail → /api/activities/:id →    │
                │  activity_stats.simplified_time_series →     │
                │    Leaflet map + synced uPlot charts         │
                │    (elev/speed/HR/power/cad) + HR/Power     │
                │    zone cards (side-by-side when both)       │
               │                                              │
               │  Gear Maintenance:                           │
               │  Gear page → /api/gear/stats →              │
               │  per-gear aggregation (LEFT JOIN from gear)  │
               │    → stats table + progress bars             │
               │  Activity gear assignment:                   │
               │    - Upload page: dropdown to select gear    │
               │    - Edit modal: change/clear gear assignment│
               │    - gear_id on activity → distance counts   │
               │      toward maintenance progress             │
                │  Mark serviced → POST /api/gear/:id/service │
                │    → stamps last_service_date + distance     │
                │    → bar resets to 0                         │
                │                                              │
                │  Training Auto-Link:                         │
                │  Upload activity → /api/activities/upload →  │
                │  after stats computed, before commit:        │
                │    query TrainingSession where                │
                │      scheduled_date = activity date           │
                │      AND activity_id IS NULL                  │
                │      AND status = 'planned'                   │
                │      AND plan belongs to user                 │
                │    match if session.sport_type is null        │
                │      OR session.sport_type = activity type    │
                │    → set session.activity_id = activity.id    │
                │    → set session.status = 'completed'         │
                │  Delete activity → unlink sessions:           │
                │    → clear activity_id, reset to 'planned'   │
                │                                              │
                │  Weekly Volume:                              │
                │  Calendar/Insights →                         │
                │  GET /api/training/weekly-volume?            │
                │    plan_id=X&weeks=24 →                     │
                │  Sum session targets (distance/duration      │
                │    from targets JSON) for planned volume    │
                │  Sum activities in same date range          │
                │    for actual volume                        │
                │  Group by week + sport                     │
                │  → per-week breakdown: planned vs actual   │
                │  Calendar: weekly progress bars            │
                │  Insights: target lines on weekly volume   │
                │    chart (dashed horizontal lines)          │
                │                                              │
                │  Route Planner:                              │
                │  Click map → add waypoint markers           │
                │  → POST /api/routes/plan {waypoints}        │
                │  Backend → OSRM /route/v1/foot/             │
                │    lon1,lat1;lon2,lat2?overview=full         │
                │  → snapped polyline + distance              │
                │  → POST /api/routes/elevation {points}      │
                │  Backend → Open-Meteo /v1/elevation?        │
                │    latitude=...&longitude=...               │
                │  → elevation profile + gain/loss            │
                │  Frontend: draw polyline + uPlot chart      │
                 │  Save → POST /api/routes → DB               │
                 │  Export → generate GPX from waypoints       │
                 │                                              │
                  │  Segments (v2):                              │
                  │  Bidirectional matching:                     │
                  │                                                │
                  │  New activity → scan all segments:           │
                  │  Activity upload → ActivityProcessor         │
                  │  → SegmentMatcher checks all segments      │
                  │    (haversine distance, 50m tolerance)       │
                  │  → If activity passes start + end points   │
                  │    → create SegmentEffort (elapsed time,   │
                  │      avg speed, avg HR, avg power)           │
                  │                                                │
                  │  Back-match old activities (manual):          │
                  │  Segment detail page → "Match Activities"   │
                  │  button → POST /api/segments/{id}/match    │
                  │  → match_activities_for_segment() reparses │
                  │  raw GPX/FIT files of most recent 500      │
                  │  activities matching sport_type → runs     │
                  │  same haversine check → creates efforts   │
                  │                                                │
                  │  Two creation modes:                          │
                  │  1. From Activity Detail: Click "Create       │
                  │     Segment" → modal opens inline showing     │
                  │     the activity's single route on the map   │
                  │     → pick start/end points → POST            │
                  │  2. From Segments page: Click "Create         │
                  │     Segment" → fetches all user's activity    │
                  │     routes (GET /api/stats/activity-routes)  │
                  │     → modal opens showing ALL routes as       │
                  │     thin overlay lines on the map             │
                  │     → pick start/end points on any route      │
                  │                                                │
                  │  Segment detail page:                         │
                  │  Full-page view (replaces old sidebar)        │
                  │  → RouteChartPanel with segment polyline     │
                  │  → Elevation fetched via routeApi.elevation │
                  │  → PR card, leaderboard, paginated efforts  │
                  │  → Edit, delete, match actions in top bar   │
                  │                                                │
                  │  SegmentPickerMap (self-contained Leaflet)    │
                  │  Click start + end points, auto-distance      │
                  │  → POST /api/segments                        │
                  │  Uses onMount/onDestroy for reliable          │
                  │  lifecycle (no bind:this + $effect)          │
                 │                                              │
                 │  Admin:                                      │
                 │  First registration → is_admin=true          │
                 │  Profile → /api/users (admin-only)           │
                 │  → user list with role badges               │
                 │  Toggle admin → PUT /api/users/{id}/admin   │
                 │    (admin-only, cannot self-modify)         │
                 └──────────────────────────────────────────────┘
```

## Data Processing Pipeline

### Raw Data Ingestion

When a GPX file is uploaded, the **GPX Parser** (`services/gpx_parser.py`) extracts every `<trkpt>` element and returns a list of `TrackPoint` objects. Each point can contain:

| Field     | Source                        | Required |
|-----------|-------------------------------|----------|
| `lat`     | `<trkpt lat="...">`          | Yes      |
| `lng`     | `<trkpt lon="...">`          | Yes      |
| `ele`     | `<ele>`                       | No       |
| `time`    | `<time>`                      | No       |
| `hr`      | `<extensions><TrackPointExtension><hr>` | No |
| `cadence` | `<extensions><TrackPointExtension><cad>` | No |
| `power`   | `<extensions><TrackPointExtension><power>` | No |
| `temp`    | `<extensions><TrackPointExtension><atemp>` | No |

The raw GPX file is saved to disk at `data/gpx/{user_id}/` and the path is stored in `activities.raw_file_path`. This preserves the original data for reprocessing if the computation logic changes.

When a **FIT file** is uploaded, the **FIT Parser** (`services/fit_parser.py`) uses the `fitparse` library to extract:

**Session summary** (pre-computed by the device):
- `sport` → mapped to `sport_type` (cycling→ride, running→run, walking→walk, hiking→hike, swimming→swim)
- `total_distance`, `total_elapsed_time`, `total_calories`
- `avg_speed`, `max_speed`, `avg_heart_rate`, `max_heart_rate`
- `start_time`

**Track points** (record messages):
- GPS coordinates in semicircles → converted to degrees (`value * 180 / 2^31`)
- `altitude` / `enhanced_altitude` (meters, -1.0 = no data → forward-filled from last valid value)
- `speed` / `enhanced_speed` (m/s)
- `heart_rate`, `cadence`, `power`, `temperature`

**Key differences from GPX:**
- Session summary provides pre-computed stats (no need to derive from points)
- Calories are available directly (always null from GPX)
- Sport type is provided (GPX has no concept of sport)
- Elevation data may be sparse (forward-filled to enable gain/loss computation)
- `activity_processor.process_activity()` accepts optional `session_overrides` dict — session values replace computed values when present

### Computed Stats

The **Activity Processor** (`services/activity_processor.py`) takes the parsed `TrackPoint[]` and computes:

**Activity-level stats** (stored in `activity_stats` table):

| Stat            | How it's computed                                                  |
|-----------------|--------------------------------------------------------------------|
| `distance_m`    | Sum of haversine distance between consecutive points               |
| `duration_s`    | `last_point.time - first_point.time`                               |
| `moving_time_s` | Sum of time deltas where speed > 0.5 m/s (filters stopped time)   |
| `elevation_gain`| Sum of positive elevation differences between consecutive points   |
| `elevation_loss`| Sum of negative elevation differences (absolute value)            |
| `avg_speed`     | `distance_m / duration_s`                                          |
| `max_speed`     | Max of `segment_distance / time_diff` across all segments          |
| `avg_hr`        | Mean of all non-null HR values                                     |
| `max_hr`        | Max of all non-null HR values                                      |
| `avg_power`     | Mean of all non-null power values                                  |
| `max_power`     | Max of all non-null power values                                   |
| `avg_cadence`   | Mean of all non-null cadence values                                |
| `avg_temp`      | Mean of all non-null temperature values                            |
| `calories`      | `None` for GPX (not in spec); populated from Garmin API sync       |

**Spatial data** (stored in `activity_stats`):

| Field                    | Description                                              |
|--------------------------|----------------------------------------------------------|
| `polyline`               | Google-encoded polyline of lat/lng (for Leaflet渲染)     |
| `elevation_profile`      | JSON array of `[cumulative_distance, elevation]` pairs   |
| `simplified_time_series` | JSON array of every Nth point (default: every 10th)      |
| `min_lat / max_lat / min_lng / max_lng` | Bounding box for map fitBounds |

**Simplified time series** — each entry contains:
```json
{
  "d": 1234.5,       // cumulative distance (m)
  "ele": 142.3,      // elevation (m)
  "spd": 3.2,        // speed (m/s)
  "pace": 5.21,      // pace (min/km, only for run/walk/hike/swim)
  "hr": 145,         // heart rate (bpm)
  "pwr": 220,        // power (watts)
  "cad": 88,         // cadence (spm)
  "lat": 38.7223,    // latitude
  "lng": -9.1393     // longitude
}
```
This is the primary data source for charts, maps, and zone calculations on the frontend. Reduces data size by ~90% vs full point array while preserving all fields needed for visualization.

**Time Series Storage — Current vs Future:**

Currently, `simplified_time_series` is a JSON string stored in the same row as aggregate stats in `activity_stats`. This works for small databases but has scaling problems:

```
CURRENT (JSON blob in activity_stats):
┌──────────────────────────────────────────────────────────┐
│  activity_stats row                                      │
│  ├─ distance_m: 12500                                    │
│  ├─ duration_s: 3600                                     │
│  ├─ avg_hr: 155                                          │
│  ├─ polyline: "encoded_polyline..."                      │
│  └─ simplified_time_series: "[{d:0,hr:145,spd:2.8},     │ ← 50-200KB JSON blob
│     {d:50,hr:150,spd:3.1}, ...]"                        │   loaded for EVERY
└──────────────────────────────────────────────────────────┘   dashboard/stats query

PROBLEM: Dashboard queries SUM(distance_m), AVG(avg_hr) — they only need the
aggregate columns. But because time_series is in the same row, PostgreSQL
must read the entire row (including the 200KB JSON blob) for every activity.
At 10,000 activities, that's ~2GB of unnecessary data scanned.
```

**Future: Normalized time series table (Phase 6.4):**

```
NORMALIZED (separate table):
┌─────────────────────────────────────────────┐
│  activity_stats row (SMALL, always loaded)  │
│  ├─ distance_m: 12500                       │
│  ├─ duration_s: 3600                        │
│  ├─ avg_hr: 155                             │
│  └─ polyline: "encoded_polyline..."         │ ← ~1KB, fast for aggregates
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  activity_time_series rows (LARGE, loaded only on demand)   │
│  ├─ (activity_id=1, idx=0, d=0,    ele=45, spd=2.8, hr=145)│
│  ├─ (activity_id=1, idx=1, d=50,   ele=46, spd=3.1, hr=150)│ ← each row ~100 bytes
│  ├─ (activity_id=1, idx=2, d=100,  ele=47, spd=2.9, hr=148)│
│  └─ ... (100-500 rows per activity)                         │
└─────────────────────────────────────────────────────────────┘

BENEFIT: Dashboard queries only touch the small activity_stats rows.
Activity detail page JOINs to time_series table only when opened.
```

**Columnar storage (for very large datasets, 100k+ activities):**

Traditional row-based storage (PostgreSQL default) stores all columns of a row together. Columnar storage stores each column separately — all HR values in one block, all speed values in another.

```
ROW-BASED (PostgreSQL default):
  Row 1: [d=0,   ele=45, spd=2.8, hr=145, lat=38.1, lng=-3.9]
  Row 2: [d=50,  ele=46, spd=3.1, hr=150, lat=38.1, lng=-3.9]
  Row 3: [d=100, ele=47, spd=2.9, hr=148, lat=38.1, lng=-3.9]
  (reading HR requires scanning entire rows)

COLUMNAR:
  d:    [0,    50,   100,  ...]
  ele:  [45,   46,   47,   ...]
  spd:  [2.8,  3.1,  2.9,  ...]
  hr:   [145,  150,  148,  ...]  ← read only HR column, skip the rest
  (much faster for "what was my average HR?" queries)
```

For Trace, columnar storage becomes relevant when:
- Users have 100k+ activities and want cross-activity time series analysis
- Querying patterns like "show me my HR distribution across all activities"
- Running ML/analysis on historical performance data

**Practical path:**
1. **Now**: JSON blobs work fine for <10k activities per user
2. **Phase 6.4**: Move to normalized `activity_time_series` table (PostgreSQL)
3. **Later**: If needed, use TimescaleDB extension (PostgreSQL) for time-series specific optimizations (compression, continuous aggregates, chunking by time range)

**Lap stats** (stored in `laps` table, one row per lap):

| Stat          | Description                                    |
|---------------|------------------------------------------------|
| `lap_index`   | Sequential lap number (0-based)                |
| `distance_m`  | Distance covered in this lap                   |
| `duration_s`  | Time for this lap                              |
| `avg_speed`   | Mean segment speed within the lap              |
| `max_speed`   | Max segment speed within the lap               |
| `avg_hr`      | Mean HR within the lap                         |
| `max_hr`      | Max HR within the lap                          |
| `avg_power`   | Mean power within the lap                      |
| `max_power`   | Max power within the lap                       |
| `avg_cadence` | Mean cadence within the lap                    |

Laps are auto-generated every 1km (configurable). The remaining distance after the last full lap becomes the final lap if > 10m.

### Storage Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        STORAGE LAYERS                            │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  DISK — Raw files                                       │    │
│  │                                                         │    │
│  │  data/gpx/{user_id}/{activity_id}.gpx                   │    │
│  │  - Original GPX XML, untouched                          │    │
│  │  - Referenced by activities.raw_file_path                │    │
│  │  - Used for reprocessing if logic changes               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  DATABASE — activities table                            │    │
│  │                                                         │    │
│  │  Core metadata: name, sport_type, start_time,           │    │
│  │  timezone, source, gear_id, notes, rpe                  │    │
│  │  - Written once on import                               │    │
│  │  - Queryable, indexed                                   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  DATABASE — activity_stats table (1:1 with activities)  │    │
│  │                                                         │    │
│  │  Summary columns: distance_m, duration_s, moving_time_s,│    │
│  │  elevation_gain/loss, avg/max speed, avg/max HR,        │    │
│  │  avg/max power, avg_cadence, calories, avg_temp         │    │
│  │  - Fast SQL aggregations (SUM, AVG, COUNT)              │    │
│  │  - Used by dashboard, stats, heatmap endpoints          │    │
│  │                                                         │    │
│  │  Spatial columns: polyline (text),                      │    │
│  │  elevation_profile (JSON), simplified_time_series (JSON),│    │
│  │  min/max lat/lng                                        │    │
│  │  - Used by map, charts, zone calculations               │    │
│  │  - Avoids re-parsing GPX for rendering                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  DATABASE — laps table (1:N with activities)            │    │
│  │                                                         │    │
│  │  One row per auto-generated lap:                        │    │
│  │  lap_index, distance_m, duration_s, avg/max speed,      │    │
│  │  avg/max HR, avg/max power, avg_cadence                 │    │
│  │  - Generated on import (every 1km)                      │    │
│  │  - Displayed on activity detail page                    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Processing Flow

```
GPX / FIT Upload (with optional gear_id)
    │
    ▼
parse_gpx(content) or parse_fit(content) → TrackPoint[]
    │                 (lat, lng, ele, time, hr, cad, power, temp)
    │
    ├─► Save raw file to disk → activities.raw_file_path
    │
    ▼
process_activity(points, session_overrides?)
    │
    ├─► compute_stats(points)
    │     distance, duration, moving_time, elevation gain/loss,
    │     avg/max speed, avg/max HR, avg/max power, avg cadence,
    │     avg temp
    │     (FIT: session_overrides replace computed values when present)
    │
    ├─► encode_polyline(points) → Google-encoded string
    │
    ├─► build_elevation_profile(points) → [[dist, ele], ...]
    │
    ├─► build_simplified_time_series(points, nth=10)
    │     → [{d, ele, spd, pace, hr, pwr, cad, lat, lng}, ...]
    │
    ├─► generate_laps(points, interval_m=1000)
    │     → [{lap_index, distance_m, duration_s, avg_speed, ...}, ...]
    │
    └─► Compute bounding box (min/max lat/lng)
    │
    ▼
Store in DB:
    activities       ← metadata + gear_id (if selected)
    activity_stats   ← all computed fields + JSON blobs
    laps             ← one row per lap
```
