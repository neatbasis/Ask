Here’s a solid, end-user-facing documentation shape you can drop into your repo (README section + API doc). I’ll write it as if your package is `ha_ask`, with `ask_question()`, `AskSpec`, `Answer`, plus the `errors.py` helpers as supported public surface.

---

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

Environment variables (recommended via `.env`):

* `HA_API_URL` – base URL of Home Assistant (e.g. `https://home.example.com`)
* `HA_API_SECRET` – Long-Lived Access Token
* `HA_SATELLITE_ENTITY_ID` *(optional)* – default satellite entity id
* `HA_NOTIFY_SERVICE` *(optional)* – notify service name (e.g. `mobile_app_sebastian_mobile`)

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
    notify_service="mobile_app_my_phone",                  # mobile only
)
```

### Parameters

* `channel`:

  * `"satellite"`: calls Home Assistant `assist_satellite.ask_question`
  * `"mobile"`: sends actionable notification and listens for response events
* `spec` (`AskSpec`): question + answers + behavior flags
* `api_url`, `token`: Home Assistant REST base URL and long-lived token
* `satellite_entity_id`: required for satellite unless you set `HA_SATELLITE_ENTITY_ID` or rely on your library default
* `notify_service`: required for mobile unless you set `HA_NOTIFY_SERVICE`

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

### Satellite

```python
from ha_ask import ask_question, AskSpec
from ha_ask.errors import is_ok

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
    notify_service=cfg["notify_service"],
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

res = ask_question(channel="mobile", spec=spec, api_url=..., token=..., notify_service=...)

print(res["id"])            # "yes" or "no"
print(res["meta"]["replies"])  # optional text replies
```

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
