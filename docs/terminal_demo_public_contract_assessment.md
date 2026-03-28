# Terminal demo vs canonical Ask surface: architectural assessment

## A) Executive conclusion

**Verdict: Mixed.**

The terminal scenario demo (`ask.demo_terminal_scenarios`) does construct requests via the canonical public surface (`AskClient` + `AskSpec` + `Answer`) and dispatches through `client.ask_question(channel="terminal", spec=...)`, which is faithful to advertised usage. However, the terminal adapter itself immediately translates `AskSpec` into richer internal `InteractionSpec` semantics and conditionally supports behaviors (template hints/rendering) that are not naturally expressible via public `AskSpec` construction in the demo path. This is partly legitimate adapter-layer evolution, but also a transitional seam that leaks into tests and demo messaging. In particular, sentence-style/template behavior is validated by monkeypatching internal interaction mapping in tests, indicating the full behavior is not directly driven by canonical public models alone. Result shape remains canonically stable (`AskResult` keys) in terminal paths, which strengthens contract coherence. The docs and demo text are unusually explicit that sentence-style support is “best-effort” on today’s public API, which reduces risk of outright misrepresentation. Net: the demo is trustworthy for basic canonical flows, but not yet a pure proof that the full interaction semantics are first-class in the public model.

## B) Evidence table

| Area | Evidence found | Why it matters | Verdict |
|---|---|---|---|
| Public exports | `ask.__init__` exports `AskClient`, dispatch helpers, `AskSpec`/`ChoiceSpec`/`FreeformSpec`, and `Answer`; it does **not** export `InteractionSpec` family. | Shows the canonical surface is intentionally centered on `AskSpec`-style models, with richer interaction types kept off the main public import surface. | Canonical public usage with hidden richer internals. |
| Demo scenario construction | `ask.demo_terminal_scenarios` imports from `ask` (`AskClient`, `AskSpec`, `Answer`), builds all scenarios via `AskSpec`, and calls `client.ask_question(channel="terminal", spec=spec)`. | Confirms the demo itself uses public construction and canonical dispatch entrypoint, not a terminal-only private API. | Canonical public usage. |
| Dispatch contract | `ask.dispatch.ask_question` routes terminal by calling `terminal_chan.ask_question(spec)` and always persists/returns `AskResult`. | Demonstrates one common dispatcher path for terminal and non-terminal channels; no demo-only dispatcher bypass. | Canonical public usage. |
| Terminal adapter input surface | Terminal channel signature accepts `spec: AskSpec`; returns standardized `AskResult` via `_ok_result` / `_cancel_result` with stable keys. | Preserves public request/result contract externally. | Legitimate adapter implementation. |
| Terminal adapter internal model conversion | `ask.channels.terminal` imports `ask_spec_to_interaction` and branches on internal `InteractionMode`, slots, templates. | Indicates adapter depends on richer internal semantics than exposed in core demo construction types. | Legitimate internal adaptation with transitional seam. |
| Response/result contract | Tests assert terminal results include exactly `{id, sentence, slots, meta, error}` and channel metadata under `meta`. | Strong evidence of contract consistency and no demo-only result shape. | Canonical contract upheld. |
| Sentence-style / advanced interaction support | Scenario 5 explicitly says public API is “best effort”; full template rendering is noted as internal. Tests for template rendering monkeypatch `ask_spec_to_interaction` to inject `InteractionSpec(...templates=...)`. | Suggests advanced capability currently relies on internal constructs not directly modeled in public scenario-building API. | Transitional seam; partial public-model incompleteness. |
| Docs/examples alignment | README claims terminal demo and caveats terminal/satellite differences; capability map says terminal/mobile do not perform voice-template extraction and labels helper APIs as transitional where applicable. | Documentation is largely aligned with limitations rather than hiding them. | Mostly aligned and honest, though transitional complexity remains. |

## C) Boundary analysis

### Canonical public usage
- Terminal demo constructs scenarios with `AskSpec`/`Answer` imported from `ask` and runs via `AskClient.ask_question`. 
- Dispatch path uses the canonical channel router (`ask.dispatch.ask_question`) and shared persistence.
- Returned objects follow documented `AskResult` shape.

### Legitimate internal adaptation
- Terminal adapter converts public `AskSpec` into internal `InteractionSpec` via `ask_spec_to_interaction` to normalize behavior across richer semantic modes.
- Internal helpers for slot collection/template rendering are adapter details and remain hidden from the advertised top-level API.

### Transitional compatibility seam
- `AskSpec` is explicitly described as “legacy/general spec kept for transition compatibility,” while internal `InteractionSpec` represents richer semantic center.
- Sentence-style/template behavior in terminal is partially exercised only through internal injection in tests, not purely by public constructors.
- `AskResult` exists in `types.py` but is not exported from `ask.__init__`, creating a small public-story gap.

### Workaround / bypass
- No evidence that the demo script directly imports internal interaction types or calls a private terminal-only dispatch bypass.
- No evidence of alternate/shadow result schema in terminal demo code.

### Unclear
- Whether `InteractionSpec` (or parts of it) is intended to become public was not explicitly declared in a design doc; code comments imply an “additive seam” but not final boundary intent.

## D) Findings (most important first)

1. **The terminal demo is canonically wired at the entrypoint level.**  
   **Evidence:** Demo imports `AskClient`, `AskSpec`, `Answer` from `ask`; scenarios call `client.ask_question(channel="terminal", spec=...)`.  
   **Impact:** Downstream users can trust the demo for how to call Ask through its public API.

2. **The terminal adapter’s behavior is powered by internal interaction modeling, not just raw `AskSpec`.**  
   **Evidence:** Terminal channel invokes `ask_spec_to_interaction(spec)` and branches on `InteractionMode`, required slots, templates.  
   **Impact:** This is architecturally fine as an adapter detail, but it means runtime semantics are richer than what public constructors currently express directly.

3. **Advanced template/sentence-style behavior is only partially first-class in the public model.**  
   **Evidence:** Scenario 5 says full template object rendering is internal; terminal tests monkeypatch interaction mapping to inject templates.  
   **Impact:** Demonstrates incomplete public expressiveness for richer interactions, despite functioning internal support.

4. **Result contract coherence is strong across terminal flows.**  
   **Evidence:** Terminal tests enforce exact `AskResult` key set and stable semantics for id/sentence/slots/meta/error.  
   **Impact:** Reduces risk of demo-only response-shape drift and supports cross-channel consistency.

5. **Documentation is more transparent than deceptive about transitional status.**  
   **Evidence:** README marks helper APIs as transitional and documents terminal slot/template caveats; demo prints notes about best-effort sentence-style behavior.  
   **Impact:** Limits false confidence, though users still face a two-layer mental model (public spec vs richer internal semantics).

## E) Risks

- **False confidence risk (moderate):** Users may infer sentence-style/template semantics are fully public because terminal can demonstrate parts of them, while key mechanisms remain internal/transitional.
- **Public expressiveness gap risk (moderate):** If product direction leans on richer interaction modes, `AskSpec` may become an underspecified façade.
- **Internal-model ossification risk (moderate):** Internal `InteractionSpec` could become de facto API via tests and adapter behavior before being formally declared/curated.
- **Boundary clarity risk (low-to-moderate):** Not exporting/typing `AskResult` at top-level canonical surface can blur what is guaranteed for consumers.

## F) Recommendation

**Accept but document as transitional.**

The current structure is not an outright bypass architecture: entrypoints are canonical, and adapter translation is a legitimate internal pattern. But evidence shows advanced semantics are only partially representable in public constructors and are sometimes validated through internal seams. Treat the terminal demo as a trustworthy canonical example for baseline ask flows, while explicitly framing sentence-style/template interactions as transitional capabilities backed by internal models until/unless the public model boundary is expanded.

## G) Optional follow-up deltas (small, high leverage)

1. Publicly document the `AskSpec -> InteractionSpec` translation boundary as intentional adapter internals.
2. Export `AskResult` (or an equivalent stable result protocol) from canonical `ask` surface to tighten contract clarity.
3. Add a targeted test proving scenario-5 behavior *without* monkeypatching internal interaction mapping, or explicitly mark that behavior as internal-only in tests.
4. Add one README matrix row: “publicly expressible today” vs “internally supported” for sentence/template features.
