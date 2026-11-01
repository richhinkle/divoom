from unittest.mock import patch, Mock
import pytest
import src.launches as launches_module
from src.launches import get_next_launch

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
