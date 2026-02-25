from typing import Literal, Optional
from homeassistant_api import Client, WebsocketClient

from .types import AskSpec, AskResult
from .config import normalize_rest_api_url, derive_ws_url
from .channels import satellite as satellite_chan
from .channels import mobile as mobile_chan

Channel = Literal["satellite", "mobile"]

def ask_question(
    *,
    channel: Channel,
    spec: AskSpec,
    api_url: str,
    token: str,
    notify_service: Optional[str] = None,
    satellite_entity_id: Optional[str] = None,
) -> AskResult:
    rest = normalize_rest_api_url(api_url)

    if channel == "satellite":
        with Client(rest, token) as client:
            return satellite_chan.ask_question(client, spec, entity_id=satellite_entity_id)

    if channel == "mobile":
        if not notify_service:
            return {"id": None, "sentence": None, "slots": {}, "error": "missing_notify_service"}
        ws_url = derive_ws_url(api_url)
        with Client(rest, token) as client, WebsocketClient(ws_url, token) as ws:
            return mobile_chan.ask_question(client, ws, spec, notify_service=notify_service)

    return {"id": None, "sentence": None, "slots": {}, "error": f"unknown_channel:{channel}"}
