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
