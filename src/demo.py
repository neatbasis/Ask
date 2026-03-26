"""Local satellite example script (not the supported demo path).

This script is runnable when Home Assistant environment variables are set.
The supported repository demo flow is:
    python -m ask.demo --output artifacts/demo_report.json
"""

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
