# Project State

## What This Is

Flask app implementation for the TRMNL Strava Training Dashboard.

## Current Milestone

Active/supporting app implementation with local plan loaders, Strava/weather rendering, and NAS-ready Docker deployment.

## Recent Changes

- 2026-05-20: Harness-agnostic scaffold added during Atlas project reconciliation.
- 2026-05-20: Added Docker/Compose packaging and Cloudflare Tunnel deployment notes to replace Railway hosting.

## Next Likely Action

- Deploy to UGREEN NAS, create a Cloudflare Tunnel public hostname, then update TRMNL's Training Dashboard polling URL to the tunnel `/trmnl` endpoint.

## Watchouts

- Do not log API secrets or service credential JSON.
