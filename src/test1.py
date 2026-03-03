from ha_ask.config import Config
from homeassistant_api import Client
from homeassistant_api.processing import Processing, process_json

Processing.register_processor("application/json", lambda r: process_json(r))
Processing.register_processor("text/html", lambda r: r.text)
Processing.register_processor("text/plain", lambda r: r.text)

cfg = Config.from_env()
url = cfg.api_url
tok = cfg.token
ent = cfg.satellite_entity_id or "assist_satellite.esphome_mycroft_assist_satellite"

answers = [
    {"id":"yes","sentences":["yeah","of course"]},
    {"id":"no","sentences":["no","nope"]},
]

with Client(url, tok) as c:
    _, data = c.trigger_service_with_response(
        "assist_satellite","ask_question",
        entity_id=ent,
        question="Say yeah/no",
        preannounce=True,
        answers=answers,
    )
    print(data)
