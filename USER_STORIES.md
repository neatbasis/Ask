# Roadmap User Stories

This document translates `ROADMAP.md` into actionable user stories with acceptance criteria.

## Epic A — Reliable event semantics and projection invariants

### Story A1 — Choose deterministic stream semantics
**As a** platform engineer  
**I want** each stream (`status_reports`, `spatial_awareness`) to have an explicit invariant (`snapshot` vs `history`)  
**So that** duplicate handling and downstream behavior are predictable.

**Acceptance criteria**
- Stream invariant is declared and documented for each stream.
- Running the same payload twice follows the declared behavior (overwrite or skip/exists).
- Spatial raw history and reflected projections are separated by policy.

### Story A2 — Canonical identity and dedupe
**As a** data engineer  
**I want** event identity to be derived from canonical semantic content  
**So that** noise (timestamps/uptime jitter) does not create false uniqueness.

**Acceptance criteria**
- `event_id` is computed from `sha256(canonical_json(semantic_subset))`.
- Non-semantic noise fields are excluded from the dedupe subset.
- Two semantically equivalent events resolve to the same identity.

### Story A3 — Correct bulk postconditions
**As a** service operator  
**I want** bulk indexing to verify item-level success  
**So that** failures are surfaced instead of silently reported as success.

**Acceptance criteria**
- Bulk response handling checks `errors: false` and each item status.
- Service response reports `success: false` when any item fails.
- Failure paths are covered by tests.

### Story A4 — Refresh policy aligned with workload
**As a** performance-conscious developer  
**I want** indexing to default to `refresh=false`  
**So that** throughput remains stable under normal writes.

**Acceptance criteria**
- `refresh=true` is removed as default behavior.
- `refresh=wait_for` is used only for interactive/test paths.
- Documentation describes when to use each refresh mode.

### Story A5 — Reflect only on meaningful spatial change
**As a** user of spatial reflections  
**I want** reflections to trigger only on meaningful normalized changes  
**So that** jitter does not spam downstream systems.

**Acceptance criteria**
- Normalized state (`NV`) and change vector (`CV`) are computed for each sample.
- Invariant gates (`IL`) include distance/quality/cooldown checks.
- Repeated “still at home” jitter does not trigger reflection.

---

## Epic B — `ha_ask` as a schema-completion engine

### Story B1 — Add backward-compatible schema fields
**As a** SDK consumer  
**I want** optional slot/schema metadata in ask contracts  
**So that** I can progressively adopt schema completion without breaking callers.

**Acceptance criteria**
- `AskSpec.expected_slots` and `AskSpec.slot_schema` are optional.
- `Answer.slot_bindings` is optional and available for choice channels.
- `AskResult.meta` includes optional `ask_session_id` and `slot_evidence`.
- Existing callers remain compatible.

### Story B2 — Mobile choice-to-slot mapping
**As a** workflow author  
**I want** mobile button selections to populate semantic slots  
**So that** structured schema fields can be filled without free text parsing.

**Acceptance criteria**
- Button answer selection applies `Answer.slot_bindings` into `slots`.
- `slots` remains semantic-only.
- Reply transcripts/debug details stay in `meta`.

### Story B3 — Strict reply parsing for expected slots
**As a** schema planner  
**I want** mobile/discord reply mode to parse against expected slots  
**So that** free-text responses can be validated and mapped consistently.

**Acceptance criteria**
- Reply mode uses strict parsing when `expected_slots` is set.
- Parse failures are represented clearly in result/error metadata.
- Successful parses produce slot-level evidence.

### Story B4 — Discord ask sessions
**As a** bot operator  
**I want** a Discord channel implementation with async collection and Done semantics  
**So that** schema prompts can run in chat reliably.

**Acceptance criteria**
- Discord asks post question, optional buttons, and terminal Done action.
- Session captures first reply time, completion time, and latency fields.
- Timeout returns `error: "timeout"` with metrics populated.

### Story B5 — Cross-channel ask session metrics
**As a** product analyst  
**I want** one unified ask session record shape across channels  
**So that** latency and quality analysis is comparable.

**Acceptance criteria**
- Ask session schema stores prompts, answers, channel/user, transcript, result, and derived metrics.
- Metrics include time-to-first-reply, completion latency, replies count, chosen id, and slots/evidence.
- Metrics are persisted for Satellite, Mobile, and Discord.

---

## Epic C — Draft-to-finalize schema completion service

### Story C1 — Draft creation from partial input
**As a** API client  
**I want** to create schema drafts from partial objects  
**So that** missing and uncertain fields are tracked for completion.

**Acceptance criteria**
- `POST /schemas/{name}/drafts` creates a `schema_draft` record.
- Draft state includes missing/uncertain fields and constraints.
- Draft records are persisted in SurrealDB.

### Story C2 — Deterministic question planning
**As a** planner consumer  
**I want** deterministic ordered probes for a given draft state  
**So that** planning is explainable and testable.

**Acceptance criteria**
- `POST /schemas/drafts/{id}/plan_questions` returns ordered probes.
- Ordering follows IG × p(answer) × p(resolve) − cost heuristic.
- Golden tests show same draft -> same plan.

### Story C3 — Ask-next execution with evidence capture
**As a** completion service  
**I want** to execute the next planned question via `ha_ask`  
**So that** ask sessions and evidence are stored consistently.

**Acceptance criteria**
- `POST /schemas/drafts/{id}/ask_next` runs through configured channel executor.
- Ask session is stored with raw transcript, metrics, and slot evidence.
- Channel escalation path is supported by policy.

### Story C4 — Apply answers safely to drafts
**As a** data steward  
**I want** only allowed fields to be updated when applying answers  
**So that** schema integrity is preserved.

**Acceptance criteria**
- `POST /schemas/drafts/{id}/apply` updates only allowed field paths.
- Per-field evidence mapping is updated during apply.
- Tests verify blocked writes to disallowed fields.

### Story C5 — Evidence-gated finalize
**As a** compliance-focused user  
**I want** finalize to fail when required fields lack evidence  
**So that** completed objects are fully attributable.

**Acceptance criteria**
- `POST /schemas/drafts/{id}/finalize` validates required fields + constraints.
- Finalization fails if required fields have no evidence or explicit unknown/declined resolution.
- Finalized instance persists validated object with evidence map.

---

## Delivery plan as release-oriented stories

### Phase 0 — Quality gates
- CI runs `ruff`, `mypy`, `pytest`, build, and twine checks.
- CI fails if pytest collects zero tests.

### Phase 1 — `ha_ask` slots/evidence/metrics
- Stories: B1, B2, B5 (initial persistence path).

### Phase 2 — Discord support
- Stories: B4 plus async API and optional dependency packaging.

### Phase 3 — Spatial invariants
- Stories: A1, A2, A5 (+ refresh policy A4 where pipeline touches indexing).

### Phase 4 — Schema completion service
- Stories: C1, C2, C3, C4, C5.

### Phase 5 — Projections/lifecycle
- Story set expands from A4/A5 and B5 metrics into dashboard-facing read models.
