# Agent Log

Append one entry whenever an AI harness makes meaningful changes.

## 2026-07-19 - Hermes Agent

Summary:
- Standardized the user-facing product as Running Dashboard / Training Dashboard.
- Changed the app's production activity selector to load HealthFit/Apple Health directly instead of attempting the paid Strava API first; retained the old API function only for explicit diagnostics.
- Preserved legacy filesystem, NAS, route, and hostname identifiers to avoid risky filename churn.

Files touched:
- `main.py`, `tests/test_activity_source.py`, `PROJECT_STATE.md`
- `docs/decisions.md`, `docs/agent-log.md`

Verification:
- Local test passed and Python compilation succeeded.
- Live NAS `/activity-health` reports `source = healthfit/apple-health` and the Jul 7 Apple Health run.
- Live `/plan-health` reports `ok = true`, 42 loaded rows, and 7 upcoming W30 rows.
- Live `/trmnl` is nonblank and contains no user-facing `Strava` text.

Open questions / next steps:
- Source is ready, but the NAS container was not rebuilt because the SSH user lacks Docker/sudo permission. The currently deployed app already falls back to local health successfully; deploy the direct-local selector during the next authorized NAS rebuild.

## YYYY-MM-DD - Harness / model

Summary:
- What changed.

Files touched:
- `path`

Verification:
- Command run, result.

Open questions / next steps:
- Anything the next agent should know.

## 2026-05-20 - Codex

Summary:
- Added harness-agnostic project memory scaffold during Atlas/local project reconciliation.
- Filled `PROJECT_STATE.md` with a concise Flask app implementation summary.

Files touched:
- `AGENTS.md`
- `CLAUDE.md`
- `Gemini.md`
- `PROJECT_STATE.md`
- `docs/agent-log.md`
- `docs/decisions.md`
- `docs/setup.md`

Verification:
- Confirmed scaffold files exist.

Open questions / next steps:
- Keep run/deploy requirements and environment-variable notes current.

## 2026-05-20 - Codex

Summary:
- Added NAS-ready Docker packaging for the Strava dashboard.
- Added Cloudflare Tunnel compose sidecar and `.env.example`.
- Added `/health` endpoint for lightweight uptime checks.
- Documented NAS deployment and TRMNL cutover steps.

Files touched:
- `Dockerfile`
- `.dockerignore`
- `compose.yaml`
- `.env.example`
- `main.py`
- `requirements.txt`
- `docs/nas-cloudflare-deploy.md`
- `docs/setup.md`
- `docs/decisions.md`
- `PROJECT_STATE.md`

Verification:
- Ran Flask test client against `/health`, `/plan-health`, and `/trmnl`; all returned 200 locally.
- Docker could not be built on this Mac because `docker` is not installed in the local environment.

Open questions / next steps:
- Install/run the compose bundle on the UGREEN NAS.
- Create a Cloudflare Tunnel and set its public hostname service to `http://strava-dashboard:8080`.
- Update the TRMNL Training Dashboard polling URL to the tunnel hostname plus `/trmnl`.

## 2026-05-20 - Codex

Summary:
- Deployed `trmnl-strava` in the UGREEN NAS Docker app using a GitHub build context.
- Exposed the dashboard locally on NAS port `18080`.
- Confirmed the NAS-hosted app returns upcoming workouts.

Files touched:
- `docs/agent-log.md`

Verification:
- `curl http://192.168.5.3:18080/health` returned 200 with `plan_rows_loaded: 35`.
- `curl http://192.168.5.3:18080/plan-health` returned 11 upcoming rows through 2026-05-30.
- `curl http://192.168.5.3:18080/trmnl` returned JSON markup containing three upcoming workout cards.

Open questions / next steps:
- Cloudflare dashboard requires user login and human verification before creating the tunnel.
- After Cloudflare login, create a tunnel public hostname pointed to the NAS app and update TRMNL's polling URL.

## 2026-06-22 - Codex

Summary:
- Morning watchdog checked the NAS LAN endpoint and Tailscale Funnel endpoint.
- Service health was reachable on both paths and `/trmnl` returned nonblank markup.
- `/plan-health` reported `ok = false`, `plan_rows_loaded = 28`, and `upcoming_rows = 0` through 2026-07-02, so the dashboard is missing upcoming workout data.

Files touched:
- `PROJECT_STATE.md`
- `../../PROJECT_STATE.md`
- `docs/agent-log.md`

Verification:
- `curl http://192.168.5.3:18080/health` returned 200 with `ok = true`.
- `curl https://trmnl-strava-nas.tail7e5673.ts.net/health` returned 200 with `ok = true`.
- `curl` against both `/plan-health` endpoints returned zero upcoming rows.
- `curl` against both `/trmnl` endpoints returned markup of about 19 KB.

Open questions / next steps:
- Sync or generate current RunningCoach plan rows on the NAS-mounted data path so upcoming workouts appear again.

## 2026-07-01 - Codex

Summary:
- Investigated missing June 30 run and suspected Strava API subscription/tier cutoff.
- Confirmed OAuth refresh still succeeds with `activity:read_all read`, but Strava API reads for `/athlete` and `/athlete/activities` return HTTP 403 with `Application.Status = Inactive`.
- Read the saved Strava API Update PDF; it states existing Standard Tier developers require a Strava subscription effective June 30, 2026.
- Added a sanitized `/strava-health` route for on-demand diagnostics without exposing tokens.

Files touched:
- `main.py`
- `PROJECT_STATE.md`
- `../../PROJECT_STATE.md`
- `docs/agent-log.md`
- `../../docs/agent-log.md`

Verification:
- Local Flask test client: `/health` returned 200 and advertises `/strava-health`.
- Local Flask test client: `/strava-health` returned `ok = false`, `stage = athlete`, HTTP 403, `Application.Status = Inactive`.
- Local Flask test client: `/plan-health` returned current local RunningCoach plan rows.
- Chrome was opened to Strava API settings, but Strava redirected to `/login`.
- Public Funnel `/strava-health` currently falls through to Endurain, so expose that diagnostic publicly only after adding the path to the Funnel routing map.

Open questions / next steps:
- User needs to sign in to Strava and reactivate/upgrade the API app in API Settings.
- After reactivation, rerun local `/strava-health`, then deploy/restart the NAS container and add `/strava-health` to Funnel routing if desired.

## 2026-07-01 - Codex

Summary:
- Replaced Strava-only activity rendering with Strava-first, HealthFit/Apple Health fallback rendering.
- Found and normalized the HealthFit FIT export for the missing June 30 run.
- Added `/activity-health` so the effective source and latest run can be checked without exposing private route data or API tokens.
- Copied normalized HealthFit, Apple Health, and RunningCoach plan files to the NAS-mounted data volume.

Files touched:
- `main.py`
- `PROJECT_STATE.md`
- `../../PROJECT_STATE.md`
- `docs/agent-log.md`
- `../../docs/agent-log.md`
- `docs/setup.md`

Verification:
- `PYTHONPATH=vendor/python python3 scripts/normalize_healthfit.py --days 30` in RunningCoach wrote 4 workouts and 18 laps; latest workout was June 30, 2026, 2.96 mi.
- Local Flask test client showed `get_strava_data()` falling back to `local-health`, latest run from HealthFit, 20 activities, and YTD run totals.
- Local `/health`, `/plan-health`, and `/trmnl` returned 200; `/trmnl` markup includes `HealthFit` and the latest outdoor run.
- Copied `data/healthfit`, `data/health`, and current week plan files to `/volume1/docker/trmnl-strava/running-coach/` on the NAS.

Open questions / next steps:
- Rebuild/restart the NAS `trmnl-strava-dashboard` container from the updated repo; SSH user lacks Docker socket permission.
- Optionally route `/activity-health` and `/strava-health` through the shared Tailscale Funnel path map for public diagnostics.

## 2026-07-01 - Codex

Summary:
- Completed the NAS rebuild after Mike entered the sudo password locally.
- Verified the live dashboard now uses the HealthFit/Apple Health fallback over LAN and through the Tailscale Funnel.

Verification:
- LAN `/health` exposes `/activity-health`; LAN `/activity-health` reports `source: healthfit/apple-health`, 20 activities, 11 runs, and latest run `2026-06-30T17:15:07-04:00`, `2.96 mi`.
- LAN `/trmnl` and public Funnel `/trmnl` include `HealthFit` and `Outdoor Running`, and do not include "No recent run".
- Public Funnel `/health` is current. Public `/activity-health` is not currently routed to the dashboard because the shared Funnel path map sends unmatched paths to Endurain.

Open questions / next steps:
- Optionally route `/activity-health` and `/strava-health` through the shared Tailscale Funnel path map for public diagnostics.

## 2026-07-02 - Codex

Summary:
- Morning watchdog checked the NAS LAN endpoint and Tailscale Funnel endpoint.
- Service health was reachable on both paths, `/trmnl` returned nonblank markup, and `/plan-health` reported current upcoming workouts.

Files touched:
- `PROJECT_STATE.md`
- `../../PROJECT_STATE.md`
- `docs/agent-log.md`
- `../../docs/agent-log.md`

Verification:
- `curl`/urllib against LAN and Funnel `/health` returned 200 with `ok = true`.
- `curl`/urllib against LAN and Funnel `/plan-health` returned `plan_rows_loaded = 42` and `upcoming_rows = 4`.
- `curl`/urllib against LAN and Funnel `/trmnl` returned nonblank markup containing HealthFit and upcoming workout content.
- Local `RUNNING_COACH_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/RunningCoach" ./.venv/bin/python check_running_coach_plan.py` loaded 42 rows and 4 upcoming rows through 2026-07-12.

Open questions / next steps:
- Keep monitoring the NAS-mounted RunningCoach data so upcoming workouts remain nonzero.
