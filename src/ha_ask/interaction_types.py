from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum

from .types import Answer, AskSpec, ChoiceSpec, FreeformSpec


class InteractionMode(str, Enum):
    """Semantic interaction modes used by Ask orchestration internals."""

    FREEFORM = "freeform"
    CHOICE = "choice"
    TEMPLATE_FILL = "template_fill"
    MIXED = "mixed"


@dataclass(frozen=True)
class SlotSpec:
    """A missing named field that may need to be collected for intent completion."""

    name: str
    description: str | None = None
    required: bool = True
    multi: bool = False


@dataclass(frozen=True)
class AnswerTemplate:
    """A semantic response template, e.g. ``play {album} by {artist}``."""

    id: str
    sentences: Sequence[str]
    label: str | None = None
    slot_bindings: dict[str, object] | None = None


@dataclass(frozen=True)
class InteractionSpec:
    """
    Internal semantic interaction target for Ask.

    This additive seam helps Ask move from "prompt + optional choices" toward
    collecting the missing values needed to complete an intent. Channels can
    support different subsets of these semantics.
    """

    id: str
    prompt: str
    mode: InteractionMode
    slots: Sequence[SlotSpec] = field(default_factory=tuple)
    choices: Sequence[Answer] = field(default_factory=tuple)
    templates: Sequence[AnswerTemplate] = field(default_factory=tuple)
    timeout_seconds: float | None = None


def _map_slots(spec: AskSpec) -> tuple[SlotSpec, ...]:
    if not spec.expected_slots:
        return ()
    return tuple(SlotSpec(name=slot_name) for slot_name in spec.expected_slots)


def choice_spec_to_interaction(spec: ChoiceSpec) -> InteractionSpec:
    return InteractionSpec(
        id="choice",
        prompt=spec.question,
        mode=InteractionMode.CHOICE,
        slots=_map_slots(spec),
        choices=tuple(spec.answers),
        timeout_seconds=spec.timeout_s,
    )


def freeform_spec_to_interaction(spec: FreeformSpec) -> InteractionSpec:
    return InteractionSpec(
        id="freeform",
        prompt=spec.question,
        mode=InteractionMode.FREEFORM,
        slots=_map_slots(spec),
        timeout_seconds=spec.timeout_s,
    )


def ask_spec_to_interaction(spec: AskSpec) -> InteractionSpec:
    """
    Conservative compatibility mapping from current Ask specs.

    - specs with answers map to choice mode
    - reply-oriented/no-answer specs map to freeform mode

    This keeps existing AskSpec/ChoiceSpec/FreeformSpec public usage intact while
    introducing a richer internal semantic center.
    """

    if isinstance(spec, ChoiceSpec):
        return choice_spec_to_interaction(spec)
    if isinstance(spec, FreeformSpec):
        return freeform_spec_to_interaction(spec)

    if spec.answers:
        return InteractionSpec(
            id="ask.choice",
            prompt=spec.question,
            mode=InteractionMode.CHOICE,
            slots=_map_slots(spec),
            choices=tuple(spec.answers),
            timeout_seconds=spec.timeout_s,
        )

    return InteractionSpec(
        id="ask.freeform",
        prompt=spec.question,
        mode=InteractionMode.FREEFORM,
        slots=_map_slots(spec),
        timeout_seconds=spec.timeout_s,
    )
