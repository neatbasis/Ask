# ha_ask/channels/mobile.py
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from homeassistant_api import Client, WebsocketClient

from ..types import AskSpec, AskResult, Answer
from ..errors import ERR_TIMEOUT
from ..client import call_service_no_response


@dataclass
class _Session:
    tag: str
    t_sent: float
    t_first_reply: Optional[float] = None
    t_done: Optional[float] = None
    replies: list[str] = field(default_factory=list)
    events: list[Dict[str, Any]] = field(default_factory=list)
    device_id: Optional[str] = None


def _to_dict(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    try:
        return dict(obj)
    except Exception:
        return {"_raw": repr(obj)}


def _extract_data(evd: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize event shape from homeassistant_api websocket client.

    We care about inner event data fields:
      tag, action, reply_text, device_id, ...
    """
    if "data" in evd and isinstance(evd["data"], dict):
        return evd["data"]
    if "event" in evd and isinstance(evd["event"], dict):
        inner = evd["event"]
        if "data" in inner and isinstance(inner["data"], dict):
            return inner["data"]
    if "event_data" in evd and isinstance(evd["event_data"], dict):
        return evd["event_data"]
    return evd if isinstance(evd, dict) else {}


def ask_question(
    client: Client,
    ws: WebsocketClient,
    spec: AskSpec,
    notify_service: str,
) -> AskResult:
    """
    Mobile channel adapter using actionable notifications.

    Assist-compatible semantics:
      - If spec.answers is provided:
          * terminal is button press (choice-mode)
          * returns id=<answer.id>, sentence=<button label>
          * slots comes from Answer.slot_bindings for the selected option
      - If spec.answers is None:
          * reply-mode (free-form)
          * collect 0..N replies via REPLY_<tag>
          * terminal is DONE_<tag>
          * returns id=None, sentence=<last reply or "">
          * slots is ALWAYS {}
      - All transport/UI data goes under top-level 'meta' (NOT in slots).
    """
    tag = uuid.uuid4().hex
    session = _Session(tag=tag, t_sent=time.time())

    has_answers = bool(spec.answers)
    reply_mode = not has_answers  # Assist: no answers => id=None; free-form

    # Build actions
    actions: list[Dict[str, Any]] = []
    answer_title: Dict[str, str] = {}
    answer_slot_bindings: Dict[str, Dict[str, Any]] = {}

    if has_answers:
        for a in spec.answers or []:
            title = a.title or a.id
            answer_title[a.id] = title
            answer_slot_bindings[a.id] = dict(a.slot_bindings or {})
            actions.append({"action": f"OPT_{tag}_{a.id}", "title": title})

    if spec.allow_replies:
        actions.append({"action": f"REPLY_{tag}", "title": "Reply", "behavior": "textInput"})

    # Mobile UX boundary condition: in reply-mode the notification only disappears
    # when user presses a button; so we provide DONE.
    if reply_mode and spec.expect_reply:
        actions.append({"action": f"DONE_{tag}", "title": "Done"})

    payload: Dict[str, Any] = {"message": spec.question, "data": {"tag": tag, "actions": actions}}
    if spec.title:
        payload["title"] = spec.title

    ok, err = call_service_no_response(client, "notify", notify_service, **payload)
    if not ok:
        return {
            "id": None,
            "sentence": None,
            "slots": {},
            "meta": {"channel": "mobile", "tag": tag, "notify_service": notify_service},
            "error": f"send_failed: {err}",
        }

    deadline = time.time() + spec.timeout_s

    with ws.listen_events("mobile_app_notification_action") as events:
        for ev in events:
            if time.time() >= deadline:
                return {
                    "id": None,
                    "sentence": None,
                    "slots": {},
                    "meta": {
                        "channel": "mobile",
                        "mode": "reply" if reply_mode else "choice",
                        "tag": tag,
                        "notify_service": notify_service,
                        "device_id": session.device_id,
                        "replies": session.replies,
                        "events": session.events,
                        "timed_out": True,
                    },
                    "error": ERR_TIMEOUT,
                }

            data = _extract_data(_to_dict(ev))
            ev_tag = data.get("tag")
            action = data.get("action")

            # Primary correlation: tag equality
            # Secondary correlation: action suffix match (older patterns)
            if ev_tag != tag:
                if not (isinstance(action, str) and action.endswith("_" + tag)):
                    continue

            if session.device_id is None and isinstance(data.get("device_id"), str):
                session.device_id = data["device_id"]

            session.events.append(data)

            # Accumulate reply texts (0..N), even in choice-mode (before button press)
            rt = data.get("reply_text")
            if spec.allow_replies and isinstance(rt, str) and rt.strip():
                if session.t_first_reply is None:
                    session.t_first_reply = time.time()
                session.replies.append(rt.strip())

            if not isinstance(action, str):
                continue

            # Terminal: option selected (choice-mode)
            if action.startswith(f"OPT_{tag}_"):
                answer_id = action.split("_", 2)[2]
                session.t_done = time.time()
                slot_bindings = answer_slot_bindings.get(answer_id, {})
                slot_evidence = {
                    slot_name: {
                        "source": "answer.slot_bindings",
                        "answer_id": answer_id,
                        "tag": tag,
                    }
                    for slot_name in slot_bindings
                }
                return {
                    "id": answer_id,
                    "sentence": answer_title.get(answer_id, answer_id),
                    "slots": slot_bindings,
                    "meta": {
                        "channel": "mobile",
                        "mode": "choice",
                        "tag": tag,
                        "ask_session_id": tag,
                        "slot_evidence": slot_evidence,
                        "notify_service": notify_service,
                        "device_id": session.device_id,
                        "replies": session.replies,
                        "action": action,
                        "t_sent": session.t_sent,
                        "t_first_reply": session.t_first_reply,
                        "t_done": session.t_done,
                        "events": session.events,
                    },
                    "error": None,
                }

            # Terminal: reply-mode completed
            if action == f"DONE_{tag}":
                sentence = session.replies[-1] if session.replies else ""
                session.t_done = time.time()
                return {
                    "id": None,
                    "sentence": sentence,
                    "slots": {},
                    "meta": {
                        "channel": "mobile",
                        "mode": "reply",
                        "tag": tag,
                        "ask_session_id": tag,
                        "slot_evidence": {},
                        "notify_service": notify_service,
                        "device_id": session.device_id,
                        "replies": session.replies,
                        "action": action,
                        "t_sent": session.t_sent,
                        "t_first_reply": session.t_first_reply,
                        "t_done": session.t_done,
                        "events": session.events,
                    },
                    "error": None,
                }

    # If the context manager closes without returning, treat as timeout-ish
    return {
        "id": None,
        "sentence": None,
        "slots": {},
        "meta": {"channel": "mobile", "tag": tag, "notify_service": notify_service},
        "error": ERR_TIMEOUT,
    }
