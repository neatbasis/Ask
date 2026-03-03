# demo-satellite-choice.py
from ha_ask import ask_question
from ha_ask.config import Config

from ha_ask.specs import yes_no_spec

cfg = Config.from_env()
spec = yes_no_spec("Proceed with the next step?", title="SemanticNG", timeout_s=10)

print(ask_question(
    channel="satellite",  # or "mobile"
    spec=spec,
    api_url=cfg.api_url,
    token=cfg.token,
    notify_service=cfg.notify_service,
    satellite_entity_id=cfg.satellite_entity_id,
))
