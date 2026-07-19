# Decisions

Record durable decisions that future agents should not casually relitigate.

## 2026-07-19 - Running/Training Dashboard Name and Data Authority

Decision:
- Call the user-facing product Running Dashboard or Training Dashboard, never Strava Dashboard.
- Use HealthFit/Apple Health/AHE activity plus RunningCoach plans as production sources. Direct Strava API access is optional legacy diagnostics only.

Reasoning:
- Strava API reads are paywalled/inactive and cannot be treated as dependable infrastructure.
- Locally controlled health exports already provide the activity data needed by the dashboard.

Implications:
- Preserve existing `strava` folder, NAS container, machine, route, and diagnostic identifiers for compatibility until a separately planned migration maps every dependency.
- New UI copy and documentation must use Running/Training terminology.

## YYYY-MM-DD - Decision Title

Decision:
- What was decided.

Reasoning:
- Why it was chosen.

Implications:
- What future work should respect.

## 2026-05-20 - Replace Railway With NAS Tunnel

Decision:
- Prefer running the TRMNL Strava dashboard on the UGREEN NAS behind Cloudflare Tunnel instead of continuing Railway hosting.

Reasoning:
- Railway's trial/payment model is a poor fit for a small always-available TRMNL polling endpoint.
- The NAS can run the existing Python app with minimal rewrite.
- Cloudflare Tunnel provides a stable HTTPS URL without router port forwarding.

Implications:
- Keep the app container-friendly.
- Keep secrets in NAS `.env`, not in source.
- Update TRMNL's polling URL only after the tunnel hostname is verified.
