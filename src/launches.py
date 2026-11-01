import logging
import time
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo

import requests

logger = logging.getLogger(__name__)

_cache: dict | None = None
_cache_time: float = 0
_CACHE_TTL = 300  # 5 minutes
_EASTERN = ZoneInfo("America/New_York")
_FALLBACK = {"name": "No launches scheduled", "net": "", "days": -1}
_LOCATION_ID = 12


def get_next_launch() -> dict:
    global _cache, _cache_time
    if _cache is not None and time.time() - _cache_time < _CACHE_TTL:
        return _cache

    try:
        url = (
            f"https://ll2.thespacedevs.com/2.3.0/launches/upcoming/"
            f"?location__ids={_LOCATION_ID}&limit=1&format=json"
        )
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            _cache = _FALLBACK
            _cache_time = time.time()
            return _cache

        launch = results[0]
        name = launch["name"][:35]
        net_str = launch.get("net", "")
        net_dt = datetime.fromisoformat(net_str.replace("Z", "+00:00")).astimezone(_EASTERN)
        net_formatted = net_dt.strftime("%b %-d, %-I:%M %p ET")
        days = (net_dt.date() - date.today()).days

        _cache = {"name": name, "net": net_formatted, "days": days}
        _cache_time = time.time()
        return _cache

    except Exception as e:
        logger.warning("Failed to fetch launches: %s", e)
        return _FALLBACK
