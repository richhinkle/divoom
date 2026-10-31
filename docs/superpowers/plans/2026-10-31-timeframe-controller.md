# TimeFrame Controller Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a Docker stack on dockervm that cycles a Divoom TimeFrame between an analog clock face and a live info panel showing weather, rocket launches, and door lock status.

**Architecture:** Two Docker services share one image — `server` (FastAPI serving `/launch` and `/locks` JSON) and `controller` (loop that switches the device between ClockId 570 and a custom `EnterCustomControlMode` info panel). The TimeFrame fetches live data itself via NetData elements pointing at the server. The controller just drives the mode switching.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, requests, httpx, python-dotenv, pytest

**Spec:** `docs/superpowers/specs/2026-10-31-timeframe-controller-design.md`

## Global Constraints

- Python 3.11+
- Device IP: `192.168.1.25`, local token: `639954`, API port: `9000`, endpoint: `/divoom_api`
- Server host: dockervm `192.168.1.243`, port `8080`
- Analog clock face: `Channel/SetClockSelectId` with `ClockId: 570`
- Info panel: `Device/EnterCustomControlMode` → 15s → `Device/ExitCustomControlMode`
- Clock duration default: `50s`; slide duration default: `15s`
- Launch Library 2 free tier: cache results for 5 minutes (≤15 req/hour)
- Launch location filter: `location__ids=12` (Cape Canaveral / KSC)
- If HA not configured (empty `HA_URL`), `/locks` returns `{}`
- On data-fetch failure: skip the slide, do not crash
- Display resolution: 800×1280 px (portrait)

## Review Focus

- **Device unreachable at startup**: controller should log and retry with 30s backoff, not exit
- **Launch Library 2 returns empty list**: `/launch` should return `{"name": "No launches scheduled", "net": "", "days": -1}`
- **HA token valid but entity not found**: log the missing entity, return partial results for the others
- **Controller crashes mid-cycle leaving device in custom mode**: on restart, always send `ExitCustomControlMode` before entering the loop
- **NetData `RequestTime` minimum is 10s**: setting it below 10 causes undefined behavior — lock poll must be ≥ 10 in display payload

---

## File Structure

```
divoom/
  Dockerfile
  docker-compose.yml
  .env.example
  requirements.txt
  src/
    config.py          # Reads all env vars, single Config dataclass
    divoom.py          # HTTP client: send_command() to device
    launches.py        # Fetch + cache next Cape Canaveral launch
    locks.py           # Fetch HA lock states
    display.py         # Build EnterCustomControlMode payload
    server.py          # FastAPI: GET /launch, GET /locks
    controller.py      # Main loop: clock ↔ info panel
    main_server.py     # Entrypoint: uvicorn server
    main_controller.py # Entrypoint: controller loop
  tests/
    test_divoom.py
    test_launches.py
    test_locks.py
    test_display.py
    test_server.py
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `src/__init__.py` (empty)
- Create: `tests/__init__.py` (empty)

- [ ] **Step 1: Write `requirements.txt`**

```
fastapi==0.115.0
uvicorn==0.30.0
requests==2.32.3
httpx==0.27.0
python-dotenv==1.0.1
pytest==8.3.2
pytest-asyncio==0.23.8
httpx==0.27.0
```

- [ ] **Step 2: Write `Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
```

- [ ] **Step 3: Write `docker-compose.yml`**

Two services using same build context, different entrypoints, both with `restart: unless-stopped` and `env_file: .env`:
- `server`: `command: python -m src.main_server`; `ports: ["8080:8080"]`
- `controller`: `command: python -m src.main_controller`; no ports

- [ ] **Step 4: Write `.env.example`**

```
TIMEFRAME_IP=192.168.1.25
TIMEFRAME_TOKEN=639954
SERVER_HOST=0.0.0.0
SERVER_PORT=8080
SERVER_BASE_URL=http://192.168.1.243:8080
CLOCK_DURATION=50
SLIDE_DURATION=15
HA_URL=
HA_TOKEN=
HA_LOCK_ENTITIES=
LAUNCH_LOCATION_ID=12
WEATHER_LOCATION=Oviedo,FL
```

- [ ] **Step 5: Commit**

```bash
git add Dockerfile docker-compose.yml requirements.txt .env.example src/__init__.py tests/__init__.py
git commit -m "feat: project scaffold for TimeFrame controller"
```

---

## Task 2: Config + Divoom Client

**Files:**
- Create: `src/config.py`
- Create: `src/divoom.py`
- Create: `tests/test_divoom.py`

**Interfaces:**
- Produces:
  - `Config` dataclass with fields: `timeframe_ip: str`, `timeframe_token: int`, `server_base_url: str`, `clock_duration: int`, `slide_duration: int`, `ha_url: str`, `ha_token: str`, `ha_lock_entities: list[str]`, `launch_location_id: int`
  - `load_config() -> Config` reads from env via `python-dotenv`
  - `send_command(ip: str, token: int, payload: dict) -> dict` — raises `DivoomError(message, return_code)` if `ReturnCode != 0`
  - `class DivoomError(Exception)` with `.return_code: int`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_divoom.py
from unittest.mock import patch, Mock
import pytest
from src.divoom import send_command, DivoomError

def test_send_command_returns_response_on_success():
    mock_resp = Mock()
    mock_resp.json.return_value = {"ReturnCode": 0}
    with patch("src.divoom.requests.get", return_value=mock_resp):
        result = send_command("192.168.1.25", 639954, {"Command": "Channel/OnOffScreen", "OnOff": 1})
    assert result == {"ReturnCode": 0}

def test_send_command_raises_on_nonzero_return_code():
    mock_resp = Mock()
    mock_resp.json.return_value = {"ReturnCode": 5, "ReturnMessage": "error"}
    with patch("src.divoom.requests.get", return_value=mock_resp):
        with pytest.raises(DivoomError) as exc_info:
            send_command("192.168.1.25", 639954, {"Command": "bad"})
    assert exc_info.value.return_code == 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_divoom.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement `src/config.py` and `src/divoom.py`**

`config.py`: `load_config()` calls `load_dotenv()` then reads env vars with `os.getenv`. `HA_LOCK_ENTITIES` splits on `,` and strips whitespace; empty string → empty list.

`divoom.py`: `send_command` POSTs JSON to `http://{ip}:9000/divoom_api` using `requests.get` (the API uses GET with a JSON body — pass `json=payload`). Timeout: 10s.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_divoom.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/config.py src/divoom.py tests/test_divoom.py
git commit -m "feat: config loader and divoom HTTP client"
```

---

## Task 3: Launch Fetcher

**Files:**
- Create: `src/launches.py`
- Create: `tests/test_launches.py`

**Interfaces:**
- Consumes: `requests`
- Produces: `get_next_launch() -> dict` — always returns a dict with keys `name: str`, `net: str`, `days: int`. Returns `{"name": "No launches scheduled", "net": "", "days": -1}` when list is empty or fetch fails.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_launches.py
from unittest.mock import patch, Mock
from src.launches import get_next_launch

SAMPLE_RESPONSE = {
    "results": [{
        "name": "Falcon 9 Block 5 | Starlink",
        "net": "2026-11-03T02:15:00Z",
        "pad": {"location": {"name": "Kennedy Space Center"}}
    }]
}

def test_returns_launch_name_and_formatted_net():
    mock_resp = Mock()
    mock_resp.json.return_value = SAMPLE_RESPONSE
    mock_resp.raise_for_status = Mock()
    with patch("src.launches.requests.get", return_value=mock_resp):
        result = get_next_launch()
    assert result["name"] == "Falcon 9 Block 5 | Starlink"
    assert "Nov" in result["net"]
    assert isinstance(result["days"], int)

def test_returns_fallback_on_empty_results():
    mock_resp = Mock()
    mock_resp.json.return_value = {"results": []}
    mock_resp.raise_for_status = Mock()
    with patch("src.launches.requests.get", return_value=mock_resp):
        result = get_next_launch()
    assert result["name"] == "No launches scheduled"
    assert result["days"] == -1

def test_returns_fallback_on_request_error():
    with patch("src.launches.requests.get", side_effect=Exception("timeout")):
        result = get_next_launch()
    assert result["name"] == "No launches scheduled"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_launches.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement `src/launches.py`**

URL: `https://ll2.thespacedevs.com/2.3.0/launches/upcoming/?location__ids={LAUNCH_LOCATION_ID}&limit=1&format=json`

Cache: module-level `_cache: dict | None = None` and `_cache_time: float = 0`. Return cached result if `time.time() - _cache_time < 300`.

`net` formatting: parse ISO UTC with `datetime.fromisoformat`, convert to US/Eastern, format as `"Nov 3, 2:15 AM ET"`. `days` = `(net_dt.date() - date.today()).days`.

Truncate `name` to 35 characters.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_launches.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/launches.py tests/test_launches.py
git commit -m "feat: launch fetcher with 5-minute cache"
```

---

## Task 4: Locks Fetcher

**Files:**
- Create: `src/locks.py`
- Create: `tests/test_locks.py`

**Interfaces:**
- Produces: `get_lock_states(ha_url: str, ha_token: str, entities: list[str]) -> dict[str, str]`
  - Returns `{"front_door": "LOCKED", "garage": "UNLOCKED"}` — keys are entity IDs with `lock.` prefix stripped, values uppercased.
  - Returns `{}` if `ha_url` is empty or entities list is empty.
  - Skips missing entities (logs warning), returns partial results.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_locks.py
from unittest.mock import patch, Mock
from src.locks import get_lock_states

def test_returns_empty_when_ha_url_not_configured():
    result = get_lock_states("", "", ["lock.front_door"])
    assert result == {}

def test_returns_lock_states():
    def mock_get(url, headers, timeout):
        m = Mock()
        m.json.return_value = {"state": "locked"}
        m.raise_for_status = Mock()
        return m
    with patch("src.locks.requests.get", side_effect=mock_get):
        result = get_lock_states("http://ha.local:8123", "token123", ["lock.front_door"])
    assert result == {"front_door": "LOCKED"}

def test_strips_lock_prefix_from_key():
    def mock_get(url, headers, timeout):
        m = Mock()
        m.json.return_value = {"state": "unlocked"}
        m.raise_for_status = Mock()
        return m
    with patch("src.locks.requests.get", side_effect=mock_get):
        result = get_lock_states("http://ha.local:8123", "tok", ["lock.garage"])
    assert "garage" in result
    assert result["garage"] == "UNLOCKED"

def test_returns_partial_on_missing_entity():
    def mock_get(url, headers, timeout):
        if "missing" in url:
            raise Exception("404")
        m = Mock()
        m.json.return_value = {"state": "locked"}
        m.raise_for_status = Mock()
        return m
    with patch("src.locks.requests.get", side_effect=mock_get):
        result = get_lock_states("http://ha.local", "tok", ["lock.front_door", "lock.missing"])
    assert "front_door" in result
    assert "missing" not in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_locks.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement `src/locks.py`**

For each entity, GET `{ha_url}/api/states/{entity}` with header `Authorization: Bearer {ha_token}`. Strip `lock.` prefix from entity ID for the key. Uppercase the state value. Catch per-entity exceptions, log with `logging.warning`, continue.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_locks.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/locks.py tests/test_locks.py
git commit -m "feat: home assistant lock state fetcher"
```

---

## Task 5: FastAPI Server

**Files:**
- Create: `src/server.py`
- Create: `src/main_server.py`
- Create: `tests/test_server.py`

**Interfaces:**
- Consumes: `get_next_launch() -> dict`, `get_lock_states(...) -> dict`, `load_config() -> Config`
- Produces:
  - `GET /launch` → `{"name": str, "net": str, "days": int}`
  - `GET /locks` → flat dict of lock key → state string
  - `GET /health` → `{"status": "ok"}`
  - `app: FastAPI` instance importable from `src.server`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_server.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

def test_launch_endpoint_returns_expected_shape():
    from src.server import app
    client = TestClient(app)
    with patch("src.server.get_next_launch", return_value={"name": "Falcon 9", "net": "Nov 3", "days": 2}):
        resp = client.get("/launch")
    assert resp.status_code == 200
    data = resp.json()
    assert "name" in data and "net" in data and "days" in data

def test_locks_endpoint_returns_dict():
    from src.server import app
    client = TestClient(app)
    with patch("src.server.get_lock_states", return_value={"front_door": "LOCKED"}):
        resp = client.get("/locks")
    assert resp.status_code == 200
    assert resp.json() == {"front_door": "LOCKED"}

def test_health_endpoint():
    from src.server import app
    client = TestClient(app)
    assert client.get("/health").status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_server.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement `src/server.py`**

`app = FastAPI()`. Each route calls the appropriate fetcher using config loaded at module import via `load_config()`. Pass `ha_url`, `ha_token`, `ha_lock_entities` from config to `get_lock_states`.

- [ ] **Step 4: Implement `src/main_server.py`**

```python
import uvicorn
from src.config import load_config
from src.server import app

if __name__ == "__main__":
    cfg = load_config()
    uvicorn.run(app, host=cfg.server_host, port=cfg.server_port)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_server.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/server.py src/main_server.py tests/test_server.py
git commit -m "feat: FastAPI server with /launch and /locks endpoints"
```

---

## Task 6: Display Builder

**Files:**
- Create: `src/display.py`
- Create: `tests/test_display.py`

**Interfaces:**
- Produces: `build_info_panel(server_base_url: str, lock_entity_keys: list[str]) -> dict`
  - Returns a complete `Device/EnterCustomControlMode` payload dict.
  - `DispList` contains: Time (ID 1), Date (ID 2), Temperature (ID 3), Weather (ID 4), launch name NetData (ID 5), launch NET NetData (ID 6), lock NetData elements (IDs 10+, one per key, max 4).
  - All NetData elements point to `{server_base_url}/launch` or `{server_base_url}/locks`.
  - Lock `RequestTime`: 30. Launch `RequestTime`: 300.

Layout (800×1280, dark bg `#111111`):

| ID | Type | StartX | StartY | Width | Height | FontSize | FontID | FontColor | Align |
|----|------|--------|--------|-------|--------|----------|--------|-----------|-------|
| 1 | Time | 0 | 80 | 800 | 200 | 150 | 52 | #FFFFFF | 2 |
| 2 | Date | 0 | 290 | 800 | 70 | 50 | 52 | #AAAAAA | 2 |
| 3 | Temperature | 0 | 380 | 400 | 60 | 45 | 52 | #FFD700 | 2 |
| 4 | Weather | 400 | 375 | 64 | 64 | 45 | 52 | #FFFFFF | 2 |
| 5 | NetData (launch name) | 20 | 520 | 760 | 70 | 45 | 52 | #00BFFF | 2 |
| 6 | NetData (launch net) | 20 | 600 | 760 | 60 | 40 | 52 | #87CEEB | 2 |
| 7 | Text (label "LOCKS") | 0 | 730 | 800 | 55 | 40 | 52 | #888888 | 2 |
| 10+ | NetData (each lock) | 0 | 790+(i*90) | 800 | 80 | 55 | 52 | color | 2 |

Lock color: `#00FF88` when value is `"LOCKED"` — but since the display builder doesn't know runtime values, use `#FFFFFF` for lock text; the locking display shows the value string itself.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_display.py
from src.display import build_info_panel

def test_returns_enter_custom_control_mode_command():
    payload = build_info_panel("http://192.168.1.243:8080", [])
    assert payload["Command"] == "Device/EnterCustomControlMode"

def test_disp_list_contains_time_element():
    payload = build_info_panel("http://192.168.1.243:8080", [])
    types = [item["Type"] for item in payload["DispList"]]
    assert "Time" in types

def test_lock_elements_added_per_entity_key():
    payload = build_info_panel("http://192.168.1.243:8080", ["front_door", "garage"])
    net_data = [i for i in payload["DispList"] if i["Type"] == "NetData"]
    lock_elements = [i for i in net_data if "locks" in i.get("Url", "")]
    assert len(lock_elements) == 2

def test_lock_rule_info_uses_entity_key():
    payload = build_info_panel("http://192.168.1.243:8080", ["front_door"])
    lock_el = next(i for i in payload["DispList"] if "locks" in i.get("Url", ""))
    assert lock_el["RuleInfo"] == "s:front_door"

def test_launch_netdata_points_to_server():
    payload = build_info_panel("http://192.168.1.243:8080", [])
    launch_els = [i for i in payload["DispList"] if "launch" in i.get("Url", "")]
    assert len(launch_els) >= 1
    assert launch_els[0]["Url"] == "http://192.168.1.243:8080/launch"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_display.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement `src/display.py`**

Build the `DispList` from the layout table above. Background: `BackgroudImageLocalFlag: 0`, `BackgroudImageAddr: ""` (no background image — device uses black). Cap lock entries at 4 (`lock_entity_keys[:4]`). Each lock NetData element: `RequestTime: 30`, `RuleInfo: f"s:{key}"`, `Url: f"{server_base_url}/locks"`. Weather element: `Url` is the Divoom weather webp from the API docs example (`https://f.divoom-gz.com/group1/M00/0C/4D/rBAAM2fZCOSEN4MoAAAAADuUrnI59.webp`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_display.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/display.py tests/test_display.py
git commit -m "feat: info panel display builder"
```

---

## Task 7: Controller

**Files:**
- Create: `src/controller.py`
- Create: `src/main_controller.py`

**Interfaces:**
- Consumes: `send_command(ip, token, payload) -> dict`, `DivoomError`, `build_info_panel(server_base_url, lock_entity_keys) -> dict`, `load_config() -> Config`
- Produces: `run(config: Config) -> None` — infinite loop, never returns normally

- [ ] **Step 1: Implement `src/controller.py`**

```python
def run(config: Config) -> None:
```

Logic:
1. On startup: attempt `ExitCustomControlMode` (ignore errors — cleans up any leftover state)
2. Build info panel payload once: `panel = build_info_panel(config.server_base_url, config.ha_lock_entities_keys)`  
   where `ha_lock_entities_keys` strips `lock.` prefix from each entity
3. Loop:
   - Try `send_command(ip, token, {"Command": "Channel/SetClockSelectId", "ClockId": 570})`; on `DivoomError` or `Exception`: log, sleep 30s, retry from top
   - `time.sleep(config.clock_duration)`
   - Try `send_command(ip, token, panel)`; on error: log, skip slide (go back to clock)
   - `time.sleep(config.slide_duration)`
   - Try `send_command(ip, token, {"Command": "Device/ExitCustomControlMode"})`; on error: log, continue

- [ ] **Step 2: Implement `src/main_controller.py`**

```python
from src.config import load_config
from src.controller import run

if __name__ == "__main__":
    run(load_config())
```

- [ ] **Step 3: Smoke test manually**

```bash
# From dev VM, verify config loads and device responds
python -c "from src.config import load_config; from src.divoom import send_command; cfg = load_config(); print(send_command(cfg.timeframe_ip, cfg.timeframe_token, {'Command': 'Channel/OnOffScreen', 'OnOff': 1}))"
```
Expected: `{'ReturnCode': 0}`

- [ ] **Step 4: Commit**

```bash
git add src/controller.py src/main_controller.py
git commit -m "feat: controller main loop with clock/info panel cycling"
```

---

## Task 8: Integration + Deployment

**Files:**
- Modify: `docker-compose.yml` (verify final form)
- Create: `.env` (on dockervm, not committed)

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: all PASS

- [ ] **Step 2: Copy project to dockervm**

```bash
rsync -av --exclude='.env' --exclude='venv' --exclude='__pycache__' \
  /home/rich/projects/active/divoom/ dockervm:/opt/divoom/
```

- [ ] **Step 3: Create `.env` on dockervm**

SSH to dockervm and create `/opt/divoom/.env` from `.env.example` with real values filled in.

- [ ] **Step 4: Build and start the stack**

```bash
ssh dockervm "cd /opt/divoom && docker compose up -d --build"
```

- [ ] **Step 5: Verify server is responding**

```bash
curl http://192.168.1.243:8080/health
curl http://192.168.1.243:8080/launch
curl http://192.168.1.243:8080/locks
```
Expected: all return valid JSON

- [ ] **Step 6: Verify device is cycling**

Watch the TimeFrame for ~70 seconds. It should show the analog clock face, then switch to the info panel for 15 seconds, then back to the clock.

- [ ] **Step 7: Verify controller logs**

```bash
ssh dockervm "docker compose -f /opt/divoom/docker-compose.yml logs controller --tail 50"
```
Expected: no errors, cycle log lines visible

- [ ] **Step 8: Commit final state**

```bash
git add .
git commit -m "feat: complete TimeFrame controller — clock/info panel cycling with weather, launches, and HA locks"
```
