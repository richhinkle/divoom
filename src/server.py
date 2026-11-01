from fastapi import FastAPI

from src.config import load_config
from src.launches import get_next_launch
from src.locks import get_lock_states

app = FastAPI()
_config = load_config()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/launch")
def launch():
    return get_next_launch()


@app.get("/locks")
def locks():
    return get_lock_states(_config.ha_url, _config.ha_token, _config.ha_lock_entities, _config.ha_lock_names)
