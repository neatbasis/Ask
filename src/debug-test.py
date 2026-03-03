#!/usr/bin/env python3
"""
debug-test.py

Interactive falsification-oriented tests for:
- direct Assist Satellite ask_question calls (with/without answers)
- adapter-based ask_question via ha_ask dispatcher (satellite + mobile)
- Assist-compatible contract checks:
    * id semantics
    * slots contains ONLY wildcard captures (no transport metadata)
    * transport/UI metadata lives in top-level result["meta"]
    * error classification uses ha_ask.errors helpers

Environment:
  HA_API_URL
  HA_API_SECRET
  (optional) HA_SATELLITE_ENTITY_ID
  (optional) HA_NOTIFY_SERVICE

Run:
  python3 debug-test.py
"""

from __future__ import annotations

import os
import sys
import json
from typing import Any, Dict, List, Optional

from ha_ask import ask_question, AskSpec, Answer
from ha_ask.config import Config, derive_ws_url
from ha_ask.types import AskResult
from ha_ask.errors import (
    error_kind,
    is_ok,
    is_match,
    is_no_match,
    is_no_response,
    is_timeout,
    is_other_error,
)

from homeassistant_api import Client
from homeassistant_api.processing import Processing, process_json
import homeassistant_api.errors as ha_errors


# ─────────────────────────────────────────────
# Processors needed for stability (match your working pattern)
# ─────────────────────────────────────────────
@Processing.processor("application/json")
def _json_processor(response):
    return process_json(response)


@Processing.processor("text/html")
def _html_processor(response):
    return response.text


@Processing.processor("text/plain")
def _text_processor(response):
    return response.text


# ─────────────────────────────────────────────
# Errors (for direct calls)
# ─────────────────────────────────────────────
InternalServerError = getattr(ha_errors, "InternalServerError", None)
BaseHAError = (
    getattr(ha_errors, "HomeAssistantAPIError", None)
    or getattr(ha_errors, "HomeAssistantApiError", None)
    or getattr(ha_errors, "HomeAssistantError", None)
    or getattr(ha_errors, "ClientError", None)
    or getattr(ha_errors, "ServerError", None)
    or Exception
)


def classify_direct_error(exc: BaseHAError) -> str:
    """Map client exceptions to stable-ish strings (mirrors your client.py behavior)."""
    is_500 = InternalServerError is not None and isinstance(exc, InternalServerError)
    return "no_response" if is_500 else f"{type(exc).__name__}: {exc}"


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def pp(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def assert_assist_slots_pure(result: Dict[str, Any], label: str) -> None:
    """
    Assist contract:
      - slots must be only wildcard captures from the matching answer template
      - therefore, slots must be a dict
      - and must NOT contain transport metadata keys like "_meta"
    """
    slots = result.get("slots")
    if not isinstance(slots, dict):
        print(f"[FAIL] {label}: slots is not a dict: {type(slots)}")
        return
    if "_meta" in slots:
        print(f"[FAIL] {label}: slots contains '_meta' (transport metadata pollution)")
        return
    print(f"[OK]   {label}: slots is Assist-pure (keys={sorted(slots.keys())})")


def assert_meta_present(result: Dict[str, Any], label: str) -> None:
    meta = result.get("meta")
    if not isinstance(meta, dict):
        print(f"[FAIL] {label}: meta is not a dict: {type(meta)}")
        return
    print(f"[OK]   {label}: meta present (keys={sorted(meta.keys())})")


def summarize_result(res: AskResult) -> str:
    err = res.get("error")
    kind = error_kind(err)
    return f"error={err!r} kind={kind!r} id={res.get('id')!r} sentence={res.get('sentence')!r}"


def report_adapter_result(res: AskResult, label: str, *, expect_mode: str) -> None:
    """
    Assertion + reporting layer using ha_ask.errors helpers.

    expect_mode:
      - "satellite_choice": answers provided, expect match or no_match (or no_response/timeout)
      - "satellite_free": no answers, expect ok with id None (or no_response/timeout)
      - "mobile_choice": buttons provided, expect match (or timeout/no_response/other)
      - "mobile_reply": no answers, expect ok with id None; sentence may be "" if no reply (or timeout/no_response/other)
    """
    print(f"\n[{label}] {summarize_result(res)}")
    assert_assist_slots_pure(res, label)
    assert_meta_present(res, label)

    if is_ok(res):
        # success cases
        if expect_mode in ("satellite_choice", "mobile_choice"):
            if is_match(res):
                print(f"[OK]   {label}: matched (id={res.get('id')!r})")
            else:
                # ok + id None in choice modes is suspicious
                print(f"[WARN] {label}: ok=True but id=None (unexpected for {expect_mode})")
        elif expect_mode in ("satellite_free", "mobile_reply"):
            if res.get("id") is None:
                print(f"[OK]   {label}: free-form semantics (id=None)")
            else:
                print(f"[WARN] {label}: expected id=None but got id={res.get('id')!r}")
        return

    # failure cases
    if is_no_match(res):
        if expect_mode == "satellite_choice":
            print(f"[OK]   {label}: no_match (expected possibility for satellite_choice)")
        else:
            print(f"[WARN] {label}: no_match unexpected for {expect_mode}")
        return

    if is_no_response(res):
        print(f"[OK]   {label}: no_response (silence / server / response-less path)")
        return

    if is_timeout(res):
        print(f"[OK]   {label}: timeout")
        return

    if is_other_error(res):
        print(f"[WARN] {label}: other error (channel-specific): {res.get('error')!r}")
        return

    print(f"[WARN] {label}: unclassified error: {res.get('error')!r}")


def as_fake_askresult_from_direct(
    *,
    data: Dict[str, Any],
    had_answers: bool,
    meta: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> AskResult:
    """
    Wrap raw direct HA payload into an AskResult-like structure so we can reuse errors.py helpers
    and our common reporting + invariants.

    NOTE: this is test-only glue, not library code.
    """
    id_ = data.get("id")
    sentence = data.get("sentence")
    slots = data.get("slots") or {}
    if not isinstance(slots, dict):
        slots = {}

    # If explicit error passed, keep it. Otherwise infer a best-effort error for reporting.
    if error is None:
        if sentence is None:
            error = "no_response"
        elif had_answers and id_ is None:
            error = "no_match"
        else:
            error = None

    return AskResult(
        id=id_,
        sentence=sentence,
        slots=slots,
        meta=meta or {"channel": "direct"},
        error=error,
    )


# ─────────────────────────────────────────────
# Direct API tests (bypass our adapters)
# ─────────────────────────────────────────────
def direct_satellite_call(
    client: Client,
    *,
    entity_id: str,
    question: str,
    answers: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    kwargs = dict(entity_id=entity_id, question=question, preannounce=True)
    if answers is not None:
        kwargs["answers"] = answers

    _result, data = client.trigger_service_with_response("assist_satellite", "ask_question", **kwargs)
    if not isinstance(data, dict):
        data = {"_non_dict_data": repr(data)}
    return data


# ─────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────
def test_T1_direct_satellite_with_answers(client: Client, entity_id: str) -> None:
    section("T1 (DIRECT) assist_satellite.ask_question WITH answers (expect id yes/no)")
    print("Speak one of the expected utterances into the satellite, e.g. 'yes'/'yeah' or 'no'/'nope'.")
    answers = [
        {"id": "yes", "sentences": ["yes", "yeah", "of course", "sure"]},
        {"id": "no", "sentences": ["no", "nope", "nah"]},
    ]

    try:
        data = direct_satellite_call(
            client,
            entity_id=entity_id,
            question="Say YES (yes/yeah/of course/sure) OR say NO (no/nope/nah)",
            answers=answers,
        )
        res = as_fake_askresult_from_direct(
            data=data,
            had_answers=True,
            meta={"channel": "direct", "test": "T1", "entity_id": entity_id},
        )
    except BaseHAError as e:
        res = AskResult(
            id=None,
            sentence=None,
            slots={},
            meta={"channel": "direct", "test": "T1", "entity_id": entity_id},
            error=classify_direct_error(e),
        )

    pp(res)
    report_adapter_result(res, "T1 direct satellite", expect_mode="satellite_choice")
    print("\n[REPORT BACK] Did id become 'yes' or 'no'? If it stayed None, note the utterance + sentence.")


def test_T2_direct_satellite_without_answers(client: Client, entity_id: str) -> None:
    section("T2 (DIRECT) assist_satellite.ask_question WITHOUT answers (expect id=None, sentence populated)")
    print("Speak anything into the satellite.")

    try:
        data = direct_satellite_call(
            client,
            entity_id=entity_id,
            question="Say anything (no answers provided)",
            answers=None,
        )
        res = as_fake_askresult_from_direct(
            data=data,
            had_answers=False,
            meta={"channel": "direct", "test": "T2", "entity_id": entity_id},
        )
    except BaseHAError as e:
        res = AskResult(
            id=None,
            sentence=None,
            slots={},
            meta={"channel": "direct", "test": "T2", "entity_id": entity_id},
            error=classify_direct_error(e),
        )

    pp(res)
    report_adapter_result(res, "T2 direct satellite", expect_mode="satellite_free")
    print("\n[REPORT BACK] Confirm id is None and sentence is your utterance.")


def test_T3_direct_satellite_case_robustness(client: Client, entity_id: str) -> None:
    section("T3 (DIRECT) satellite case robustness (try 'Yes' / 'YES' / 'yeah')")
    print("Try saying 'Yes', 'YES', 'yeah', 'of course'.")
    answers = [
        {"id": "yes", "sentences": ["yes", "yeah", "of course", "sure"]},
        {"id": "no", "sentences": ["no", "nope", "nah"]},
    ]

    try:
        data = direct_satellite_call(
            client,
            entity_id=entity_id,
            question="Try variants: Yes / YES / yeah / of course",
            answers=answers,
        )
        res = as_fake_askresult_from_direct(
            data=data,
            had_answers=True,
            meta={"channel": "direct", "test": "T3", "entity_id": entity_id},
        )
    except BaseHAError as e:
        res = AskResult(
            id=None,
            sentence=None,
            slots={},
            meta={"channel": "direct", "test": "T3", "entity_id": entity_id},
            error=classify_direct_error(e),
        )

    pp(res)
    report_adapter_result(res, "T3 direct satellite", expect_mode="satellite_choice")
    print("\n[REPORT BACK] Which variants reliably map to id yes/no on your instance?")


def test_T4_adapter_satellite_answers(cfg: Config) -> None:
    section("T4 (ADAPTER) ha_ask ask_question(channel='satellite') with answers (expect id yes/no)")
    spec = AskSpec(
        question="Say YES (yes/yeah/of course/sure) OR say NO (no/nope/nah)",
        answers=[
            Answer("yes", ["yes", "yeah", "of course", "sure"], title="Yes"),
            Answer("no", ["no", "nope", "nah"], title="No"),
        ],
        timeout_s=60,
    )
    res = ask_question(
        channel="satellite",
        spec=spec,
        api_url=cfg.api_url,
        token=cfg.token,
        satellite_entity_id=cfg.satellite_entity_id,
    )

    pp(res)
    report_adapter_result(res, "T4 adapter satellite", expect_mode="satellite_choice")
    print("\n[REPORT BACK] If id is None here but not in T1/T3, then our adapter is not passing answers correctly.")


def test_T5_adapter_mobile_choice(cfg: Config) -> None:
    section("T5 (ADAPTER) ha_ask ask_question(channel='mobile') choice-mode (expect id yes/no, replies collected)")
    notify_service = cfg.notify_service or os.environ.get("HA_NOTIFY_SERVICE")
    if not notify_service:
        print("[SKIP] No HA_NOTIFY_SERVICE set. Add it to .env to run mobile tests.")
        return

    spec = AskSpec(
        question="Proceed with the next step? (You can reply multiple times, then press Yes/No)",
        answers=[
            Answer("yes", ["yes"], title="Yes"),
            Answer("no", ["no"], title="No"),
        ],
        allow_replies=True,
        timeout_s=300,
        title="SemanticNG",
    )

    res = ask_question(
        channel="mobile",
        spec=spec,
        api_url=cfg.api_url,
        token=cfg.token,
        notify_service=notify_service,
    )

    pp(res)
    report_adapter_result(res, "T5 adapter mobile choice", expect_mode="mobile_choice")
    print("\n[REPORT BACK] Confirm:")
    print("  - id is 'yes' or 'no'")
    print("  - meta['replies'] contains all replies")
    print("  - slots is {} (Assist-pure)")


def test_T6_adapter_mobile_reply(cfg: Config) -> None:
    section("T6 (ADAPTER) ha_ask ask_question(channel='mobile') reply-mode (expect id=None, sentence=last reply)")
    notify_service = cfg.notify_service or os.environ.get("HA_NOTIFY_SERVICE")
    if not notify_service:
        print("[SKIP] No HA_NOTIFY_SERVICE set. Add it to .env to run mobile tests.")
        return

    spec = AskSpec(
        question="Tell me what you want next. You can reply multiple times, then press Done.",
        answers=None,          # reply-mode
        expect_reply=True,     # ensures Done exists
        allow_replies=True,
        timeout_s=300,
        title="SemanticNG",
    )

    res = ask_question(
        channel="mobile",
        spec=spec,
        api_url=cfg.api_url,
        token=cfg.token,
        notify_service=notify_service,
    )

    pp(res)
    report_adapter_result(res, "T6 adapter mobile reply", expect_mode="mobile_reply")
    print("\n[REPORT BACK] Confirm:")
    print("  - id is None (Assist semantics for free reply)")
    print("  - sentence is last reply (or empty string if none)")
    print("  - meta['replies'] contains all replies")
    print("  - slots is {} (Assist-pure)")


def main() -> None:
    cfg = Config.from_env()

    if not cfg.api_url or not cfg.token:
        sys.exit("Missing HA_API_URL or HA_API_SECRET in environment")

    rest = cfg.api_url
    entity_id = cfg.satellite_entity_id or "assist_satellite.esphome_mycroft_assist_satellite"

    section("CONFIG")
    print("REST:", rest)
    print("WS:  ", derive_ws_url(cfg.api_url))
    print("SATELLITE_ENTITY_ID:", entity_id)
    print("NOTIFY_SERVICE:", cfg.notify_service or os.environ.get("HA_NOTIFY_SERVICE"))

    # Direct tests (satellite)
    with Client(rest, cfg.token) as client:
        test_T1_direct_satellite_with_answers(client, entity_id)
        test_T2_direct_satellite_without_answers(client, entity_id)
        test_T3_direct_satellite_case_robustness(client, entity_id)

    # Adapter tests
    test_T4_adapter_satellite_answers(cfg)
    test_T5_adapter_mobile_choice(cfg)
    test_T6_adapter_mobile_reply(cfg)

    section("DONE")
    print("Please paste the outputs of T1–T6 back into chat (or summarize each).")


if __name__ == "__main__":
    main()
