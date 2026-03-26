"""Local satellite-choice example script (not the supported demo path).

This script is runnable when Home Assistant environment variables are set.
The supported repository demo flow is:
    python -m ask.demo --output artifacts/demo_report.json
"""

from ask import AskClient
from ask.config import Config

from ask.specs import yes_no_spec

cfg = Config.from_env()
client = AskClient(cfg)
spec = yes_no_spec("Proceed with the next step?", title="SemanticNG", timeout_s=10)

print(client.ask_question(
    channel="satellite",  # or "mobile"
    spec=spec,
))
