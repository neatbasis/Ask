from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .types import AskSpec, ChoiceEvidenceRecord, ReplyEvidenceRecord


@dataclass(frozen=True)
class EvidenceContext:
    field_path: str
    channel: str
    question_text: str
    ask_session_id: str
    asked_at: str
    answered_at: str


@dataclass(frozen=True)
class ChoiceEvidence:
    field_path: str
    source: str
    channel: str
    question_text: str
    answer_id: str | None
    answer_text: str | None
    slot_binding: dict[str, Any]
    ask_session_id: str
    asked_at: str
    answered_at: str


@dataclass(frozen=True)
class ReplyEvidence:
    field_path: str
    source: str
    channel: str
    question_text: str
    raw_reply: str
    parsed_value: Any
    parse_status: str
    ask_session_id: str
    asked_at: str
    answered_at: str


REQUIRED_EVIDENCE_KEYS_BY_FIELD: dict[str, set[str]] = {
    "consent_to_contact": {
        "field_path",
        "source",
        "channel",
        "question_text",
        "answer_id",
        "answer_text",
        "slot_binding",
        "ask_session_id",
        "asked_at",
        "answered_at",
    },
    "preferred_contact_method": {
        "field_path",
        "source",
        "channel",
        "question_text",
        "answer_id",
        "answer_text",
        "slot_binding",
        "ask_session_id",
        "asked_at",
        "answered_at",
    },
    "timezone": {
        "field_path",
        "source",
        "channel",
        "question_text",
        "raw_reply",
        "parsed_value",
        "parse_status",
        "ask_session_id",
        "asked_at",
        "answered_at",
    },
}


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
    evidence = ChoiceEvidence(
        field_path=field_path,
        source="ask_session",
        channel=channel,
        question_text=question_text,
        answer_id=answer_id,
        answer_text=answer_text,
        slot_binding=dict(slot_binding),
        ask_session_id=ask_session_id,
        asked_at=asked_at,
        answered_at=answered_at,
    )
    return asdict(evidence)


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
    evidence = ReplyEvidence(
        field_path=field_path,
        source="ask_session",
        channel=channel,
        question_text=question_text,
        raw_reply=raw_reply,
        parsed_value=parsed_value,
        parse_status=status,
        ask_session_id=ask_session_id,
        asked_at=asked_at,
        answered_at=answered_at,
    )
    return asdict(evidence)


def build_choice_evidence_for_apply(
    *,
    context: EvidenceContext,
    ask_spec: AskSpec,
    ask_result: Mapping[str, Any],
    resolved_values: Mapping[str, Any],
) -> ChoiceEvidenceRecord:
    matched_id = ask_result.get("id") if isinstance(ask_result.get("id"), str) else None
    answer_text = None
    if matched_id:
        for answer in ask_spec.answers or ():
            if answer.id == matched_id:
                answer_text = answer.title
                break

    return build_choice_evidence(
        field_path=context.field_path,
        channel=context.channel,
        question_text=context.question_text,
        answer_id=matched_id,
        answer_text=answer_text,
        slot_binding=resolved_values,
        ask_session_id=context.ask_session_id,
        asked_at=context.asked_at,
        answered_at=context.answered_at,
    )


def build_reply_evidence_for_apply(
    *,
    context: EvidenceContext,
    raw_reply: str,
    parsed_value: Any,
    parse_status: str,
) -> ReplyEvidenceRecord:
    return build_reply_evidence(
        field_path=context.field_path,
        channel=context.channel,
        question_text=context.question_text,
        raw_reply=raw_reply,
        parsed_value=parsed_value,
        parse_status=parse_status,
        ask_session_id=context.ask_session_id,
        asked_at=context.asked_at,
        answered_at=context.answered_at,
    )


__all__ = [
    "ChoiceEvidence",
    "EvidenceContext",
    "REQUIRED_EVIDENCE_KEYS_BY_FIELD",
    "ReplyEvidence",
    "build_choice_evidence",
    "build_choice_evidence_for_apply",
    "build_reply_evidence",
    "build_reply_evidence_for_apply",
]
