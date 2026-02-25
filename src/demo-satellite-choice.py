# demo-satellite-choice.py
from ha_ask import ask_question, AskSpec, Answer
from ha_ask.config import load_config

from ha_ask import ask_question
from ha_ask.specs import yes_no_spec
from ha_ask.config import load_config

cfg = load_config()
spec = yes_no_spec("Proceed with the next step?", title="SemanticNG", timeout_s=10)

print(ask_question(
    channel="satellite",  # or "mobile"
    spec=spec,
    api_url=cfg["api_url"],
    token=cfg["token"],
    notify_service=cfg.get("notify_service"),
    satellite_entity_id=cfg.get("satellite_entity_id"),
))
