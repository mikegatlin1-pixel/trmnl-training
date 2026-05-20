# NAS + Cloudflare Tunnel Deployment

This is the preferred replacement for Railway. It runs the TRMNL Strava dashboard on the UGREEN NAS and exposes it to TRMNL through a free Cloudflare Tunnel.

## What Runs

- `strava-dashboard`: the Python/Flask dashboard on port `8080`.
- `cloudflared`: an outbound-only Cloudflare Tunnel connector.

TRMNL should poll:

```text
https://YOUR-CLOUDFLARE-HOSTNAME/trmnl
```

Health checks:

```text
https://YOUR-CLOUDFLARE-HOSTNAME/health
https://YOUR-CLOUDFLARE-HOSTNAME/plan-health
```

## NAS Folder Layout

Suggested NAS folder:

```text
/volume1/docker/trmnl-strava/
  app/
  running-coach/
  workouts/
```

Place this project folder's app files in `app/`. Put weekly plan markdown files under:

```text
/volume1/docker/trmnl-strava/running-coach/logs/plans/week_YYYY-WNN.md
```

The simpler fallback markdown file can live at:

```text
/volume1/docker/trmnl-strava/workouts/training-plan.md
```

## Setup

1. Copy `.env.example` to `.env`.
2. Fill in Strava credentials and confirm the NAS folder paths.
3. In Cloudflare Zero Trust, create a Tunnel and choose Docker as the connector.
4. Copy only the tunnel token value into `CLOUDFLARE_TUNNEL_TOKEN`.
5. In the tunnel public hostname settings, point your hostname to:

```text
http://strava-dashboard:8080
```

6. Start the dashboard:

```bash
docker compose up -d --build
```

7. Start the dashboard plus tunnel:

```bash
docker compose --profile tunnel up -d --build
```

8. Check logs:

```bash
docker compose logs -f strava-dashboard
docker compose logs -f cloudflared
```

## TRMNL Cutover

In the TRMNL private plugin settings for Training Dashboard:

- Strategy: `Polling`
- Polling URL: `https://YOUR-CLOUDFLARE-HOSTNAME/trmnl`
- Verb: `GET`
- Refresh rate: every 15 minutes or every 30 minutes

After saving, use Force Refresh once.

## Notes

- Do not expose port `8080` publicly on your router.
- Cloudflare Tunnel makes an outbound connection from the NAS, so port forwarding is not required.
- Keep `.env` only on the NAS or trusted local machines.
