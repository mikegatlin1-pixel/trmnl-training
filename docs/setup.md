# Setup

Document how to run, test, build, deploy, or operate this project.

## Commands

- Run locally: `python main.py`
- Test app routes: `python - <<'PY'
import main
c = main.app.test_client()
for p in ["/health", "/plan-health", "/trmnl"]:
    r = c.get(p)
    print(p, r.status_code, r.content_type, len(r.data))
PY`
- Build NAS container: `docker compose build`
- Deploy on NAS without tunnel: `docker compose up -d --build`
- Deploy on NAS with Cloudflare Tunnel: `docker compose --profile tunnel up -d --build`

## Environment

- Required tools: Python 3.12 locally; Docker Compose on the UGREEN NAS.
- Required local files: optional `RunningCoach/logs/plans/week_YYYY-WNN.md` files or `workouts/training-plan.md`.
- Secrets location, without revealing secret values: `.env` on the NAS, based on `.env.example`.

## Notes

- Railway is no longer preferred because the free trial becomes paid. Use the NAS + Cloudflare Tunnel path in `docs/nas-cloudflare-deploy.md`.
- Current NAS local endpoint: `http://192.168.5.3:18080`.
- Current NAS health checks: `http://192.168.5.3:18080/health` and `http://192.168.5.3:18080/plan-health`.
