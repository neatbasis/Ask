from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from homeassistant_api import Client, WebsocketClient

from ..client import call_service_no_response
from ..config import parse_ha_action
from ..errors import ERR_TIMEOUT
from ..types import AskResult, AskSpec


@dataclass
class _Session:
    tag: str
    t_sent: float
    t_first_reply: Optional[float] = None
    t_done: Optional[float] = None
    replies: list[str] = field(default_factory=list)
    events: list[Dict[str, Any]] = field(default_factory=list)
    user_id: Optional[str] = None


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
    if "data" in evd and isinstance(evd["data"], dict):
        return evd["data"]
    if "event" in evd and isinstance(evd["event"], dict):
        inner = evd["event"]
        if "data" in inner and isinstance(inner["data"], dict):
            return inner["data"]
    if "event_data" in evd and isinstance(evd["event_data"], dict):
        return evd["event_data"]
    return evd if isinstance(evd, dict) else {}


def ask_question(client: Client, ws: WebsocketClient, spec: AskSpec, notify_action: str) -> AskResult:
    tag = uuid.uuid4().hex
    session = _Session(tag=tag, t_sent=time.time())

    has_answers = bool(spec.answers)
    reply_mode = not has_answers

    actions: list[Dict[str, Any]] = []
    answer_title: Dict[str, str] = {}
    answer_slot_bindings: Dict[str, Dict[str, Any]] = {}

    if has_answers:
        for answer in spec.answers or []:
            title = answer.title or answer.id
            answer_title[answer.id] = title
            answer_slot_bindings[answer.id] = dict(answer.slot_bindings or {})
            actions.append({"action": f"OPT_{tag}_{answer.id}", "title": title})

    if spec.allow_replies:
        actions.append({"action": f"REPLY_{tag}", "title": "Reply", "behavior": "textInput"})

    if reply_mode and spec.expect_reply:
        actions.append({"action": f"DONE_{tag}", "title": "Done"})

    payload: Dict[str, Any] = {"message": spec.question, "data": {"tag": tag, "actions": actions}}
    if spec.title:
        payload["title"] = spec.title

    try:
        domain, service = parse_ha_action(notify_action)
    except ValueError as exc:
        return {
            "id": None,
            "sentence": None,
            "slots": {},
            "meta": {"channel": "discord", "tag": tag, "notify_action": notify_action},
            "error": str(exc),
        }

    ok, err = call_service_no_response(client, domain, service, **payload)
    if not ok:
        return {
            "id": None,
            "sentence": None,
            "slots": {},
            "meta": {"channel": "discord", "tag": tag, "notify_action": notify_action},
            "error": f"send_failed: {err}",
        }

    deadline = time.time() + spec.timeout_s
    with ws.listen_events("discord_notification_action") as events:
        for ev in events:
            if time.time() >= deadline:
                return {
                    "id": None,
                    "sentence": None,
                    "slots": {},
                    "meta": {
                        "channel": "discord",
                        "mode": "reply" if reply_mode else "choice",
                        "tag": tag,
                        "notify_action": notify_action,
                        "user_id": session.user_id,
                        "replies": session.replies,
                        "events": session.events,
                        "timed_out": True,
                    },
                    "error": ERR_TIMEOUT,
                }

            data = _extract_data(_to_dict(ev))
            ev_tag = data.get("tag")
            action = data.get("action")
            if ev_tag != tag:
                if not (isinstance(action, str) and action.endswith("_" + tag)):
                    continue

            if session.user_id is None and isinstance(data.get("user_id"), str):
                session.user_id = data["user_id"]

            session.events.append(data)

            reply_text = data.get("reply_text")
            if spec.allow_replies and isinstance(reply_text, str) and reply_text.strip():
                if session.t_first_reply is None:
                    session.t_first_reply = time.time()
                session.replies.append(reply_text.strip())

            if not isinstance(action, str):
                continue

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
                        "channel": "discord",
                        "mode": "choice",
                        "tag": tag,
                        "ask_session_id": tag,
                        "slot_evidence": slot_evidence,
                        "notify_action": notify_action,
                        "user_id": session.user_id,
                        "replies": session.replies,
                        "action": action,
                        "t_sent": session.t_sent,
                        "t_first_reply": session.t_first_reply,
                        "t_done": session.t_done,
                        "events": session.events,
                    },
                    "error": None,
                }

            if action == f"DONE_{tag}":
                sentence = session.replies[-1] if session.replies else ""
                session.t_done = time.time()
                return {
                    "id": None,
                    "sentence": sentence,
                    "slots": {},
                    "meta": {
                        "channel": "discord",
                        "mode": "reply",
                        "tag": tag,
                        "ask_session_id": tag,
                        "slot_evidence": {},
                        "notify_action": notify_action,
                        "user_id": session.user_id,
                        "replies": session.replies,
                        "action": action,
                        "t_sent": session.t_sent,
                        "t_first_reply": session.t_first_reply,
                        "t_done": session.t_done,
                        "events": session.events,
                    },
                    "error": None,
                }

    return {
        "id": None,
        "sentence": None,
        "slots": {},
        "meta": {"channel": "discord", "tag": tag, "notify_action": notify_action},
        "error": ERR_TIMEOUT,
    }
