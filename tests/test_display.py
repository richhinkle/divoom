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
