from __future__ import annotations

import time
import uuid
from typing import Any, Dict

from .types import AskResult, AskSpec

_ASK_SESSIONS: Dict[str, Dict[str, Any]] = {}


def persist_ask_session(*, channel: str, spec: AskSpec, result: AskResult) -> str:
    meta = result.setdefault("meta", {})
    ask_session_id = str(meta.get("ask_session_id") or uuid.uuid4().hex)
    meta["ask_session_id"] = ask_session_id

    slot_evidence = meta.get("slot_evidence")
    if not isinstance(slot_evidence, dict):
        slot_evidence = {}
        meta["slot_evidence"] = slot_evidence

    replies = meta.get("replies")
    if not isinstance(replies, list):
        replies = []

    record = {
        "ask_session_id": ask_session_id,
        "channel": channel,
        "prompt": spec.question,
        "chosen_answer_id": result.get("id"),
        "sentence": result.get("sentence"),
        "replies": replies,
        "slot_evidence": slot_evidence,
        "slots": result.get("slots") if isinstance(result.get("slots"), dict) else {},
        "t_sent": meta.get("t_sent"),
        "t_first_reply": meta.get("t_first_reply"),
        "t_done": meta.get("t_done"),
        "persisted_at": time.time(),
    }
    _ASK_SESSIONS[ask_session_id] = record
    return ask_session_id


def get_ask_session(ask_session_id: str) -> Dict[str, Any] | None:
    return _ASK_SESSIONS.get(ask_session_id)


def clear_ask_sessions() -> None:
    _ASK_SESSIONS.clear()
