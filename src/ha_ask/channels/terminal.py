from __future__ import annotations

from collections.abc import Callable, Sequence

from ..errors import ERR_CANCELLED
from ..interaction_types import InteractionMode, SlotSpec, ask_spec_to_interaction
from ..types import Answer, AskResult, AskSpec
from .terminal_ui import TerminalUIUnavailable, select_answer_interactive

_CANCEL_TOKENS = {"\x1b", "esc", "escape"}


InteractiveSelector = Callable[[str, Sequence[Answer]], Answer | None]


def _normalize_text(raw: str | None) -> str:
    if raw is None:
        return ""
    return raw.strip().lower()


def _is_cancel_input(raw: str | None) -> bool:
    return _normalize_text(raw) in _CANCEL_TOKENS


def _label(answer: Answer) -> str:
    return answer.title or answer.id


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
        lines.append(f"  {idx}) {_label(answer)}")
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


def _slot_prompt(slot: SlotSpec) -> str:
    slot_name = slot.name.replace("_", " ").strip().title()
    if slot.description:
        return f"{slot_name} ({slot.description}): "
    return f"{slot_name}: "


def _required_slots(slots: Sequence[SlotSpec]) -> list[SlotSpec]:
    return [slot for slot in slots if slot.required]


def _collect_slots(
    input_fn: Callable[[str], str],
    slots: Sequence[SlotSpec],
    *,
    initial_slots: dict[str, object] | None = None,
) -> tuple[dict[str, object], bool]:
    collected: dict[str, object] = dict(initial_slots or {})
    for slot in _required_slots(slots):
        if slot.name in collected:
            continue
        raw = input_fn(_slot_prompt(slot))
        if _is_cancel_input(raw):
            return collected, False
        collected[slot.name] = raw
    return collected, True


def _sentence_from_slots(slots: dict[str, object]) -> str:
    return ", ".join(f"{key}={value}" for key, value in slots.items())


def _ask_multichoice(
    spec: AskSpec,
    input_fn: Callable[[str], str],
    answers: Sequence[Answer],
    *,
    interactive_selector: InteractiveSelector = select_answer_interactive,
    prefer_interactive: bool = True,
) -> AskResult:
    if prefer_interactive and input_fn is input:
        try:
            selected = interactive_selector(spec.question, answers)
            if selected is None:
                return _cancel_result(spec)
            return _ok_result(
                spec,
                answer_id=selected.id,
                sentence=_label(selected),
                slots=dict(selected.slot_bindings or {}),
            )
        except TerminalUIUnavailable:
            pass

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
        return _ok_result(
            spec,
            answer_id=answer.id,
            sentence=raw,
            slots=dict(answer.slot_bindings or {}),
        )


def _ask_slot_collection(
    spec: AskSpec,
    interaction_slots: Sequence[SlotSpec],
    input_fn: Callable[[str], str],
    *,
    answer_id: str | None = None,
    sentence: str | None = None,
    initial_slots: dict[str, object] | None = None,
) -> AskResult:
    collected_slots, completed = _collect_slots(
        input_fn,
        interaction_slots,
        initial_slots=initial_slots,
    )
    if not completed:
        return _cancel_result(spec)

    result_sentence = sentence
    if result_sentence is None:
        result_sentence = _sentence_from_slots(collected_slots)

    return _ok_result(
        spec,
        answer_id=answer_id,
        sentence=result_sentence,
        slots=collected_slots,
    )


def ask_question(
    spec: AskSpec,
    input_fn: Callable[[str], str] = input,
    *,
    interactive_selector: InteractiveSelector = select_answer_interactive,
    prefer_interactive: bool = True,
) -> AskResult:
    try:
        interaction = ask_spec_to_interaction(spec)

        if interaction.mode == InteractionMode.CHOICE and interaction.choices:
            choice_result = _ask_multichoice(
                spec,
                input_fn,
                interaction.choices,
                interactive_selector=interactive_selector,
                prefer_interactive=prefer_interactive,
            )
            if choice_result["error"] is not None:
                return choice_result

            if _required_slots(interaction.slots):
                return _ask_slot_collection(
                    spec,
                    interaction.slots,
                    input_fn,
                    answer_id=choice_result["id"],
                    sentence=choice_result["sentence"],
                    initial_slots=choice_result["slots"],
                )

            return choice_result

        if _required_slots(interaction.slots):
            return _ask_slot_collection(spec, interaction.slots, input_fn)

        # Terminal starts with a small subset of the richer model.
        # Other modes can be added incrementally without changing AskResult.
        return _ask_freeform(spec, input_fn)
    except KeyboardInterrupt:
        return _cancel_result(spec)
