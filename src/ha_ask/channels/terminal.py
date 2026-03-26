from __future__ import annotations

from typing import Callable, Sequence

from ..errors import ERR_CANCELLED
from ..types import Answer, AskResult, AskSpec

_CANCEL_TOKENS = {"\x1b", "esc", "escape"}


def _normalize_text(raw: str | None) -> str:
    if raw is None:
        return ""
    return raw.strip().lower()


def _is_cancel_input(raw: str | None) -> bool:
    return _normalize_text(raw) in _CANCEL_TOKENS


def _cancel_result(spec: AskSpec) -> AskResult:
    return {
        "id": None,
        "sentence": None,
        "slots": {},
        "meta": {"channel": "terminal", "question": spec.question},
        "error": ERR_CANCELLED,
    }


def _ok_result(spec: AskSpec, *, answer_id: str | None, sentence: str, slots: dict) -> AskResult:
    return {
        "id": answer_id,
        "sentence": sentence,
        "slots": slots,
        "meta": {"channel": "terminal", "question": spec.question},
        "error": None,
    }


def _render_choice_prompt(spec: AskSpec, answers: Sequence[Answer]) -> str:
    lines = [spec.question]
    for idx, answer in enumerate(answers, start=1):
        label = answer.title or answer.id
        lines.append(f"  {idx}) {label}")
    lines.append("Type option number, id, label/title, or alias: ")
    return "\n".join(lines)


def _build_choice_lookup(answers: Sequence[Answer]) -> dict[str, int]:
    lookup: dict[str, int] = {}
    for idx, answer in enumerate(answers):
        candidates: list[str] = [answer.id]
        if answer.title:
            candidates.append(answer.title)
        candidates.extend(answer.sentences)

        for candidate in candidates:
            normalized = _normalize_text(candidate)
            if normalized and normalized not in lookup:
                lookup[normalized] = idx

        option_number = str(idx + 1)
        if option_number not in lookup:
            lookup[option_number] = idx

    return lookup


def _ask_freeform(spec: AskSpec, input_fn: Callable[[str], str]) -> AskResult:
    prompt = f"{spec.question} "
    text = input_fn(prompt)
    if _is_cancel_input(text):
        return _cancel_result(spec)
    return _ok_result(spec, answer_id=None, sentence=text, slots={})


def _ask_multichoice(spec: AskSpec, input_fn: Callable[[str], str], answers: Sequence[Answer]) -> AskResult:
    prompt = _render_choice_prompt(spec, answers)
    lookup = _build_choice_lookup(answers)

    while True:
        raw = input_fn(prompt)
        if _is_cancel_input(raw):
            return _cancel_result(spec)

        normalized = _normalize_text(raw)
        matched_index = lookup.get(normalized)
        if matched_index is None:
            prompt = "Invalid choice. Try again (or type 'esc' to cancel): "
            continue

        answer = answers[matched_index]
        sentence = raw
        return _ok_result(
            spec,
            answer_id=answer.id,
            sentence=sentence,
            slots=dict(answer.slot_bindings or {}),
        )


def ask_question(spec: AskSpec, input_fn: Callable[[str], str] = input) -> AskResult:
    try:
        if spec.answers:
            return _ask_multichoice(spec, input_fn, spec.answers)
        return _ask_freeform(spec, input_fn)
    except KeyboardInterrupt:
        return _cancel_result(spec)
