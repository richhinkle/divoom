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
