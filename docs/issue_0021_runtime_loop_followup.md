# ISSUE-0021 follow-up: runtime-loop seam status after transport extraction

Date: 2026-03-28

## Scope

This note records the post-transport-extraction seam check requested for:

- `runtime_loop.sat_say`
- facade `sat_say`
- `run_chat_loop`
- transport ownership for Home Assistant satellite output

## Investigation summary

Repository-wide symbol search was run for the legacy seam names:

- `sat_say`
- `run_chat_loop`
- `runtime_loop`
- `ha_satellite_output`
- `start_conversation`

Result: **no matches** in `src/`, `tests/`, `docs/`, `README.md`, or `ROADMAP.md`.

In this repository revision, the active satellite transport owner is channel adapter code:

- `ask.channels.satellite.ask_question(...)`
- `ha_ask.channels.satellite.ask_question(...)` (compatibility package path)

Those adapters call Home Assistant `assist_satellite.ask_question` via the shared client transport helper (`call_service_with_response`).

## Reclassification for retirement inventory

Because the legacy names are no longer present in the current tree:

- `sat_say`: treat as **already retired / not present** in this codebase.
- `runtime_loop` ownership wording updates: **not applicable** (no `runtime_loop.py` currently exists).
- `run_chat_loop` extraction target: **not applicable under current package layout**.

## Next extraction seam in this repo

For this codebase, the closest remaining runtime ownership seam is not `run_chat_loop`; it is the dispatcher/channel boundary:

- canonical orchestration surface: `ask.dispatch.dispatch_ask_question(...)`
- canonical satellite transport surface: `ask.channels.satellite.ask_question(...)`

Any further extraction should focus on reducing compatibility duplication between `ask` and `ha_ask` wrappers while preserving import stability.
