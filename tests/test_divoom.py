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
