import requests


class DivoomError(Exception):
    def __init__(self, message: str, return_code: int):
        super().__init__(message)
        self.return_code = return_code


def send_command(ip: str, token: int, payload: dict) -> dict:
    url = f"http://{ip}:9000/divoom_api"
    response = requests.get(url, json=payload, timeout=10)
    data = response.json()
    if data.get("ReturnCode", 0) != 0:
        msg = data.get("ReturnMessage", "Device returned error")
        raise DivoomError(msg, data["ReturnCode"])
    return data
