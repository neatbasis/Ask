# demo-satellite-choice.py
from ask import AskClient
from ask.config import Config

from ask.specs import yes_no_spec

cfg = Config(
    ha_api_url="https://home.example.com",
    ha_api_token="YOUR_LONG_LIVED_TOKEN",
    satellite_entity_id="assist_satellite.kitchen",
)
client = AskClient(cfg)
spec = yes_no_spec("Proceed with the next step?", title="SemanticNG", timeout_s=10)

print(client.ask_question(
    channel="satellite",  # or "mobile"
    spec=spec,
))
