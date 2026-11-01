import logging
import requests

logger = logging.getLogger(__name__)


def get_lock_states(ha_url: str, ha_token: str, entities: list[str], names: dict[str, str] | None = None) -> dict[str, str]:
    if not ha_url or not entities:
        return {}

    headers = {"Authorization": f"Bearer {ha_token}"}
    result = {}

    for entity in entities:
        try:
            resp = requests.get(
                f"{ha_url}/api/states/{entity}",
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
            state = resp.json().get("state", "unknown").upper()
            key = (names or {}).get(entity) or entity.removeprefix("lock.")
            result[key] = state
        except Exception as e:
            logger.warning("Failed to fetch lock state for %s: %s", entity, e)

    return result
