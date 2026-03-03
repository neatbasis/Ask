from __future__ import annotations

from typing import Any, Mapping

from .types import ChoiceEvidenceRecord, ReplyEvidenceRecord


def build_choice_evidence(
    *,
    field_path: str,
    channel: str,
    question_text: str,
    answer_id: str | None,
    answer_text: str | None,
    slot_binding: Mapping[str, Any],
    ask_session_id: str,
    asked_at: str,
    answered_at: str,
) -> ChoiceEvidenceRecord:
    return {
        "field_path": field_path,
        "source": "ask_session",
        "channel": channel,
        "question_text": question_text,
        "answer_id": answer_id,
        "answer_text": answer_text,
        "slot_binding": dict(slot_binding),
        "ask_session_id": ask_session_id,
        "asked_at": asked_at,
        "answered_at": answered_at,
    }


def build_reply_evidence(
    *,
    field_path: str,
    channel: str,
    question_text: str,
    raw_reply: str,
    parsed_value: Any,
    parse_status: str,
    ask_session_id: str,
    asked_at: str,
    answered_at: str,
) -> ReplyEvidenceRecord:
    status = "success" if parse_status == "success" else "failed"
    return {
        "field_path": field_path,
        "source": "ask_session",
        "channel": channel,
        "question_text": question_text,
        "raw_reply": raw_reply,
        "parsed_value": parsed_value,
        "parse_status": status,
        "ask_session_id": ask_session_id,
        "asked_at": asked_at,
        "answered_at": answered_at,
    }


__all__ = ["build_choice_evidence", "build_reply_evidence"]
