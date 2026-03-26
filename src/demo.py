from ask import AskClient, AskSpec
from ask.config import Config

cfg = Config.from_env()
client = AskClient(cfg)
spec = AskSpec(question="What's the magic word?", timeout_s=30)

res = client.ask_question(
    channel="satellite",
    spec=spec,
)
print(res)
