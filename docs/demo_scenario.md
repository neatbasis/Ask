# Canonical Demo Scenario: Schema Completion via Mobile Ask Flow

This document defines one **canonical, deterministic demo run** for schema completion. Future PRs should execute this flow and compare outputs against the exact target below.

## 1) Initial partial payload

Use this payload to create a draft (`POST /schemas/{name}/drafts`).

- Schema name: `person_profile_v1`
- Required fields: `full_name`, `preferred_contact_method`, `timezone`, `consent_to_contact`
- Initial payload (intentionally incomplete):

```json
{
  "full_name": "Alex Kim",
  "timezone": null,
  "preferred_contact_method": null,
  "consent_to_contact": null
}
```

Missing/uncertain fields at start (exactly 3):
1. `preferred_contact_method`
2. `timezone`
3. `consent_to_contact`

## 2) Expected planned questions (in exact order)

Run `POST /schemas/drafts/{id}/plan_questions` and assert the planner returns these probes in this exact sequence:

1. **Field:** `consent_to_contact`  
   **Question:** `Do you consent to being contacted about this request?`  
   **Mode:** choice  
   **Choices (id -> title):**
   - `consent_yes` -> `Yes`
   - `consent_no` -> `No`

2. **Field:** `preferred_contact_method`  
   **Question:** `What is your preferred contact method?`  
   **Mode:** choice  
   **Choices (id -> title):**
   - `contact_sms` -> `SMS`
   - `contact_email` -> `Email`
   - `contact_phone` -> `Phone call`

3. **Field:** `timezone`  
   **Question:** `What timezone should we use for scheduling?`  
   **Mode:** reply (free text parsed into a normalized timezone)

### Canonical answers to use during demo

To keep the run deterministic, provide these answers when asked:

1. `consent_to_contact` -> choose `consent_yes`
2. `preferred_contact_method` -> choose `contact_email`
3. `timezone` -> reply `America/Los_Angeles`

## 3) Channel for the canonical demo

Use **`mobile`** for every ask in this scenario.

- Channel: `mobile`
- Rationale: deterministic button IDs/titles for choice steps and stable transcript collection for reply mode.
- Do not switch channels mid-run for the canonical check.

## 4) Final schema instance expected after completion

After all asks are applied (`ask_next` + `apply`) and `finalize` succeeds, the finalized instance must equal:

```json
{
  "full_name": "Alex Kim",
  "preferred_contact_method": "email",
  "timezone": "America/Los_Angeles",
  "consent_to_contact": true
}
```

Normalization rules expected in this canonical run:
- `contact_email` button maps to semantic value `"email"`.
- `consent_yes` button maps to semantic value `true`.
- Timezone reply is stored as canonical IANA string `"America/Los_Angeles"`.

## 5) Required evidence artifacts per resolved field

Each resolved field must have a persisted evidence record (either in draft evidence map or finalized instance evidence map) with the following minimum artifacts.

### `consent_to_contact`
- `field_path`: `consent_to_contact`
- `source`: `ask_session`
- `channel`: `mobile`
- `question_text`: exact prompt used
- `answer_id`: `consent_yes`
- `answer_text`: `Yes`
- `slot_binding`: `{ "consent_to_contact": true }`
- `ask_session_id`: non-empty
- `asked_at`, `answered_at`: valid timestamps

### `preferred_contact_method`
- `field_path`: `preferred_contact_method`
- `source`: `ask_session`
- `channel`: `mobile`
- `question_text`: exact prompt used
- `answer_id`: `contact_email`
- `answer_text`: `Email`
- `slot_binding`: `{ "preferred_contact_method": "email" }`
- `ask_session_id`: non-empty
- `asked_at`, `answered_at`: valid timestamps

### `timezone`
- `field_path`: `timezone`
- `source`: `ask_session`
- `channel`: `mobile`
- `question_text`: exact prompt used
- `raw_reply`: `America/Los_Angeles`
- `parsed_value`: `America/Los_Angeles`
- `parse_status`: `success`
- `ask_session_id`: non-empty
- `asked_at`, `answered_at`: valid timestamps

---

## Exact success criteria for demo validation

A demo run is considered **PASS** only if all checks below pass.

1. **Draft initialization**
   - Draft creation succeeds.
   - Initial unresolved set is exactly `{consent_to_contact, preferred_contact_method, timezone}`.

2. **Deterministic planning**
   - `plan_questions` returns exactly 3 questions.
   - Order matches this document exactly.
   - Choice question IDs/titles match exactly.

3. **Channel consistency**
   - Every ask session records `meta.channel == "mobile"`.
   - No fallback/escalation to other channels occurs.

4. **Answer application correctness**
   - `consent_yes` maps to boolean `true`.
   - `contact_email` maps to enum/string `"email"`.
   - Reply parser resolves `America/Los_Angeles` successfully.

5. **Evidence completeness**
   - All 3 fields have evidence entries.
   - Each evidence entry includes required artifacts listed in Section 5.
   - Each evidence entry references a non-empty `ask_session_id`.

6. **Finalize gate**
   - `finalize` returns success.
   - Finalized instance exactly equals Section 4 JSON (no extra or missing keys).

7. **No unresolved required fields**
   - Required field unresolved count is `0` at finalize time.

8. **Repeatability check**
   - Running the same canonical answers on a fresh draft produces identical final JSON and same planned question order.

If any criterion above fails, mark the demo run **FAIL** and include a diff against this document in the PR description.
