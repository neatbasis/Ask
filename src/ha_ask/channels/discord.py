from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from ..errors import ERR_TIMEOUT
from ..types import AskResult, AskSpec


@dataclass(frozen=True)
class DiscordRecipient:
    user_id: int
    channel_id: int | None = None


def _normalize_service_url(service_url: str) -> str:
    trimmed = service_url.strip().rstrip("/")
    if not trimmed:
        raise ValueError("invalid_discord_turn_url:empty")
    if trimmed.endswith("/ask-turn"):
        return trimmed
    return f"{trimmed}/ask-turn"


def _parse_recipient(raw: str) -> DiscordRecipient:
    candidate = raw.strip()
    if not candidate:
        raise ValueError("invalid_discord_recipient:empty")

    if ":" in candidate:
        user_part, channel_part = candidate.split(":", 1)
    else:
        user_part, channel_part = candidate, ""

    try:
        user_id = int(user_part)
    except ValueError as exc:
        raise ValueError("invalid_discord_recipient:user_id") from exc

    if not channel_part:
        return DiscordRecipient(user_id=user_id)

    try:
        channel_id = int(channel_part)
    except ValueError as exc:
        raise ValueError("invalid_discord_recipient:channel_id") from exc

    return DiscordRecipient(user_id=user_id, channel_id=channel_id)


def _build_payload(
    *, correlation_id: str, spec: AskSpec, recipient: DiscordRecipient
) -> dict[str, Any]:
    ask_kind = "multichoice" if spec.answers else "freeform"
    payload: dict[str, Any] = {
        "correlation_id": correlation_id,
        "user_id": recipient.user_id,
        "prompt": spec.question,
        "timeout_seconds": spec.timeout_s,
        "mode": "dm",
        "ask_kind": ask_kind,
    }
    if recipient.channel_id is not None:
        payload["channel_id"] = recipient.channel_id

    if spec.answers:
        payload["choices"] = [
            {
                "key": answer.id,
                "label": answer.title or answer.id,
            }
            for answer in spec.answers
        ]

    return payload


def _map_response(
    *,
    payload: dict[str, Any],
    spec: AskSpec,
    correlation_id: str,
    recipient: DiscordRecipient,
    service_url: str,
) -> AskResult:
    status = payload.get("status")
    response_text = payload.get("response_text")
    selected_choice_key = payload.get("selected_choice_key")

    if status == "timed_out":
        return {
            "id": None,
            "sentence": None,
            "slots": {},
            "meta": {
                "channel": "discord",
                "timed_out": True,
                "status": status,
                "correlation_id": correlation_id,
                "recipient": {
                    "user_id": recipient.user_id,
                    "channel_id": recipient.channel_id,
                },
                "discord_turn_url": service_url,
            },
            "error": ERR_TIMEOUT,
        }

    if status != "answered":
        reason = payload.get("reason")
        error = payload.get("error")
        detail = reason or error or f"unexpected_discord_turn_status:{status}"
        return {
            "id": None,
            "sentence": None,
            "slots": {},
            "meta": {
                "channel": "discord",
                "status": status,
                "correlation_id": correlation_id,
                "recipient": {
                    "user_id": recipient.user_id,
                    "channel_id": recipient.channel_id,
                },
                "discord_turn_url": service_url,
            },
            "error": str(detail),
        }

    answer_slot_bindings = {
        answer.id: dict(answer.slot_bindings or {})
        for answer in (spec.answers or [])
    }
    slot_bindings = answer_slot_bindings.get(selected_choice_key or "", {})
    slot_evidence = {
        slot_name: {
            "source": "answer.slot_bindings",
            "answer_id": selected_choice_key,
            "correlation_id": correlation_id,
        }
        for slot_name in slot_bindings
    }

    return {
        "id": selected_choice_key,
        "sentence": response_text,
        "slots": slot_bindings,
        "meta": {
            "channel": "discord",
            "mode": "choice" if spec.answers else "reply",
            "status": status,
            "correlation_id": correlation_id,
            "recipient": {
                "user_id": recipient.user_id,
                "channel_id": recipient.channel_id,
            },
            "discord_turn_url": service_url,
            "slot_evidence": slot_evidence,
        },
        "error": None,
    }


def ask_question(
    *,
    spec: AskSpec,
    service_url: str,
    recipient: str,
    bearer_token: str | None = None,
) -> AskResult:
    correlation_id = uuid.uuid4().hex

    try:
        endpoint = _normalize_service_url(service_url)
        parsed_recipient = _parse_recipient(recipient)
    except ValueError as exc:
        return {
            "id": None,
            "sentence": None,
            "slots": {},
            "meta": {"channel": "discord", "correlation_id": correlation_id},
            "error": str(exc),
        }

    payload = _build_payload(correlation_id=correlation_id, spec=spec, recipient=parsed_recipient)
    body = json.dumps(payload).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    req = request.Request(endpoint, data=body, headers=headers, method="POST")

    timeout_s = max(float(spec.timeout_s), 0.0) + 5.0
    try:
        with request.urlopen(req, timeout=timeout_s) as resp:
            response_payload = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        return {
            "id": None,
            "sentence": None,
            "slots": {},
            "meta": {
                "channel": "discord",
                "discord_turn_url": endpoint,
                "correlation_id": correlation_id,
                "http_status": exc.code,
            },
            "error": f"discord_turn_http_error:{exc.code}",
        }
    except error.URLError as exc:
        return {
            "id": None,
            "sentence": None,
            "slots": {},
            "meta": {
                "channel": "discord",
                "discord_turn_url": endpoint,
                "correlation_id": correlation_id,
            },
            "error": f"discord_turn_unreachable:{exc.reason}",
        }
    except TimeoutError:
        return {
            "id": None,
            "sentence": None,
            "slots": {},
            "meta": {
                "channel": "discord",
                "discord_turn_url": endpoint,
                "correlation_id": correlation_id,
            },
            "error": ERR_TIMEOUT,
        }
    except json.JSONDecodeError:
        return {
            "id": None,
            "sentence": None,
            "slots": {},
            "meta": {
                "channel": "discord",
                "discord_turn_url": endpoint,
                "correlation_id": correlation_id,
            },
            "error": "discord_turn_invalid_json",
        }

    return _map_response(
        payload=response_payload,
        spec=spec,
        correlation_id=correlation_id,
        recipient=parsed_recipient,
        service_url=endpoint,
    )
