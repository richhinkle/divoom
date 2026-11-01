_WEATHER_WEBP = "https://f.divoom-gz.com/group1/M00/0C/4D/rBAAM2fZCOSEN4MoAAAAADuUrnI59.webp"


def build_info_panel(server_base_url: str, lock_entity_keys: list[str]) -> dict:
    disp_list = [
        {
            "ID": 1, "Type": "Time",
            "StartX": 0, "StartY": 80, "Width": 800, "Height": 200,
            "Align": 2, "FontSize": 150, "FontID": 52, "FontColor": "#FFFFFF", "BgColor": "#111111",
        },
        {
            "ID": 2, "Type": "Date",
            "StartX": 0, "StartY": 290, "Width": 800, "Height": 70,
            "Align": 2, "FontSize": 50, "FontID": 52, "FontColor": "#AAAAAA", "BgColor": "#111111",
        },
        {
            "ID": 3, "Type": "Temperature",
            "StartX": 0, "StartY": 380, "Width": 400, "Height": 60,
            "Align": 2, "FontSize": 45, "FontID": 52, "FontColor": "#FFD700", "BgColor": "#111111",
        },
        {
            "ID": 4, "Type": "Weather",
            "StartX": 400, "StartY": 375, "Width": 64, "Height": 64,
            "Align": 2, "FontSize": 45, "FontID": 52, "FontColor": "#FFFFFF", "BgColor": "#111111",
            "Url": _WEATHER_WEBP,
        },
        {
            "ID": 5, "Type": "NetData",
            "StartX": 20, "StartY": 520, "Width": 760, "Height": 70,
            "Align": 2, "FontSize": 45, "FontID": 52, "FontColor": "#00BFFF", "BgColor": "#111111",
            "Url": f"{server_base_url}/launch",
            "RuleInfo": "s:name",
            "RequestTime": 300,
        },
        {
            "ID": 6, "Type": "NetData",
            "StartX": 20, "StartY": 600, "Width": 760, "Height": 60,
            "Align": 2, "FontSize": 40, "FontID": 52, "FontColor": "#87CEEB", "BgColor": "#111111",
            "Url": f"{server_base_url}/launch",
            "RuleInfo": "s:net",
            "RequestTime": 300,
        },
        {
            "ID": 7, "Type": "Text",
            "StartX": 0, "StartY": 730, "Width": 800, "Height": 55,
            "Align": 2, "FontSize": 40, "FontID": 52, "FontColor": "#888888", "BgColor": "#111111",
            "TextMessage": "DOOR LOCKS",
        },
    ]

    for i, key in enumerate(lock_entity_keys[:4]):
        disp_list.append({
            "ID": 10 + i, "Type": "NetData",
            "StartX": 0, "StartY": 790 + i * 90, "Width": 800, "Height": 80,
            "Align": 2, "FontSize": 55, "FontID": 52, "FontColor": "#FFFFFF", "BgColor": "#111111",
            "Url": f"{server_base_url}/locks",
            "RuleInfo": f"s:{key}",
            "RequestTime": 30,
        })

    return {
        "Command": "Device/EnterCustomControlMode",
        "BackgroudImageLocalFlag": 0,
        "BackgroudImageAddr": "",
        "DispList": disp_list,
    }
