from ask import AskClient, AskSpec
from ask.config import Config

cfg = Config(
    ha_api_url="https://home.example.com",
    ha_api_token="YOUR_LONG_LIVED_TOKEN",
    satellite_entity_id="assist_satellite.kitchen",
)
client = AskClient(cfg)
spec = AskSpec(question="What's the magic word?", timeout_s=30)

res = client.ask_question(
    channel="satellite",
    spec=spec,
)
print(res)
