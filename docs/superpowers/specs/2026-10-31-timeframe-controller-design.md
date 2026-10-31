# Divoom TimeFrame Controller — Design

**Date:** 2026-10-31

## Intent

A continuously-running service that cycles the Divoom TimeFrame display through a clock and a set of contextual info slides (weather, rocket launches, door lock status). The device is a dumb display; all logic runs on a host and pushes updates over WiFi via the `divoom-wifi-python` SDK.

## Goals

- Clock as the default resting state (~50s per cycle)
- Rotate through weather, rocket launches, and door lock status (10s each)
- Runs as a Docker container on dockervm (192.168.1.243), its own standalone stack
- Config via `.env` file — no secrets baked in
- Restarts automatically on failure

## Non-Goals

- No web UI or admin interface
- No historical logging of sensor data
- No support for other Divoom devices (TimeFrame only)
- No on-device code — firmware is not modified

## Anti-Goals

- Must not require cloud connectivity to function (local API to TimeFrame, local HA connection)
- Must not fail silently — if a data source is unavailable, show a placeholder/error slide rather than crashing

## Constraints

- TimeFrame IP: 192.168.1.25 (local token: 639954)
- Host: dockervm at 192.168.1.243, Docker + Compose available
- SDK: `divoom-wifi-python` (already proven to connect)
- Python 3.11+

## Architecture

Single Python process in a Docker container. Main loop:

1. Show clock slide (50s)
2. Fetch + show weather slide (10s)
3. Fetch + show rocket launch slide (10s)
4. Fetch + show door lock slide (10s)
5. Repeat

Data is fetched fresh each cycle (no caching needed given low frequency).

## Slides

### Clock
- Uses SDK's `select_clock` method to set a built-in clock face
- Stays for 50 seconds, then switches to custom mode for info slides

### Weather — Oviedo, FL
- Source: `wttr.in` JSON API (no key required)
- URL: `https://wttr.in/Oviedo,FL?format=j1`
- Shows: current temp (°F) and condition description
- Display: text via `update_display_items`

### Rocket Launches — Cape Canaveral
- Source: Launch Library 2 free tier (`https://ll2.thespacedevs.com/2.2.0/launch/upcoming/`)
- Filter: `location__ids=12` (Cape Canaveral / Kennedy Space Center)
- Shows: next launch name and NET (No Earlier Than) date/time
- If no upcoming launches: shows "No launches scheduled"

### Door Locks — Home Assistant
- Source: Home Assistant REST API (`/api/states/<entity_id>`)
- Auth: Bearer token in `.env`
- Entity IDs: configured in `.env` as a comma-separated list
- Shows: lock name + locked/unlocked state for each configured lock
- **Placeholder:** HA_URL and HA_TOKEN are empty by default; if unset, slide shows "HA not configured"

## Configuration (`.env`)

```
TIMEFRAME_IP=192.168.1.25
TIMEFRAME_TOKEN=639954

CLOCK_DURATION=50
SLIDE_DURATION=10

HA_URL=
HA_TOKEN=
HA_LOCK_ENTITIES=

LAUNCH_SITE_ID=12
WEATHER_LOCATION=Oviedo,FL
```

## File Layout

```
divoom/
  docker-compose.yml
  Dockerfile
  .env
  .env.example
  src/
    main.py         # main loop
    slides/
      clock.py
      weather.py
      launches.py
      locks.py
    divoom_client.py  # thin wrapper around SDK connect/reconnect
  requirements.txt
```

## Docker

- Base image: `python:3.11-slim`
- `restart: unless-stopped`
- Mounts `.env` via `env_file`
- No ports exposed (outbound only)
- Own standalone `docker-compose.yml` stack

## Builder Calls (open questions resolved)

- **Slide transition:** enter custom mode for info slides, return to `select_clock` for clock slide
- **Reconnect logic:** if SDK raises a connection error, wait 30s and reconnect before continuing
- **Launch Library rate limiting:** free tier allows 15 req/hour; fetching once per ~70s cycle = ~51 req/hour — builder should cache launch data for 5 minutes to stay within limits
