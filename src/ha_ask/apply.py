from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypedDict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ParseStatus = Literal["not_applicable", "success", "invalid", "missing"]


class TimezoneParseResult(TypedDict):
    parse_status: Literal["success", "invalid", "missing"]
    parsed_value: str | None


class FieldApplicationResult(TypedDict):
    resolved_fields: list[str]
    parse_status: ParseStatus
    applied_values: dict[str, Any]
    evidence_fragments: dict[str, dict[str, Any]]


_DEFAULT_CANONICAL_MAPPINGS: dict[str, dict[str, Any]] = {
    "consent_to_contact": {
        "consent_yes": True,
        "consent_no": False,
    },
    "preferred_contact_method": {
        "contact_sms": "sms",
        "contact_email": "email",
        "contact_phone": "phone",
    },
}


def _collect_slots(ask_result: Mapping[str, Any]) -> dict[str, Any]:
    slots = ask_result.get("slots")
    if not isinstance(slots, Mapping):
        return {}
    return {str(k): v for k, v in slots.items()}


def _extract_reply_text(ask_result: Mapping[str, Any]) -> str:
    sentence = ask_result.get("sentence")
    if isinstance(sentence, str) and sentence.strip():
        return sentence.strip()

    meta = ask_result.get("meta")
    if isinstance(meta, Mapping):
        replies = meta.get("replies")
        if isinstance(replies, list):
            for item in reversed(replies):
                if isinstance(item, str) and item.strip():
                    return item.strip()
    return ""


def parse_timezone_reply(reply_text: str | None) -> TimezoneParseResult:
    if not isinstance(reply_text, str) or not reply_text.strip():
        return {"parse_status": "missing", "parsed_value": None}

    candidate = reply_text.strip()
    try:
        ZoneInfo(candidate)
    except ZoneInfoNotFoundError:
        return {"parse_status": "invalid", "parsed_value": None}

    return {"parse_status": "success", "parsed_value": candidate}


def _canonical_mappings(mapping_config: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    configured = mapping_config.get("canonical_mappings") if isinstance(mapping_config, Mapping) else None
    if not isinstance(configured, Mapping):
        return {k: dict(v) for k, v in _DEFAULT_CANONICAL_MAPPINGS.items()}

    merged = {k: dict(v) for k, v in _DEFAULT_CANONICAL_MAPPINGS.items()}
    for field_path, field_map in configured.items():
        if isinstance(field_path, str) and isinstance(field_map, Mapping):
            merged[field_path] = {str(answer_id): value for answer_id, value in field_map.items()}
    return merged


def apply_answer_to_field(
    field_path: str,
    ask_result: Mapping[str, Any],
    mapping_config: Mapping[str, Any] | None,
) -> FieldApplicationResult:
    resolved_fields: list[str] = []
    applied_values: dict[str, Any] = {}
    evidence: dict[str, Any] = {}

    answer_id = ask_result.get("id") if isinstance(ask_result.get("id"), str) else None
    mappings = _canonical_mappings(mapping_config)

    if field_path == "timezone":
        raw_reply = _extract_reply_text(ask_result)
        timezone_result = parse_timezone_reply(raw_reply)

        if timezone_result["parse_status"] == "success":
            resolved_fields.append(field_path)
            applied_values[field_path] = timezone_result["parsed_value"]

        evidence = {
            "field_path": field_path,
            "raw_reply": raw_reply,
            "parsed_value": timezone_result["parsed_value"],
            "parse_status": timezone_result["parse_status"],
        }
        return {
            "resolved_fields": resolved_fields,
            "parse_status": timezone_result["parse_status"],
            "applied_values": applied_values,
            "evidence_fragments": {field_path: evidence},
        }

    mapped_value: Any = None
    mapping_source = "unresolved"

    if answer_id and field_path in mappings and answer_id in mappings[field_path]:
        mapped_value = mappings[field_path][answer_id]
        mapping_source = "canonical_answer_id"
    else:
        slots = _collect_slots(ask_result)
        if field_path in slots:
            mapped_value = slots[field_path]
            mapping_source = "slot_binding"

    if mapping_source != "unresolved":
        resolved_fields.append(field_path)
        applied_values[field_path] = mapped_value

    evidence = {
        "field_path": field_path,
        "answer_id": answer_id,
        "mapped_value": mapped_value,
        "mapping_source": mapping_source,
    }

    return {
        "resolved_fields": resolved_fields,
        "parse_status": "not_applicable",
        "applied_values": applied_values,
        "evidence_fragments": {field_path: evidence},
    }


__all__ = ["FieldApplicationResult", "TimezoneParseResult", "apply_answer_to_field", "parse_timezone_reply"]
