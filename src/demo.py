from ha_ask import ask_question, AskSpec
from ha_ask.config import Config

cfg = Config.from_env()
spec = AskSpec(question="What's the magic word?", timeout_s=30)

res = ask_question(
    channel="satellite",
    spec=spec,
    api_url=cfg.api_url,
    token=cfg.token,
    satellite_entity_id=cfg.satellite_entity_id,
)
print(res)
