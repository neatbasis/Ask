from __future__ import annotations

from ha_ask.interaction_types import (
    AnswerTemplate,
    InteractionMode,
    InteractionSpec,
    SlotSpec,
    ask_spec_to_interaction,
    choice_spec_to_interaction,
    freeform_spec_to_interaction,
)
from ha_ask.types import Answer, AskSpec, ChoiceSpec, FreeformSpec


def test_interaction_mode_values_are_stable() -> None:
    assert InteractionMode.FREEFORM.value == "freeform"
    assert InteractionMode.CHOICE.value == "choice"
    assert InteractionMode.TEMPLATE_FILL.value == "template_fill"
    assert InteractionMode.MIXED.value == "mixed"


def test_slot_spec_constructs_with_defaults() -> None:
    slot = SlotSpec(name="artist")

    assert slot.name == "artist"
    assert slot.description is None
    assert slot.required is True
    assert slot.multi is False


def test_answer_template_constructs_with_optional_fields() -> None:
    template = AnswerTemplate(
        id="play_album",
        sentences=("play {album} by {artist}",),
        label="Play album",
        slot_bindings={"media_type": "album"},
    )

    assert template.id == "play_album"
    assert template.label == "Play album"
    assert template.slot_bindings == {"media_type": "album"}


def test_interaction_spec_constructs_choice_shape() -> None:
    spec = InteractionSpec(
        id="choose",
        prompt="Choose one",
        mode=InteractionMode.CHOICE,
        choices=(Answer(id="yes", sentences=("yes",)),),
        timeout_seconds=30,
    )

    assert spec.mode == InteractionMode.CHOICE
    assert spec.prompt == "Choose one"
    assert spec.choices[0].id == "yes"
    assert spec.timeout_seconds == 30


def test_choice_spec_maps_to_choice_interaction_spec() -> None:
    spec = ChoiceSpec(
        question="Pick",
        answers=(Answer(id="a", sentences=("alpha",)),),
        timeout_s=42,
    )

    mapped = choice_spec_to_interaction(spec)

    assert mapped.mode == InteractionMode.CHOICE
    assert mapped.prompt == "Pick"
    assert tuple(answer.id for answer in mapped.choices) == ("a",)
    assert mapped.timeout_seconds == 42


def test_freeform_spec_maps_to_freeform_interaction_spec() -> None:
    spec = FreeformSpec(question="What next?", expected_slots=("artist",), timeout_s=99)

    mapped = freeform_spec_to_interaction(spec)

    assert mapped.mode == InteractionMode.FREEFORM
    assert mapped.prompt == "What next?"
    assert mapped.choices == ()
    assert tuple(slot.name for slot in mapped.slots) == ("artist",)
    assert mapped.timeout_seconds == 99


def test_askspec_with_answers_maps_conservatively_to_choice() -> None:
    spec = AskSpec(
        question="Pick",
        answers=(Answer(id="yes", sentences=("yes",)),),
        expected_slots=("consent",),
    )

    mapped = ask_spec_to_interaction(spec)

    assert mapped.mode == InteractionMode.CHOICE
    assert mapped.choices[0].id == "yes"
    assert tuple(slot.name for slot in mapped.slots) == ("consent",)


def test_askspec_without_answers_maps_conservatively_to_freeform() -> None:
    spec = AskSpec(question="Tell me more", expect_reply=True)

    mapped = ask_spec_to_interaction(spec)

    assert mapped.mode == InteractionMode.FREEFORM
    assert mapped.choices == ()
