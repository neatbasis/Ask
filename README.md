## `ha_ask` — Ask questions via Home Assistant (Satellite + Mobile)

`ha_ask` provides a single `ask_question()` function that can ask a question through different **channels**:

* **satellite**: uses Home Assistant’s `assist_satellite.ask_question` service (speech → classified answer + slot capture)
* **mobile**: uses actionable notifications + websocket events (buttons and/or free-form reply)

The return value is **Assist-compatible**: `id`, `sentence`, and `slots` follow the same semantics as `assist_satellite.ask_question`. Any transport/UI metadata is returned separately under `meta`.

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
python -m ha_ask.reporting > artifacts/demo_report.json
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
from ha_ask.config import Config

cfg = Config(
    api_url="https://home.example.com",
    token="YOUR_LONG_LIVED_TOKEN",
    notify_action="notify.mobile_app_sebastian_mobile",  # optional
    satellite_entity_id="assist_satellite.kitchen",  # optional
)
```

For environment-backed deployments, use `Config.from_env()`:

```python
from ha_ask.config import Config

cfg = Config.from_env()
```

### Environment variable reference (single source of truth)

Required:

* `HA_API_URL` – base URL of Home Assistant (e.g. `https://home.example.com`)
* `HA_API_SECRET` – Long-Lived Access Token

Optional:

* `HA_NOTIFY_ACTION` – full Home Assistant action string (e.g. `notify.mobile_app_sebastian_mobile`)
* `HA_SATELLITE_ENTITY_ID` – default satellite entity id

### Migration note

* Old: `load_config()` with dotenv side effects
* New: explicit `Config` construction / `Config.from_env()`

```python
# Before
from ha_ask.config import load_config

cfg = load_config()  # deprecated compatibility API

# After
from ha_ask.config import Config

cfg = Config(
    api_url="https://home.example.com",
    token="YOUR_LONG_LIVED_TOKEN",
)
# or, for env-backed deployments:
# cfg = Config.from_env()
```

`load_config()` remains available as a deprecated compatibility wrapper. Prefer `Config(...)` for explicit configuration, or `Config.from_env()` when reading from environment variables.

## Demonstrate artifact generation (canonical demo)

This is the fastest way to generate the canonical demo artifact described in `docs/demo_scenario.md`.

### Prerequisites

If you are using environment-backed config (`Config.from_env()`), set:

- `HA_API_URL`
- `HA_API_SECRET`
- `HA_NOTIFY_ACTION`

### Run this exact command

```bash
python -m ha_ask.canonical_demo --output artifacts/demo_report.json
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

- **Missing env vars**: export `HA_API_URL`, `HA_API_SECRET`, and (for mobile demos) `HA_NOTIFY_ACTION` before running demos that call Home Assistant.
- **Auth/token issues**: regenerate the long-lived token and re-export `HA_API_SECRET` if Home Assistant returns 401/403.
- **Notify service failures**: verify `HA_NOTIFY_ACTION` is a full Home Assistant action string such as `notify.mobile_app_sebastian_mobile`.

---

# Core API

## `ask_question(...)`

```python
from ha_ask import ask_question, AskSpec, Answer

res = ask_question(
    channel="satellite",             # "satellite" | "mobile"
    spec=AskSpec(...),
    api_url="https://home.example.com",
    token="YOUR_LONG_LIVED_TOKEN",
    satellite_entity_id="assist_satellite.my_satellite",   # satellite only
    notify_action="notify.mobile_app_my_phone",                  # mobile only
)
```

### Parameters

* `channel`:

  * `"satellite"`: calls Home Assistant `assist_satellite.ask_question`
  * `"mobile"`: sends actionable notification and listens for response events
* `spec` (`AskSpec`): question + answers + behavior flags
* `api_url`, `token`: Home Assistant REST base URL and long-lived token
* `satellite_entity_id`: required for satellite unless you set `HA_SATELLITE_ENTITY_ID` or rely on your library default
* `notify_action`: required for mobile unless you set `HA_NOTIFY_ACTION`

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

# Asking styles

## 1) Free-form question (no answers)

### Terminal

```python
from ha_ask import ask_question, AskSpec
from ha_ask.errors import is_ok, is_cancelled

spec = AskSpec(question="What should we do next?")
res = ask_question(channel="terminal", spec=spec)

if is_ok(res):
    print("Typed text:", res["sentence"])
elif is_cancelled(res):
    print("User cancelled from terminal (Esc/esc/escape or Ctrl+C).")
```

### Satellite

```python
from ha_ask import ask_question, AskSpec
from ha_ask.errors import is_ok
from ha_ask.config import Config

cfg = Config.from_env().to_dict()  # or build Config(...) explicitly and call to_dict()

spec = AskSpec(question="What should we do next?", answers=None, timeout_s=30)

res = ask_question(
    channel="satellite",
    spec=spec,
    api_url=cfg["api_url"],
    token=cfg["token"],
    satellite_entity_id=cfg["satellite_entity_id"],
)

if is_ok(res):
    print("User said:", res["sentence"])   # id is typically None
```

### Mobile (reply-mode)

Mobile needs a terminal “Done” action, so set `expect_reply=True`.

```python
from ha_ask import ask_question, AskSpec
from ha_ask.errors import is_ok
from ha_ask.config import Config

cfg = Config.from_env().to_dict()  # or build Config(...) explicitly and call to_dict()

spec = AskSpec(
    question="Tell me what you want next. Reply then press Done.",
    answers=None,
    expect_reply=True,
    allow_replies=True,
    timeout_s=120,
    title="SemanticNG",
)

res = ask_question(
    channel="mobile",
    spec=spec,
    api_url=cfg["api_url"],
    token=cfg["token"],
    notify_action=cfg["notify_action"],
)

if is_ok(res):
    print("Last reply:", res["sentence"])
    print("All replies:", res["meta"].get("replies", []))
```

Behavior:

* user may send 0..N replies
* “Done” ends the interaction
* if no replies were sent, `sentence == ""` and `meta["replies"] == []`

---

## 2) Multiple-choice classification (answers)

This is the closest match to Assist Satellite’s native behavior.

### Defining answers

```python
from ha_ask import Answer

answers = [
    Answer("yes", ["yes", "yeah", "yep", "sure", "of course"], title="Yes"),
    Answer("no",  ["no", "nope", "nah", "negative"],          title="No"),
]
```

### Satellite (Assist-native)

```python
spec = AskSpec(
    question="Proceed with the next step?",
    answers=answers,
    timeout_s=60,
)

res = ask_question(channel="satellite", spec=spec, api_url=..., token=..., satellite_entity_id=...)

print(res["id"])       # "yes" or "no" or None (if no match)
print(res["sentence"]) # recognized utterance
print(res["slots"])    # wildcard slots (if templates used)
```

### Terminal (typed selection)

Terminal now supports typed multiple-choice turns as a first-class ask path.
When `answers` are supplied, Ask renders options and retries until the input resolves
to a valid choice or cancellation.

Supported typed selection forms:

* option number (`1`, `2`, ...)
* answer id/key (`yes`, `no`, ...)
* answer label/title (`Yes`, `No thanks`, ...)
* answer sentence aliases (`affirmative`, `negative`, ...)

```python
from ha_ask import ask_question, AskSpec, Answer
from ha_ask.errors import is_ok

spec = AskSpec(
    question="Proceed with the next step?",
    answers=[
        Answer("yes", ["yes", "affirmative"], title="Yes", slot_bindings={"proceed": True}),
        Answer("no", ["no", "negative"], title="No", slot_bindings={"proceed": False}),
    ],
)

res = ask_question(channel="terminal", spec=spec)

if is_ok(res):
    print(res["id"])       # canonical answer id ("yes"/"no")
    print(res["sentence"]) # user typed input used for the selection
    print(res["slots"])    # copied from selected answer.slot_bindings
```

### Mobile (buttons)

On mobile, the user can only pick from the buttons you provide, so you won’t get `no_match` there.

```python
spec = AskSpec(
    question="Proceed with the next step?",
    answers=answers,
    allow_replies=True,   # allow textInput replies before choosing
    timeout_s=300,
    title="SemanticNG",
)

res = ask_question(channel="mobile", spec=spec, api_url=..., token=..., notify_action=...)

print(res["id"])            # "yes" or "no"
print(res["meta"]["replies"])  # optional text replies
```

---

## Terminal-first delivery note

This repository now includes terminal turn handling (freeform + typed multichoice)
as the immediate feature delivery. The richer `interaction_contracts` seam work
already landed separately in `DiscordTurnService` (commit
`8ae1443dcf09f25b82c303d253076f2e1e52a24d`), but Ask has not yet taken the broader
follow-up PR to consume that richer interaction model everywhere.

---

## 3) Slot capture (Satellite only)

Assist Satellite sentence templates can contain wildcards `{slots}`:

```python
answers = [
    Answer("play_album", ["play {album} by {artist}"], title="Play album"),
]
spec = AskSpec(question="What should I play?", answers=answers, timeout_s=60)

res = ask_question(channel="satellite", spec=spec, api_url=..., token=..., satellite_entity_id=...)

if res["id"] == "play_album":
    print("Album:", res["slots"].get("album"))
    print("Artist:", res["slots"].get("artist"))
```

Mobile cannot do speech-template slot capture; it only provides replies/buttons.

---

# Error handling (recommended)

Use the helper predicates from `ha_ask.errors`:

```python
from ha_ask.errors import (
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

Stable public imports:

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
