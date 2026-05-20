# Agent Log

Append one entry whenever an AI harness makes meaningful changes.

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
