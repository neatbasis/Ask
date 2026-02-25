# ha_ask/types.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, TypedDict


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


Choice = Answer  # optional backwards alias


@dataclass(frozen=True)
class AskSpec:
    question: str
    answers: Optional[Sequence[Answer]] = None

    # Mobile behavior
    expect_reply: bool = False
    allow_replies: bool = True

    timeout_s: float = 180.0
    title: Optional[str] = None
    
# ---------------------------------------------------------
# Result helpers (channel-agnostic semantics)
# ---------------------------------------------------------
# Known semantic errors (cross-channel)

