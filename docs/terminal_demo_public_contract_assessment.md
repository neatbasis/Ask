# Ask model-family and channel-presentation assessment

## A) Executive conclusion

**Verdict: Mostly yes (with a clear transitional seam).**

The terminal demo is canonical at the public API boundary: it builds asks with `AskClient` + `AskSpec` + `Answer` from `ask` and dispatches through normal channel routing, not a private demo path. `InteractionSpec` is not part of the canonical public import surface, but it is a central internal semantic layer used by terminal to interpret public asks. Sentence/template semantics are **partially public** today: public callers can provide sentence patterns via `Answer.sentences`, but richer template objects and template-driven rendering are internal and mostly exercised via internal seams/tests. Channel UX is intentionally not uniform: satellite delegates to Assist speech semantics, terminal is local typed/interactive, mobile is actionable notifications + websocket events, and Discord is turn-service driven text interaction. All channels normalize back to canonical `AskResult` shape, but they differ materially in how asks are presented and completed.

## B) Model family map

### Public contract models

| Model | Defined in | Public status | Role | Relationships |
|---|---|---|---|---|
| `AskSpec` | `src/ask/types.py` | Public canonical | General ask input contract (`question`, optional `answers`, optional `expected_slots`, mobile flags). | Base input model used by dispatch and all channels. |
| `ChoiceSpec` | `src/ask/types.py` | Public canonical | Choice-focused specialization of `AskSpec` with required `answers`. | Maps to internal choice interaction via `choice_spec_to_interaction`. |
| `FreeformSpec` | `src/ask/types.py` | Public canonical | Freeform specialization of `AskSpec` with reply defaults. | Maps to internal freeform interaction via `freeform_spec_to_interaction`. |
| `Answer` | `src/ask/types.py` | Public canonical | Choice option (`id`, `sentences`, optional `title`, optional `slot_bindings`). | Used in `AskSpec.answers`; influences choice UX and slot bindings. |
| `AskResult` | `src/ask/types.py` and exported from `src/ask/__init__.py` | Public canonical | Unified result contract (`id`, `sentence`, `slots`, `meta`, `error`). | Output of `dispatch.ask_question` and channel adapters. |

### Internal semantic models

| Model | Defined in | Public status | Role | Relationships |
|---|---|---|---|---|
| `InteractionSpec` | `src/ask/interaction_types.py` | Internal (not exported at `ask` root) | Rich internal interaction target (`mode`, `slots`, `choices`, `templates`). | Produced from `AskSpec` family by mapping functions. |
| `InteractionMode` | `src/ask/interaction_types.py` | Internal | Internal mode enum (`FREEFORM`, `CHOICE`, `TEMPLATE_FILL`, `MIXED`). | Drives terminal adapter branching. |
| `SlotSpec` | `src/ask/interaction_types.py` | Internal | Internal representation of required/optional slot collection fields. | Derived from `AskSpec.expected_slots`. |
| `AnswerTemplate` | `src/ask/interaction_types.py` | Internal | Internal sentence-template object (`sentences`, `slot_bindings`, etc.). | Consumed by terminal template hint/render helpers. |

### Translation boundary (`AskSpec` -> `InteractionSpec`)

- Translation occurs in `ask_spec_to_interaction`, with specialized paths for `ChoiceSpec` and `FreeformSpec`; otherwise conservative mapping by presence/absence of `answers`.
- Terminal adapter calls this mapping at ask time and then executes behavior by `InteractionMode`, slots, choices, and templates.
- This boundary appears **intentional and transitional**: comments explicitly describe an “additive seam” preserving public compatibility while introducing richer internal semantics.

## C) Channel presentation matrix

| Channel | Presentation to user | How answers are collected | Choice support | Freeform support | Slot collection | Template/sentence behavior | Result shape |
|---|---|---|---|---|---|---|---|
| `terminal` | CLI prompt; optional prompt-toolkit radiolist for choices; typed fallback. | `input()` / interactive selector; cancel via `esc` tokens or Ctrl+C. | Yes (`answers` list, id/title/aliases/option number matching). | Yes (single typed response when no answers/slots). | Yes: deterministic prompts for required slots (`expected_slots`) and merges `slot_bindings` before prompting missing fields. | Internal enrichment: may show `Template: ...` hint and render sentence from internal templates; public demo labels this best-effort. | Canonical `AskResult` keys preserved. |
| `satellite` | Home Assistant Assist satellite `assist_satellite.ask_question` service. | Assist runtime speech recognition/classification response. | Yes via sanitized `answers` payload to Assist. | Yes by omitting `answers`. | Indirect: slot capture comes from Assist response `slots`, not local reprompt loop. | Public sentence patterns in answers are forwarded to Assist; Assist performs template matching/slot capture. | Canonical `AskResult`; includes `no_match` normalization when answers provided but id missing. |
| `mobile` | Actionable notification with option buttons and optional text reply action; optional Done action in reply mode. | Websocket `mobile_app_notification_action` events correlated by generated `tag`. | Yes: button actions `OPT_<tag>_<id>` map to answer id + slot bindings. | Yes: reply-mode accumulates `reply_text`, terminal action is `DONE_<tag>`. | No deterministic required-slot reprompt loop in adapter. | No template rendering layer; sentence is selected label or last reply text. | Canonical `AskResult`; rich transport timeline/evidence in `meta`. |
| `discord` | Remote Discord turn service prompt (`/ask-turn`) with DM mode payload. | HTTP POST to turn service; response payload mapped back. | Yes: `choices` payload built from `answers` (`key`,`label`,`aliases`). | Yes when no `answers` (`ask_kind=freeform`). | No local required-slot reprompt loop in adapter. | No local template rendering; sentence semantics depend on turn-service `response_text`. | Canonical `AskResult`; slot bindings sourced from selected answer key. |

## D) Canonical usage examples (current real surface)

All examples below use the current canonical `ask` imports and `AskClient` call surface.

### 1) Open freeform ask (fully public)

```python
from ask import AskClient, AskSpec
from ask.config import Config

client = AskClient(Config(ha_api_url="https://home.example.com", ha_api_token="token"))
res = client.ask_question(channel="terminal", spec=AskSpec(question="What should we do next?"))
```

- **Channel:** terminal.
- **UX:** one prompt, user types text.
- **Boundary classification:** canonical public usage.

### 2) Stable decision / multiple choice (fully public)

```python
from ask import AskClient, AskSpec, Answer

spec = AskSpec(
    question="Proceed?",
    answers=[
        Answer(id="approve", title="Approve", sentences=["approve", "yes"]),
        Answer(id="block", title="Block", sentences=["block", "no"]),
    ],
)
res = client.ask_question(channel="terminal", spec=spec)
```

- **Channel:** terminal (also works through satellite/mobile/discord with channel-specific UX).
- **UX:** choice selection mapped to stable `id`.
- **Boundary classification:** canonical public usage.

### 3) Required slot collection (public ask input, terminal-specific execution)

```python
from ask import AskSpec

spec = AskSpec(question="Gather release details", expected_slots=["service", "version"])
res = client.ask_question(channel="terminal", spec=spec)
```

- **Channel:** terminal.
- **UX:** sequential prompts (`Service:`, then `Version:`).
- **Boundary classification:** public input + channel implementation detail.

### 4) Terminal demo style usage (canonical)

```python
from ask import AskClient, AskSpec, Answer

# mirrors ask.demo_terminal_scenarios patterns
res = client.ask_question(
    channel="terminal",
    spec=AskSpec(
        question="Classify this launch request.",
        answers=[
            Answer(id="approve", title="Approve", sentences=["approve", "allow"]),
            Answer(id="block", title="Block", sentences=["block", "deny"]),
        ],
    ),
)
```

- **Channel:** terminal demo path.
- **UX:** scenario menu calls canonical ask entrypoint.
- **Boundary classification:** canonical public usage.

### 5) Sentence/template boundary example (partially public, internally enriched)

```python
spec = AskSpec(
    question="What should I play?",
    expected_slots=["album", "artist"],
    answers=[Answer(id="play_album", sentences=["play {album} by {artist}"])],
)
res = client.ask_question(channel="terminal", spec=spec)
```

- **What is public:** sentence patterns via `Answer.sentences` and required slots via `expected_slots`.
- **What is internal:** terminal template object selection/hinting/rendering via internal `InteractionSpec.templates` / `AnswerTemplate`.
- **Important boundary truth:** the canonical public API does **not** expose a first-class public template object model today.

## E) Boundary analysis

### Canonical public usage
- Terminal demo scenarios use `ask` root exports (`AskClient`, `AskSpec`, `Answer`) and call `client.ask_question(channel="terminal", spec=...)`.
- Dispatcher routes all channels from a single public `ask_question` contract and persists results.
- Public root now exports `AskResult`, aligning code with documented return contract.

### Legitimate internal adaptation
- Terminal channel maps `AskSpec` to `InteractionSpec` and executes richer behavior while returning stable `AskResult`.
- Internal mapping isolates richer semantics from public compatibility surface.

### Transitional seam
- `AskSpec` is explicitly labeled transition-compatible/legacy-general while internal interaction models represent richer semantics.
- Template/sentence rendering in terminal is more naturally represented in internal `AnswerTemplate` than current public ask constructors.
- Tests for template rendering monkeypatch internal mapping seams, confirming partial public expressiveness.

### Workaround / bypass
- No direct evidence of demo code bypassing dispatcher or importing internal interaction models.
- No shadow result schema; channels normalize to canonical `AskResult` keys.

### Unclear
- Whether/when internal interaction types should be promoted to first-class public API remains undecided by current repo artifacts.

## F) Findings (ordered)

1. **Terminal demo is canonical at the entrypoint level.**  
   **Evidence:** Demo imports from `ask` root and dispatches with `AskClient.ask_question(channel="terminal", spec=...)`.  
   **Impact:** Demo is trustworthy for basic public API usage patterns.

2. **`InteractionSpec` is the central internal semantic layer for terminal behavior.**  
   **Evidence:** Terminal adapter calls `ask_spec_to_interaction` and branches on `InteractionMode` + slots/templates.  
   **Impact:** Internal semantic richness exists beyond direct public model expressiveness.

3. **Sentence/template semantics are partially public but mostly internally modeled in terminal.**  
   **Evidence:** Public inputs carry sentence patterns, but template hints/rendering depend on internal template constructs; demo text and tests acknowledge best-effort/internal seams.  
   **Impact:** Current UX can exceed what public types make explicit.

4. **Channels differ materially in user presentation and completion mechanics.**  
   **Evidence:** Satellite uses Assist service round-trip; mobile uses notification actions/events; Discord uses turn-service HTTP; terminal uses local prompt loop.  
   **Impact:** Same public ask input yields channel-specific UX and behavior envelopes.

5. **Docs are broadly honest but architecture understanding benefits from model/channel mapping.**  
   **Evidence:** README caveats channel differences and slot-template limits, but previously lacked a single model-family + channel-presentation map.  
   **Impact:** This report closes a practical comprehension gap before deeper template-boundary work.

## G) Risks (grounded)

- **Public expressiveness overestimation:** users may assume template-capable semantics are first-class public because sentence-pattern demos exist.
- **Internal model de facto promotion:** continued reliance on internal seams (especially in tests) may harden implicit contracts.
- **Channel expectation drift:** users may expect uniform ask UX across channels despite intentionally different presentation/collection mechanics.
- **Boundary ambiguity in docs:** without explicit model-family mapping, behavior can be described without clear ownership layer.

## H) Recommendations

### Immediate documentation/reporting recommendations
1. Keep this report as the architecture map and link it from README “Capability map and caveats.”
2. In docs, explicitly state: `AskSpec`/`Answer` are public ask-construction models; `InteractionSpec` family is internal semantic orchestration.
3. Keep sentence/template wording explicit: “public sentence patterns; internal template enrichment; channel-dependent behavior.”

### Possible follow-up engineering investigations (not in this change)
1. Decide whether template-capable ask construction should remain internal or become a first-class public spec.
2. Add tests that explicitly separate public commitments from internal seam behavior (especially template rendering cases).
3. Evaluate whether channel capability metadata should be codified to make UX differences discoverable programmatically.

---

## Appendix: key evidence pointers

- Public model definitions: `src/ask/types.py`.
- Internal semantic definitions and mapping: `src/ask/interaction_types.py`.
- Canonical exports: `src/ask/__init__.py`.
- Channel dispatch routing: `src/ask/dispatch.py`.
- Channel adapters: `src/ask/channels/{terminal,satellite,mobile,discord}.py`.
- Terminal demo scenarios: `src/ask/demo_terminal_scenarios.py`.
- Behavioral evidence: `tests/test_terminal_channel.py`, `tests/test_demo_terminal_scenarios.py`, `tests/test_import_surfaces.py`.
