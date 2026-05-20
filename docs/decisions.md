# Decisions

Record durable decisions that future agents should not casually relitigate.

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
