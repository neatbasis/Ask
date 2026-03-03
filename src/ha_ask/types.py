# ha_ask/types.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Mapping, Optional, Sequence, TypedDict


class AskResult(TypedDict):
    """
    Assist-compatible response contract.

    - id: matching answer id, or None if no match / free-form
    - sentence: recognized user utterance
    - slots: ONLY wildcard {slots} extracted from the matched sentence template
    - meta: transport/UI metadata (channel, tags, device_id, etc.)
    - error: None or error string
    """

    id: Optional[str]
    sentence: Optional[str]
    slots: Dict[str, Any]
    meta: Dict[str, Any]
    error: Optional[str]


@dataclass(frozen=True)
class Answer:
    id: str
    sentences: Sequence[str]
    title: Optional[str] = None
    slot_bindings: Optional[Dict[str, Any]] = None


Choice = Answer  # optional backwards alias


@dataclass(frozen=True)
class AskSpec:
    question: str
    answers: Optional[Sequence[Answer]] = None
    expected_slots: Optional[Sequence[str]] = None
    slot_schema: Optional[Dict[str, Any]] = None

    # Mobile behavior
    expect_reply: bool = False
    allow_replies: bool = True

    timeout_s: float = 180.0
    title: Optional[str] = None


EvidenceSource = Literal["ask_session"]
EvidenceChannel = Literal["mobile", "satellite"] | str


class BaseEvidenceRecord(TypedDict):
    field_path: str
    source: EvidenceSource
    channel: EvidenceChannel
    question_text: str
    ask_session_id: str
    asked_at: str
    answered_at: str


class ChoiceEvidenceRecord(BaseEvidenceRecord):
    answer_id: str | None
    answer_text: str | None
    slot_binding: Mapping[str, Any]


class ReplyEvidenceRecord(BaseEvidenceRecord):
    raw_reply: str
    parsed_value: Any
    parse_status: Literal["success", "failed"]


EvidenceRecord = ChoiceEvidenceRecord | ReplyEvidenceRecord
EvidenceMap = Dict[str, EvidenceRecord]


class AskSessionRecord(TypedDict):
    ask_session_id: str
    channel: str
    prompt: str
    chosen_answer_id: str | None
    sentence: str | None
    replies: list[Any]
    slot_evidence: Mapping[str, Any]
    slots: Dict[str, Any]
    t_sent: Any
    t_first_reply: Any
    t_done: Any
    persisted_at: float


# ---------------------------------------------------------
# Result helpers (channel-agnostic semantics)
# ---------------------------------------------------------
# Known semantic errors (cross-channel)
