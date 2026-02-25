import os
from dotenv import load_dotenv

def load_config() -> dict:
    load_dotenv()
    api_url = os.environ.get("HA_API_URL")
    token = os.environ.get("HA_API_SECRET")
    notify_service = os.environ.get("HA_NOTIFY_SERVICE")  # optional
    satellite_entity_id = os.environ.get("HA_SATELLITE_ENTITY_ID")  # optional

    return {
        "api_url": api_url,
        "token": token,
        "notify_service": notify_service,
        "satellite_entity_id": satellite_entity_id,
    }

def normalize_rest_api_url(url: str) -> str:
    url = url.rstrip("/")
    if not url.endswith("/api"):
        url += "/api"
    return url + "/"

def derive_ws_url(rest_api_url: str) -> str:
    rest = normalize_rest_api_url(rest_api_url)
    if rest.startswith("https://"):
        ws_base = "wss://" + rest[len("https://"):]
    elif rest.startswith("http://"):
        ws_base = "ws://" + rest[len("http://"):]
    else:
        ws_base = "ws://" + rest
    return ws_base.rstrip("/") + "/websocket"
