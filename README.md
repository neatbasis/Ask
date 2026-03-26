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

# Core API

## Preferred object API

```python
from ask import AskClient, AskSpec, Answer
from ask.config import Config

cfg = Config(
    ha_api_url="https://home.example.com",
    ha_api_token="YOUR_LONG_LIVED_TOKEN",
    notify_action="notify.mobile_app_my_phone",
    satellite_entity_id="assist_satellite.my_satellite",
    discord_turn_service_url="http://discord-turn.local",
)
client = AskClient(cfg)

res = client.ask_question(
    channel="satellite",
    spec=AskSpec(...),
)
```

## Compatibility function API: `ask_question(...)`

> **Compatibility API for migration only.** New code should prefer `AskClient(config)` and method calls.

```python
from ask import ask_question, AskSpec, Answer

res = ask_question(
    channel="satellite",             # "terminal" | "satellite" | "mobile" | "discord"
    spec=AskSpec(...),
    api_url="https://home.example.com",                              # Home Assistant URL
    token="YOUR_LONG_LIVED_TOKEN",
    satellite_entity_id="assist_satellite.my_satellite",   # satellite only
    notify_action="notify.mobile_app_my_phone",                    # mobile only
    discord_action="123456789012345678:234567890123456789",        # discord recipient ref
    discord_turn_service_url="http://discord-turn.local",          # DiscordTurnService URL
)
```

`ask_question(...)` and related module-level helpers (`ask_choice`, `ask_freeform`, async variants) remain available as a transitional compatibility surface. For new code, prefer `AskClient(config)` + method calls.

### Parameters

* `channel`:

  * `"terminal"`: local CLI/TTY ask flow (freeform + multichoice)
  * `"satellite"`: calls Home Assistant `assist_satellite.ask_question`
  * `"mobile"`: sends actionable notification and listens for response events
  * `"discord"`: sends prompt via Discord turn service
* `spec` (`AskSpec`): question + answers + behavior flags
* `api_url`, `token`: compatibility names for Home Assistant REST base URL and long-lived token (`api_url` is not the Discord turn service URL). Prefer configuring `ha_api_url` / `ha_api_token` on `Config` and using `AskClient`.
* `satellite_entity_id`: required for satellite unless you set `HA_SATELLITE_ENTITY_ID` or rely on your library default
* `notify_action`: Home Assistant action string used for mobile unless you set `HA_NOTIFY_ACTION`
* `discord_action`: Discord recipient reference used only for `channel="discord"`; expected format:
  * `"<user_id>"`
  * `"<user_id>:<channel_id>"`
  * `user_id` is the target Discord user snowflake and `channel_id` is an optional Discord DM channel snowflake
  * if `channel_id` is omitted, the downstream Discord turn service may resolve or create the DM channel
  * this is not a Home Assistant action string
  * compatibility behavior: if `discord_action` is omitted, dispatch currently falls back to `notify_action`; prefer setting `discord_action` explicitly
* `discord_turn_service_url`: base URL for DiscordTurnService used only for `channel="discord"` (required for Discord routing)

### Returns: `AskResult`

`AskResult` is a dict with:

* `id: Optional[str]`

  * the matched answer id (e.g. `"yes"`) or `None`
* `sentence: Optional[str]`

  * the recognized utterance (satellite) or last reply / selected label (mobile)
* `slots: Dict[str, Any]`

  * **Assist-pure**: only wildcard `{slot}` captures from sentence templates
* `meta: Dict[str, Any]`

  * transport + UI metadata (`channel`, tags, device_id, reply transcripts, raw events…)
* `error: Optional[str]`

  * `None` if successful, otherwise an error string

**Important:** `slots` is reserved for semantic slot captures only. Do not put debug metadata under `slots`.

---

# Asking styles (capability-first)

## Preferred example (object API)

```python
from ask import AskClient, AskSpec, Answer
from ask.config import Config

client = AskClient(Config.from_env())

spec = AskSpec(
    question="Proceed with the next step?",
    answers=[
        Answer("yes", ["yes", "yeah", "affirmative"], title="Yes"),
        Answer("no", ["no", "nope", "negative"], title="No"),
    ],
    allow_replies=True,
    timeout_s=120,
)

res = client.ask_question(channel="mobile", spec=spec)
print(res["id"], res["sentence"], res["slots"], res["meta"])
```

## Compatibility example (migration only)

```python
from ask import ask_question, AskSpec

res = ask_question(
    channel="satellite",
    spec=AskSpec(question="What should we do next?"),
    api_url="https://home.example.com",   # compatibility name; prefer Config.ha_api_url
    token="YOUR_LONG_LIVED_TOKEN",        # compatibility name; prefer Config.ha_api_token
)
```

## Capabilities by channel

* **terminal**
  * freeform input
  * interactive multichoice picker in TTYs, with typed fallback
  * deterministic required-slot prompting via `expected_slots`
* **satellite**
  * Home Assistant `assist_satellite.ask_question` semantics
  * speech classification + wildcard slot capture (`{album}`, `{artist}`, etc.)
  * `no_match` behavior when answers are provided but not matched
* **mobile**
  * actionable notifications (button-based classification)
  * optional text replies before completion (`allow_replies=True`)
  * reply-mode completion via “Done” when `expect_reply=True`
* **discord**
  * prompt routing via Discord turn service
  * recipient targeting via `discord_action`

## Capabilities by interaction type

* **free-form ask (`answers=None`)**
  * primary output in `sentence`
  * `id` usually `None`
* **multiple-choice classification (`answers=[...]`)**
  * stable answer id in `id`
  * normalized across channels where supported
* **slot collection (`expected_slots=[...]`)**
  * terminal stepwise collection for required fields
* **template slot capture (`"play {album} by {artist}"`)**
  * satellite wildcard capture into `slots`

## Caveats / limits

* Mobile does not perform speech-template wildcard extraction; use replies/buttons.
* `slots` is semantic-only (captured/bound values), while transport/debug data belongs in `meta`.
* `no_match` is relevant for satellite classification; mobile button flows enforce valid choices.
* Compatibility names (`api_url`, `token`) are still accepted in helper functions, but preferred naming is `ha_api_url` / `ha_api_token` on `Config`.

---

# Error handling (recommended)

Use the helper predicates from `ask`:

```python
from ask import (
    is_ok, is_match, is_no_match, is_no_response, is_timeout, is_other_error
)

res = ask_question(...)

if is_match(res):
    ...
elif is_no_match(res):
    # satellite only: answers provided but utterance didn't match any answer
    ...
elif is_no_response(res):
    # service returned no response (e.g. user never answered, HA behavior)
    ...
elif is_timeout(res):
    ...
elif is_other_error(res):
    # channel-specific or unexpected error string
    ...
```

### Known error strings

* `"no_match"`: satellite had answers but utterance didn’t match
* `"no_response"`: Home Assistant didn’t produce a response (often user didn’t answer)
* `"timeout"`: mobile listener timed out (or explicit timeout path)

Other error strings are allowed and expected as you add channel-specific failure modes.

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

Compatibility imports remain available:

```python
from ha_ask import ask_question, AskSpec, Answer
from ha_ask.errors import (
    ERR_NO_MATCH, ERR_NO_RESPONSE, ERR_TIMEOUT,
    is_ok, is_match, is_no_match, is_no_response, is_timeout, is_other_error, error_kind,
)
```

Consider everything else internal unless you explicitly document it.

---

# Best practices / conventions

* Prefer `answers` for any interaction that needs a **stable id** (classification).
* Keep `slots` semantic-only. Put debug/transport/UI data under `meta`.
* For mobile reply-mode, always set `expect_reply=True` so the notification can be dismissed via “Done”.
* For mobile choice-mode, `no_match` doesn’t apply; the UI enforces valid choices.

---

# Optional: convenience helper (recommended)

A reusable yes/no helper (consistent across channels):

```python
def ask_yes_no(*, channel: str, question: str, **kwargs):
    spec = AskSpec(
        question=question,
        answers=[
            Answer("yes", ["yes","yeah","yep","yup","sure","of course","ok","okay","alright","affirmative"], title="Yes"),
            Answer("no",  ["no","nope","nah","negative"], title="No"),
        ],
        allow_replies=True,
    )
    return ask_question(channel=channel, spec=spec, **kwargs)
```

---

If you want, I can also:

* draft a `README.md` section exactly matching your repo layout,
* or write a `docs/usage.md` plus a short `docs/api.md` (pydoc-style),
* or add a “Contract” section that explicitly mirrors the Assist Satellite documentation language (id/sentence/slots semantics) to prevent future drift.
