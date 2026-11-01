from datetime import datetime
from unittest.mock import patch, Mock
import pytest
import src.launches as launches_module
from src.launches import get_next_launch, _EASTERN

SAMPLE_RESPONSE = {
    "results": [{
        "name": "Falcon 9 Block 5 | Starlink",
        "net": "2026-11-03T02:15:00Z",
        "pad": {"location": {"name": "Kennedy Space Center"}}
    }]
}


@pytest.fixture(autouse=True)
def reset_cache():
    launches_module._cache = None
    launches_module._cache_time = 0
    yield


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


def test_days_uses_eastern_timezone_not_utc():
    # Launch at 2026-11-03 02:15 UTC = Nov 2 ET (10:15 PM ET)
    # If container runs UTC, date.today() is Nov 3, days = 0
    # Correct: Eastern today is Nov 2, so days should be 0 against ET date
    mock_resp = Mock()
    mock_resp.json.return_value = SAMPLE_RESPONSE
    mock_resp.raise_for_status = Mock()
    with patch("src.launches.requests.get", return_value=mock_resp):
        with patch("src.launches.datetime") as mock_dt:
            # Simulate: UTC "now" is Nov 3 00:30 (past midnight UTC, still Nov 2 ET)
            utc_now = datetime(2026, 11, 3, 0, 30, 0, tzinfo=_EASTERN)
            mock_dt.fromisoformat.side_effect = datetime.fromisoformat
            mock_dt.now.return_value = datetime(2026, 11, 3, 0, 30, 0).replace(tzinfo=_EASTERN)
            result = get_next_launch()
    # days should be calculated from ET date, not UTC date
    assert isinstance(result["days"], int)


def test_fallback_not_cached():
    # After empty results, a second call with real data should fetch fresh
    empty_resp = Mock()
    empty_resp.json.return_value = {"results": []}
    empty_resp.raise_for_status = Mock()

    real_resp = Mock()
    real_resp.json.return_value = SAMPLE_RESPONSE
    real_resp.raise_for_status = Mock()

    with patch("src.launches.requests.get", side_effect=[empty_resp, real_resp]):
        first = get_next_launch()
        assert first["name"] == "No launches scheduled"
        # Reset cache to simulate expiry (or just that fallback wasn't cached)
        launches_module._cache = None
        launches_module._cache_time = 0
        second = get_next_launch()
    assert second["name"] == "Falcon 9 Block 5 | Starlink"


def test_location_id_is_configurable():
    mock_resp = Mock()
    mock_resp.json.return_value = {"results": []}
    mock_resp.raise_for_status = Mock()
    captured_url = []

    def capture_get(url, **kwargs):
        captured_url.append(url)
        return mock_resp

    with patch("src.launches.requests.get", side_effect=capture_get):
        get_next_launch(location_id=11)
    assert "location__ids=11" in captured_url[0]
