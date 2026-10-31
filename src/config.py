import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    timeframe_ip: str
    timeframe_token: int
    server_host: str
    server_port: int
    server_base_url: str
    clock_duration: int
    slide_duration: int
    ha_url: str
    ha_token: str
    ha_lock_entities: list[str]
    launch_location_id: int
    weather_location: str


def load_config() -> Config:
    entities_raw = os.getenv("HA_LOCK_ENTITIES", "")
    entities = [e.strip() for e in entities_raw.split(",") if e.strip()]
    return Config(
        timeframe_ip=os.getenv("TIMEFRAME_IP", "192.168.1.25"),
        timeframe_token=int(os.getenv("TIMEFRAME_TOKEN", "639954")),
        server_host=os.getenv("SERVER_HOST", "0.0.0.0"),
        server_port=int(os.getenv("SERVER_PORT", "8080")),
        server_base_url=os.getenv("SERVER_BASE_URL", "http://192.168.1.243:8080"),
        clock_duration=int(os.getenv("CLOCK_DURATION", "50")),
        slide_duration=int(os.getenv("SLIDE_DURATION", "15")),
        ha_url=os.getenv("HA_URL", ""),
        ha_token=os.getenv("HA_TOKEN", ""),
        ha_lock_entities=entities,
        launch_location_id=int(os.getenv("LAUNCH_LOCATION_ID", "12")),
        weather_location=os.getenv("WEATHER_LOCATION", "Oviedo,FL"),
    )
