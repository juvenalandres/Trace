# Future Features

## High Priority
- [ ] **Workout Builder** — Improve the existing JSON interval format with a visual editor (drag-and-drop blocks, targets by %FTP/bpm/watts, preview chart)

## Medium Priority
- [x] **HR Zone Distribution (aggregated)** — Pre-computed `hr_zone_seconds` on `activity_stats` (JSON per zone). Startup backfill for existing activities. `GET /api/stats/hr-zone-distribution` aggregates total. `GET /api/stats/hr-zone-weekly` returns weekly buckets. Donut chart with floating tooltip + weekly stacked area trend chart side by side on Training Insights.
- [x] **FTP / LTHR / Threshold Tests** — Dedicated section to log and track test results over time. Upload FIT file, select time window from chart, auto-compute results. HR zone calibration from LTHR test.
- [x] **Standalone Segment Creation** — Create segments without an activity. Click start/end points on map, straight-line distance (haversine) + Open-Meteo elevation lookup.
- [ ] **Aerobic Decoupling (Pa:HR)** — Compute first-half vs second-half HR drift per activity. Show in activity detail stats.

## Low Priority
- [ ] **Power Duration Curve** — Peak power across durations (5s, 1m, 5m, 20m, 60m). Chart with date achieved.
- [ ] **Peak Power Analysis** — Best efforts for each duration, linked to specific activities.
