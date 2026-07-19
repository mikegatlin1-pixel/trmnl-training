# Project State

## What This Is

Flask app implementation for the TRMNL Strava Training Dashboard.

## Current Milestone

Active/supporting app implementation with local plan loaders, Strava/weather rendering, and NAS-ready Docker deployment.

## Recent Changes

- 2026-07-02: Morning watchdog confirmed live LAN and Tailscale Funnel `/plan-health` are healthy with `plan_rows_loaded = 42` and `upcoming_rows = 4`; `/trmnl` is nonblank and includes HealthFit content plus upcoming workouts.
- 2026-07-01: Added HealthFit/Apple Health activity fallback so the dashboard can keep working without Strava Premium/API reactivation. `get_strava_data()` now tries Strava first and falls back to local normalized CSVs when Strava reads fail. Added `/activity-health` to show the effective source and latest run. Local verification used HealthFit's June 30 FIT export and showed source `local-health`, latest run `2.96 mi`; NAS container was rebuilt from GitHub and live LAN/Funnel `/trmnl` now renders the latest HealthFit run.
- 2026-07-01: Incident check for missing June 30 run found Strava OAuth refresh still works, but Strava API reads return HTTP 403 with `Application.Status = Inactive`. Added a sanitized `/strava-health` route for on-demand diagnosis without logging tokens. Strava's June 1 API update email says existing Standard Tier developers require a Strava subscription effective June 30, 2026, so reactivation is account-side in Strava API Settings.
- 2026-06-30: Morning watchdog confirmed the NAS/Funnel service is reachable and `/trmnl` returns nonblank markup, but `/plan-health` reported `upcoming_rows = 0` through 2026-07-10 even though `plan_rows_loaded = 35`. The local iCloud RunningCoach W27 file exists and local `.venv` verification loads 6 upcoming rows, so the NAS-mounted RunningCoach plan data needs sync/restart attention.
- 2026-06-22: Morning watchdog confirmed the NAS/Funnel service is reachable and `/trmnl` returns nonblank markup, but `/plan-health` reported `upcoming_rows = 0` through 2026-07-02 even though `plan_rows_loaded = 28`. The NAS-mounted RunningCoach plan data needs current upcoming rows.
- 2026-05-20: Harness-agnostic scaffold added during Atlas project reconciliation.
- 2026-05-20: Added Docker/Compose packaging and Cloudflare Tunnel deployment notes to replace Railway hosting.

## Next Likely Action

- Monitor the first few TRMNL refreshes through the Tailscale Funnel URL.

## Watchouts

- Do not log API secrets or service credential JSON.
- Do not log private workout details beyond operational summaries.
- Keep `/health` cheap; use `/strava-health` for explicit Strava API diagnostics so routine uptime checks do not burn Strava read limits.
- Prefer HealthFit `data/healthfit/workouts_summary.csv` for recent workout sessions, with Apple Health `data/health/workouts_detailed.csv` as backup.
