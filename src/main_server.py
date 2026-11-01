import uvicorn
from src.config import load_config
from src.server import app

if __name__ == "__main__":
    cfg = load_config()
    uvicorn.run(app, host=cfg.server_host, port=cfg.server_port)
