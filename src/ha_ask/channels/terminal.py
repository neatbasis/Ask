from __future__ import annotations

from typing import Callable

from ..errors import ERR_CANCELLED
from ..types import AskResult, AskSpec

_CANCEL_TOKENS = {"\x1b", "esc", "escape"}


def _is_cancel_input(raw: str | None) -> bool:
    if raw is None:
        return False
    return raw.strip().lower() in _CANCEL_TOKENS


def _cancel_result(spec: AskSpec) -> AskResult:
    return {
        "id": None,
        "sentence": None,
        "slots": {},
        "meta": {"channel": "terminal", "question": spec.question},
        "error": ERR_CANCELLED,
    }


def ask_question(spec: AskSpec, input_fn: Callable[[str], str] = input) -> AskResult:
    prompt = f"{spec.question} "

    try:
        text = input_fn(prompt)
    except KeyboardInterrupt:
        return _cancel_result(spec)

    if _is_cancel_input(text):
        return _cancel_result(spec)

    return {
        "id": None,
        "sentence": text,
        "slots": {},
        "meta": {"channel": "terminal", "question": spec.question},
        "error": None,
    }
