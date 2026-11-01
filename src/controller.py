import logging
import time

from src.config import Config
from src.display import build_info_panel
from src.divoom import DivoomError, send_command

logger = logging.getLogger(__name__)


def run(config: Config) -> None:
    ip = config.timeframe_ip
    token = config.timeframe_token

    lock_keys = [e.removeprefix("lock.") for e in config.ha_lock_entities]
    panel = build_info_panel(config.server_base_url, lock_keys)

    # Clean up any leftover custom mode from a previous crash
    try:
        send_command(ip, token, {"Command": "Device/ExitCustomControlMode"})
    except Exception:
        pass

    while True:
        # Show analog clock
        try:
            send_command(ip, token, {"Command": "Channel/SetClockSelectId", "ClockId": 231})
        except Exception as e:
            logger.error("Failed to set clock: %s — retrying in 30s", e)
            time.sleep(30)
            continue

        time.sleep(config.clock_duration)

        # Show info panel
        try:
            send_command(ip, token, panel)
        except Exception as e:
            logger.warning("Failed to show info panel: %s — skipping slide", e)
            continue

        time.sleep(config.slide_duration)

        # Return to clock
        try:
            send_command(ip, token, {"Command": "Device/ExitCustomControlMode"})
        except Exception as e:
            logger.warning("Failed to exit custom mode: %s", e)
