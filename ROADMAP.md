> Implementation-ready user stories live in `USER_STORIES.md`.

## 1) Reversible compression of the instructions (so you can expand back exactly)

### 1.1 Canonical “instruction pack” format

Use a **stable ID + dictionary + ordered blocks**. Compression is “replace repeated prose with references”. Reversal is “inline referenced blocks in order”.

**Rules (reversible):**

* Every block has an ID: `B01`, `B02`, …
* A “compressed doc” is just: **Header + block order list + block bodies + dictionary**
* When a block references another block, it uses `@Bxx`.
* Reversal = expand `@Bxx` by inlining that block’s body (recursively), preserving block order.
* No semantic shortening inside blocks unless done via dictionary tokens.

### 1.2 Dictionary tokens (lossless)

Define a small token dictionary once, then reuse it everywhere.

```
D:
  $AR = AskResult{id,sentence,slots,meta,error}
  $AS = AskSpec{question,answers,timeout_s,allow_replies,expect_reply,title,slot_schema,expected_slots}
  $AN = Answer{id,sentences,title,slot_bindings?}
  $EV = evidence{source,asked_at,answered_at,transcript,channel,session_id,confidence}
  $NV = normalized_state{location_state,motion_class,activity,place_cell,data_quality_band,...}
  $CV = change_vector{changed,meaningful,reason}
  $IL = invariant_gate{predicate,action,reason}
  $CI = CI{ruff,mypy,pytest,build,twine}
  $DB = SurrealDB{events,state,questions,reflections}
  $ES = Elasticsearch{projection,facets,rollover}
```

### 1.3 Compressed instruction set (example: “Schema completion by asking”)

This is the *compressed* form you can store in a single file and expand later.

```
INSTRPACK v0.1
ORDER: B01,B02,B03,B04,B05,B06,B07

B01 PURPOSE
  Build schemas by asking boundary questions; every filled field must have $EV.

B02 CONTRACTS
  Public API: ask_question(), ask_question_async(), yes_no_spec()
  Return must be $AR. slots are semantic-only; transport/debug goes in meta.

B03 CHANNELS
  satellite: Assist templates -> slots via wildcards.
  mobile: notifications + buttons; optional multi-reply + Done.
  discord: channel wait loop; metrics captured; optional buttons + Done.

B04 SLOT BINDING
  Satellite: slot capture from templates.
  Mobile/Discord: slot capture via:
    (a) button choices -> $AN.slot_bindings -> slots
    (b) reply-mode -> strict parser -> slots
  AskSpec may define slot_schema / expected_slots.

B05 EVIDENCE + METRICS
  Every ask session stores: t_sent,t_first_reply,t_done,latency_ms,replies,chosen_id,slots,$EV.
  Track: time-to-first-slot, time-to-complete-schema, probes-per-schema, failure-rate-by-channel.

B06 INVARIANTS
  Reject “complete” unless required fields satisfied or explicitly resolved (unknown/declined) WITH $EV.
  Don’t spam: enforce cooldown + jitter gates ($IL) before reflecting/asking again.

B07 STORAGE / PROJECTIONS
  $DB is truth: raw events + latest state + ask_sessions + schema_drafts + reflections.
  Optional $ES projection: daily indices + rollover; no refresh=true per write unless interactive.
```

**Reversal** is deterministic: expand in `ORDER`, inline `@Bxx` references if present, and expand dictionary tokens when rendering a “human version”.

If you want, I can also give you a tiny Python script that expands/compresses this format, but the above is already fully reversible by construction.

---

## 2) Plan to develop the suggested parts (concrete engineering plan)

### Workstream A — Fix “dedupe semantics” and projection invariants (status_reports + spatial)

**Goal:** make logs align with intended meaning: “latest snapshot” vs “append-only history”, and prevent jitter spam.

1. **Decide invariants per stream**

* `status_reports`: choose `snapshot` (overwrite by stable logical id) **or** `history` (append with stable `resource_id` + event id).
* `spatial_awareness`: keep append-only *raw* if you need audit, but **only reflect / project** on meaningful normalized changes.

2. **Implement canonicalization + ID strategy**

* `event_id = sha256(canonical_json(semantic_subset))`
* Exclude timestamps/uptime/noise from semantic subset (unless you *want* time-series identity).

3. **Bulk response postcondition**

* Parse ES bulk response: require `errors:false` and item-level success. Otherwise publish `success:false`.

4. **Remove `refresh=true` default**

* Use `refresh=false` normally; `wait_for` only for interactive endpoints/tests.

**Acceptance tests**

* Same input twice -> second run logs “exists / skipped” (or overwrites) exactly as invariant dictates.
* Jitter-only spatial samples do **not** trigger reflection calls.

---

### Workstream B — ha_ask upgrades: slots-for-schemas + Discord channel + metrics

**Goal:** turn asking into a schema completion tool with measurable latency and quality.

1. **Types update (backwards-compatible)**

* Add optional fields (don’t break existing callers):

  * `AskSpec.expected_slots: list[str] | None`
  * `AskSpec.slot_schema: dict | None` (JSON Schema fragment)
  * `Answer.slot_bindings: dict[str, Any] | None` (for mobile/discord buttons)
  * `AskResult.meta.ask_session_id | None`
  * `AskResult.meta.slot_evidence | None` (per-slot provenance)

2. **Channel implementations**

* **Satellite**: unchanged; keep Assist-native template capture.
* **Mobile**: buttons map to `Answer.slot_bindings`; reply-mode uses strict parsing when `expected_slots` present.
* **Discord**: async ask session:

  * post question + optional buttons + Done
  * collect replies; compute `t_first_reply`, `t_done`, `latency_*`
  * if button chosen -> fill `id` and apply `slot_bindings` to slots

3. **Metrics plumbing**

* Define a single `AskSession` record shape (works across all channels).
* Store: question, answers, user/channel, timestamps, transcripts, result, derived metrics.

**Acceptance tests**

* Unit: `yes_no_spec()` produces stable ids + titles.
* Unit: `Answer.slot_bindings` populates slots in mobile/discord choice mode.
* Async unit: discord timeout produces `error:"timeout"` and latency fields.
* Contract: slots remain semantic-only; meta holds transcripts/debug.

---

### Workstream C — “Schema Draft → Plan Questions → Ask → Apply → Finalize” service (FastAPI + SurrealDB)

**Goal:** a deterministic loop that completes schemas via boundary questions.

1. **Data model in SurrealDB**

* `schema_draft`: fields, missing, uncertain, constraints, state
* `question_episode` (or `ask_session`): channel + spec + result + evidence + metrics
* `schema_instance`: finalized, validated object + evidence map

2. **Endpoints**

* `POST /schemas/{name}/drafts` → create draft, compute missing/uncertain
* `POST /schemas/drafts/{id}/plan_questions` → ordered probes (IG×p(answer)×p(resolve)−cost)
* `POST /schemas/drafts/{id}/ask_next` → executes via ha_ask + stores ask_session
* `POST /schemas/drafts/{id}/apply` → applies slots to draft + updates missing
* `POST /schemas/drafts/{id}/finalize` → validates; enforces evidence invariants

3. **Planner policy (initial)**

* Prefer classification (answers) over free text.
* One probe per field-path per cooldown window.
* Escalate channel: satellite → mobile → discord based on failure/latency.

**Acceptance tests**

* Golden tests: same draft -> same planned questions.
* Finalize fails if required fields lack evidence.
* Apply updates only allowed fields and records per-field evidence.

---

## 3) Roadmap (sequenced, test-first, “definition of complete” style)

### Phase 0 — Baseline quality gates (1 PR)

* Add/verify `$CI` pipeline in Gitea:

  * `ruff`, `mypy`, `pytest`, `python -m build`, `twine check`
* Add “no tests ran” guard (CI fails if pytest collects 0 tests).

**Done when:** CI fails on lint/type/test/build regressions; at least 5 meaningful tests exist.

---

### Phase 1 — ha_ask: slots + evidence + metrics (2–3 PRs)

* Extend types with optional `slot_schema/expected_slots/slot_bindings`.
* Implement mapping of button choice → slots for mobile.
* Store `ask_session_id` + `slot_evidence` in meta.

**Done when:** you can complete a simple schema field via mobile button and see evidence + metrics stored.

---

### Phase 2 — Discord channel in ha_ask (2 PRs)

* Add async `ask_question_async()` and `channels/discord.py`.
* Add tests with a fake discord client (timeout + reply + button choice paths).
* Add optional dependency `ha-ask[discord]`.

**Done when:** discord ask session works end-to-end in bot process and produces latency metrics.

---

### Phase 3 — Spatial jitter invariants + “reflect only on meaningful change” (1–2 PRs)

* Introduce `$NV` + `$CV` in your spatial pipeline.
* Add `$IL` gates (accuracy-aware distance threshold, quality-band changes, cooldown).
* Stop ES `refresh=true` per event.

**Done when:** repeated “still at home with 0↔14m jitter” produces **no** reflections and minimal indexing noise.

---

### Phase 4 — Schema completion service (FastAPI + SurrealDB) (3–5 PRs)

* Implement `schema_draft` + planner + ask/apply/finalize endpoints.
* Plug ha_ask channels as executors.
* Persist ask_sessions and evidence maps.

**Done when:** a draft can be created from partial input, asked to completion, validated, finalized, and queried—with full evidence provenance.

---

### Phase 5 — Projections & lifecycle (ongoing)

* ES projections as optional read model:

  * daily indices + rollover/ILM
  * facets/views for dashboards
* Long-term metrics:

  * latency distributions by channel/question kind
  * question “resolution rate” and “follow-up churn”

**Done when:** dashboards can answer “which questions work best” and “where are we wasting tokens/time”.
