## `ask` — Ask questions across Home Assistant, terminal, and Discord

`ask` provides a configured object API (`AskClient`) and compatibility helper functions (`ask_question()`, etc.) that can ask through different **channels**:

* **satellite**: uses Home Assistant’s `assist_satellite.ask_question` service (speech → classified answer + slot capture)
* **mobile**: uses actionable notifications + websocket events (buttons and/or free-form reply)
* **terminal**: local terminal interaction with freeform input + interactive multichoice picker (with typed fallback)

The return value is **Assist-compatible**: `id`, `sentence`, and `slots` follow the same semantics as `assist_satellite.ask_question`. Any transport/UI metadata is returned separately under `meta`.

`ask` is the preferred package name for new code. `ha_ask` remains supported as a compatibility import path during migration.

Compatibility imports continue to work (use only when migrating existing code):

```python
from ha_ask import AskClient, AskSpec, Answer
from ha_ask.config import Config
```

---

## Installation (runtime)

Install the project and its core runtime dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install .
```

Install directly from GitHub with pip:

```bash
python -m pip install "git+https://github.com/neatbasis/Ask.git"
```

## Installation for editing / development

For local development, install in editable mode with test dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[test,bdd]"
```

If you also want the BDD / Gherkin tooling used by the `features/` step definitions:

```bash
python -m pip install -e ".[test,bdd]"
```

## Running tests

Run the pytest suite:

```bash
pytest
```

Run type checks (optional):

```bash
mypy src tests
```

Run lint checks (optional):

```bash
ruff check src tests
```

## Demo command

Run the canonical demo flow and generate the consolidated artifact:

```bash
python -m ask.reporting > artifacts/demo_report.json
```

### Validation contract

See the canonical scenario definition in [`docs/demo_scenario.md`](docs/demo_scenario.md).

The demo validation contract is:

1. The demo must use the canonical scenario inputs and channel expectations from `docs/demo_scenario.md`.
2. The generated artifact must include the minimum contract fields: `draft_lifecycle_timeline`, `per_question_latency`, `field_evidence_provenance`, and `retry_and_churn`.
3. Users should be able to quickly inspect artifact structure with:

   ```bash
   python -m json.tool artifacts/demo_report.json
   ```

## Configuration

Primary usage is to construct `Config(...)` directly in code:

```python
from ask.config import Config

cfg = Config(
    ha_api_url="https://home.example.com",
    ha_api_token="YOUR_LONG_LIVED_TOKEN",
    notify_action="notify.mobile_app_sebastian_mobile",  # optional
    satellite_entity_id="assist_satellite.kitchen",  # optional
    discord_turn_service_url="http://discord-turn.local",  # optional, discord channel
)
```

For environment-backed deployments, use `Config.from_env()`:

```python
from ask.config import Config

cfg = Config.from_env()  # loads Home Assistant transport config
```

## Preferred API: configured `AskClient`

Use `Config` as your long-lived transport configuration and `AskClient` as your call surface:

```python
from ask import AskClient, AskSpec
from ask.config import Config

cfg = Config.from_env()
client = AskClient(cfg)

res = client.ask_question(
    channel="discord",
    spec=AskSpec(question="Deploy now?"),
    discord_action="123456789012345678",  # Discord recipient reference
)
```

The client defaults come from `Config`:

* `ha_api_url` (preferred; legacy `api_url` is still accepted)
* `ha_api_token` (preferred; legacy `token` is still accepted)
* `notify_action`
* `satellite_entity_id`
* `discord_turn_service_url`

You can still override any of those per call when needed.

### Environment variable reference (single source of truth)

Required:

* `HA_API_URL` – base URL of Home Assistant (e.g. `https://home.example.com`)
* `HA_API_TOKEN` – preferred env var for Home Assistant long-lived access token
* `HA_API_SECRET` – legacy alias still supported for compatibility

Optional:

* `HA_NOTIFY_ACTION` – full Home Assistant action string (e.g. `notify.mobile_app_sebastian_mobile`)
* `HA_SATELLITE_ENTITY_ID` – default satellite entity id
* `DISCORD_TURN_SERVICE_URL` – base URL for Discord turn service (`channel="discord"`)

### Migration note

* Old: `load_config()` with dotenv side effects
* New: explicit `Config` construction / `Config.from_env()`

```python
# Before
from ha_ask.config import load_config

cfg = load_config()  # deprecated compatibility API

# After
from ask.config import Config

cfg = Config(
    ha_api_url="https://home.example.com",
    ha_api_token="YOUR_LONG_LIVED_TOKEN",
)
# or, for env-backed deployments:
# cfg = Config.from_env()
```

`load_config()` remains available as a deprecated compatibility wrapper. Prefer `Config(...)` for explicit configuration, or `Config.from_env()` when reading Home Assistant transport settings from environment variables.

## Demonstrate artifact generation (canonical demo)

This is the fastest way to generate the canonical demo artifact described in `docs/demo_scenario.md`.

### Prerequisites

If you are using environment-backed config (`Config.from_env()`), set:

- `HA_API_URL`
- `HA_API_TOKEN` (preferred; `HA_API_SECRET` is still accepted)
- `HA_NOTIFY_ACTION`

### Run this exact command

```bash
python -m ask.canonical_demo --output artifacts/demo_report.json
```

### Success looks like

You should see a confirmation line such as:

```text
Wrote canonical demo artifact to artifacts/demo_report.json
```

The artifact file is written to:

- `artifacts/demo_report.json`

Open the JSON and verify key contract fields exist, for example:

- `draft_lifecycle_timeline`
- `per_question_latency`

### Troubleshooting

- **Missing env vars**: export `HA_API_URL`, `HA_API_TOKEN` (or legacy `HA_API_SECRET`), and (for mobile demos) `HA_NOTIFY_ACTION` before running demos that call Home Assistant.
- **Auth/token issues**: regenerate the long-lived token and re-export `HA_API_TOKEN` (or legacy `HA_API_SECRET`) if Home Assistant returns 401/403.
- **Notify service failures**: verify `HA_NOTIFY_ACTION` is a full Home Assistant action string such as `notify.mobile_app_sebastian_mobile`.

---

# Identity and migration

Preferred public surface for new code:

* package: `ask`
* configured object API: `AskClient`
* config model: `Config` with `ha_api_url` / `ha_api_token`

Compatibility surfaces remain available for migration:

* package import path: `ha_ask`
* module-level helper functions: `ask_question(...)`, `ask_choice(...)`, `ask_freeform(...)` (and async variants)
* legacy config aliases: `api_url` / `token`

Use compatibility surfaces to migrate existing code. For new code, prefer `ask` + `Config` + `AskClient`. Compatibility surfaces may be further de-emphasized in future releases.

## Preferred object API (primary)

```python
from ask import AskClient, AskSpec, Answer
from ask.config import Config

cfg = Config(
    ha_api_url="https://home.example.com",
    ha_api_token="YOUR_LONG_LIVED_TOKEN",
    notify_action="notify.mobile_app_my_phone",           # mobile default
    satellite_entity_id="assist_satellite.my_satellite",  # satellite default
    discord_turn_service_url="http://discord-turn.local", # required for discord channel
)
client = AskClient(cfg)

res = client.ask_question(
    channel="satellite",  # "terminal" | "satellite" | "mobile" | "discord"
    spec=AskSpec(
        question="Proceed with the next step?",
        answers=[
            Answer("yes", ["yes", "affirmative"], title="Yes"),
            Answer("no", ["no", "negative"], title="No"),
        ],
    ),
)
```

## Compatibility function API (transitional)

Compatibility helper APIs are still supported for migration, but they are not the preferred teaching path for new code.

```python
from ask import ask_question, AskSpec

res = ask_question(
    channel="satellite",
    spec=AskSpec(question="Proceed?"),
    api_url="https://home.example.com",   # compatibility alias; prefer Config(ha_api_url=...)
    token="YOUR_LONG_LIVED_TOKEN",        # compatibility alias; prefer Config(ha_api_token=...)
)
```

---

# Configuration

Put long-lived transport settings in `Config`.

Preferred names:

* `ha_api_url`
* `ha_api_token`

Channel-specific settings:

* `notify_action` (mobile)
* `satellite_entity_id` (satellite)
* `discord_turn_service_url` (discord)

```python
from ask.config import Config

cfg = Config.from_env()
# Uses HA_API_URL + HA_API_TOKEN (legacy HA_API_SECRET still accepted)
```

Legacy names (`api_url`, `token`) and compatibility loaders remain supported during migration, but new code should prefer explicit `Config(...)` or `Config.from_env()` with preferred names.

---

# Capabilities by channel

## Terminal

* freeform question/answer
* multiple-choice classification with stable answer IDs
* interactive picker in suitable TTYs
* deterministic typed fallback matching (index/id/title/aliases)
* deterministic required-slot collection (`expected_slots`)
* template-aware response rendering fallback when template metadata is available

## Satellite

* Assist-native answer matching
* wildcard slot capture from sentence templates (`{slot}`)
* strongest template semantics

## Mobile

* actionable button choices
* reply mode (`expect_reply=True`) with collected text replies
* no speech-template slot capture

## Discord

* DiscordTurnService-backed turn handling
* recipient reference via `discord_action` (`<user_id>` or `<user_id>:<channel_id>`)
* requires `discord_turn_service_url`
* `discord_action` is a Discord recipient reference, not a Home Assistant action string

---

# Capabilities by interaction type

## Freeform

Open-text response flow (`answers=None`) across terminal/satellite/mobile/discord channels.

## Choice

Use `answers=[Answer(...)]` when you need stable answer IDs (for example `"yes"` / `"no"`) across channels.

## Slot collection

Deterministic required-slot prompting is available in terminal via `expected_slots=[...]`.

## Template capture

* strongest on satellite via wildcard capture in sentence templates
* terminal can apply deterministic/template-aware fallback rendering when metadata is available
* mobile/discord do not provide Assist speech-template wildcard capture semantics

---

# Caveats and limits

* Mobile does not perform Assist speech-template wildcard slot capture.
* Terminal behavior is deterministic and template-aware where metadata exists; it is not full natural-language Assist template parsing.
* Discord asks depend on a reachable DiscordTurnService and configured `discord_turn_service_url`.
* Compatibility surfaces (`ha_ask`, module-level helpers, legacy config names) remain supported for migration, but are not preferred for new code.

---

# Error handling (recommended)

Use helper predicates from the preferred `ask` surface:

```python
from ask import (
    is_match, is_no_match, is_no_response, is_timeout, is_other_error
)
```

Known error strings include:

* `"no_match"`
* `"no_response"`
* `"timeout"`

Other channel-specific error strings may appear.

---

# Public API surface (what end users should rely on)

Stable public imports (preferred):

```python
from ask import ask_question, AskSpec, Answer
from ask import (
    ERR_NO_MATCH, ERR_NO_RESPONSE, ERR_TIMEOUT,
    is_ok, is_match, is_no_match, is_no_response, is_timeout, is_other_error, error_kind,
)
```

Compatibility imports remain available for migration:

```python
from ha_ask import ask_question, AskSpec, Answer
from ha_ask.errors import (
    ERR_NO_MATCH, ERR_NO_RESPONSE, ERR_TIMEOUT,
    is_ok, is_match, is_no_match, is_no_response, is_timeout, is_other_error, error_kind,
)
```

Consider everything else internal unless explicitly documented.
