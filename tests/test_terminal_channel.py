from __future__ import annotations

from collections.abc import Iterator

from ha_ask.channels import terminal
from ha_ask.channels.terminal_ui import TerminalUIUnavailable
from ha_ask.errors import ERR_CANCELLED
from ha_ask.interaction_types import AnswerTemplate, InteractionMode, InteractionSpec, SlotSpec
from ha_ask.types import Answer, AskSpec


def _iter_input(values: list[str]):
    it: Iterator[str] = iter(values)

    def _input(_: str) -> str:
        return next(it)

    return _input


def _choice_spec() -> AskSpec:
    return AskSpec(
        question="Choose an option",
        answers=[
            Answer(
                id="yes",
                title="Yes please",
                sentences=["yes", "affirmative", "go ahead"],
                slot_bindings={"consent_to_contact": True},
            ),
            Answer(
                id="no",
                title="No thanks",
                sentences=["no", "negative"],
                slot_bindings={"consent_to_contact": False},
            ),
        ],
    )


def test_terminal_freeform_typed_text_returns_success() -> None:
    spec = AskSpec(question="What should we do next?")

    result = terminal.ask_question(spec, input_fn=lambda _: "Ship it")

    assert result == {
        "id": None,
        "sentence": "Ship it",
        "slots": {},
        "meta": {"channel": "terminal", "question": "What should we do next?"},
        "error": None,
    }


def test_terminal_multichoice_select_by_number_returns_answer_id() -> None:
    result = terminal.ask_question(_choice_spec(), input_fn=lambda _: "2")

    assert result["id"] == "no"
    assert result["error"] is None


def test_terminal_multichoice_select_by_answer_id_returns_answer_id() -> None:
    result = terminal.ask_question(_choice_spec(), input_fn=lambda _: "yes")

    assert result["id"] == "yes"


def test_terminal_multichoice_select_by_title_returns_answer_id() -> None:
    result = terminal.ask_question(_choice_spec(), input_fn=lambda _: "no thanks")

    assert result["id"] == "no"


def test_terminal_multichoice_select_by_alias_sentence_returns_answer_id() -> None:
    result = terminal.ask_question(_choice_spec(), input_fn=lambda _: "Affirmative")

    assert result["id"] == "yes"


def test_terminal_multichoice_invalid_input_retries_until_valid() -> None:
    prompts: list[str] = []

    def _input(prompt: str) -> str:
        prompts.append(prompt)
        return ["not a valid choice", "1"][len(prompts) - 1]

    result = terminal.ask_question(_choice_spec(), input_fn=_input)

    assert result["id"] == "yes"
    assert len(prompts) == 2
    assert "Type option number" in prompts[0]
    assert prompts[1] == "Invalid choice. Try again (or type 'esc' to cancel): "


def test_terminal_multichoice_cancel_token_returns_cancelled() -> None:
    result = terminal.ask_question(_choice_spec(), input_fn=lambda _: "escape")

    assert result["error"] == ERR_CANCELLED


def test_terminal_multichoice_keyboard_interrupt_returns_cancelled() -> None:
    def raise_ctrl_c(_: str) -> str:
        raise KeyboardInterrupt()

    result = terminal.ask_question(_choice_spec(), input_fn=raise_ctrl_c)

    assert result["error"] == ERR_CANCELLED


def test_terminal_multichoice_maps_slot_bindings_to_result_slots() -> None:
    result = terminal.ask_question(_choice_spec(), input_fn=lambda _: "yes")

    assert result["slots"] == {"consent_to_contact": True}


def test_terminal_multichoice_result_shape_is_intact() -> None:
    result = terminal.ask_question(_choice_spec(), input_fn=lambda _: "yes")

    assert set(result.keys()) == {"id", "sentence", "slots", "meta", "error"}
    assert result["meta"]["channel"] == "terminal"


def test_terminal_freeform_escape_returns_cancelled() -> None:
    spec = AskSpec(question="Proceed?")

    result = terminal.ask_question(spec, input_fn=lambda _: " esc ")

    assert result["error"] == ERR_CANCELLED


def test_terminal_freeform_keyboard_interrupt_returns_cancelled() -> None:
    spec = AskSpec(question="Proceed?")

    def raise_ctrl_c(_: str) -> str:
        raise KeyboardInterrupt()

    result = terminal.ask_question(spec, input_fn=raise_ctrl_c)

    assert result["error"] == ERR_CANCELLED


def test_terminal_multichoice_interactive_selection_returns_selected_id_and_slots() -> None:
    spec = _choice_spec()

    def _select(_: str, answers: tuple[Answer, ...] | list[Answer]) -> Answer | None:
        return answers[1]

    result = terminal.ask_question(spec, interactive_selector=_select)

    assert result["id"] == "no"
    assert result["sentence"] == "No thanks"
    assert result["slots"] == {"consent_to_contact": False}


def test_terminal_multichoice_interactive_cancel_returns_cancelled() -> None:
    result = terminal.ask_question(_choice_spec(), interactive_selector=lambda *_: None)

    assert result["error"] == ERR_CANCELLED


def test_terminal_multichoice_interactive_unavailable_falls_back_to_typed() -> None:
    def _unavailable(*_: object) -> Answer | None:
        raise TerminalUIUnavailable("no tty")

    result = terminal.ask_question(
        _choice_spec(),
        input_fn=lambda _: "1",
        interactive_selector=_unavailable,
    )

    assert result["id"] == "yes"


def test_terminal_slot_collection_prompts_required_slots_in_order() -> None:
    spec = AskSpec(question="Tell me what to play", expected_slots=["album", "artist"])
    prompts: list[str] = []

    def _input(prompt: str) -> str:
        prompts.append(prompt)
        return ["The White Album", "The Beatles"][len(prompts) - 1]

    result = terminal.ask_question(spec, input_fn=_input)

    assert prompts == ["Album: ", "Artist: "]
    assert result["id"] is None
    assert result["slots"] == {"album": "The White Album", "artist": "The Beatles"}
    assert result["meta"]["channel"] == "terminal"


def test_terminal_slot_collection_cancel_token_returns_cancelled() -> None:
    spec = AskSpec(question="Tell me what to play", expected_slots=["album", "artist"])

    result = terminal.ask_question(spec, input_fn=_iter_input(["The White Album", "esc"]))

    assert result["error"] == ERR_CANCELLED


def test_terminal_slot_collection_keyboard_interrupt_returns_cancelled() -> None:
    spec = AskSpec(question="Tell me what to play", expected_slots=["album", "artist"])

    def _input(prompt: str) -> str:
        if prompt == "Album: ":
            return "The White Album"
        raise KeyboardInterrupt()

    result = terminal.ask_question(spec, input_fn=_input)

    assert result["error"] == ERR_CANCELLED


def test_terminal_choice_then_collects_remaining_required_slots() -> None:
    spec = AskSpec(
        question="What should we play?",
        expected_slots=["album", "artist"],
        answers=[
            Answer(
                id="white_album",
                title="The White Album",
                sentences=["white album"],
                slot_bindings={"album": "The White Album"},
            ),
            Answer(
                id="abbey_road",
                title="Abbey Road",
                sentences=["abbey road"],
                slot_bindings={"album": "Abbey Road"},
            ),
        ],
    )
    prompts: list[str] = []

    def _input(prompt: str) -> str:
        prompts.append(prompt)
        return ["1", "The Beatles"][len(prompts) - 1]

    result = terminal.ask_question(
        spec,
        input_fn=_input,
        prefer_interactive=False,
    )

    assert result["id"] == "white_album"
    assert result["sentence"] == "album=The White Album, artist=The Beatles"
    assert result["slots"] == {"album": "The White Album", "artist": "The Beatles"}
    assert prompts == [
        "What should we play?\n  1) The White Album\n  2) Abbey Road\nType option number, id, label/title, or alias: ",
        "Artist: ",
    ]
    assert prompts[1] == "Artist: "


def test_terminal_choice_slot_bindings_do_not_reprompt_satisfied_required_slot() -> None:
    spec = AskSpec(
        question="What should we deploy?",
        expected_slots=["action", "service", "version"],
        answers=[
            Answer(
                id="deploy",
                title="Deploy",
                sentences=["deploy"],
                slot_bindings={"action": "deploy"},
            )
        ],
    )
    prompts: list[str] = []

    def _input(prompt: str) -> str:
        prompts.append(prompt)
        return ["1", "api", "2026.03.0"][len(prompts) - 1]

    result = terminal.ask_question(spec, input_fn=_input, prefer_interactive=False)

    assert result["id"] == "deploy"
    assert result["slots"] == {"action": "deploy", "service": "api", "version": "2026.03.0"}
    assert prompts == [
        "What should we deploy?\n  1) Deploy\nType option number, id, label/title, or alias: ",
        "Service: ",
        "Version: ",
    ]


def test_terminal_choice_then_slot_collection_cancel_returns_cancelled() -> None:
    spec = AskSpec(
        question="What should we deploy?",
        expected_slots=["action", "service", "version"],
        answers=[
            Answer(
                id="deploy",
                title="Deploy",
                sentences=["deploy"],
                slot_bindings={"action": "deploy"},
            )
        ],
    )

    result = terminal.ask_question(
        spec,
        input_fn=_iter_input(["1", "api", "esc"]),
        prefer_interactive=False,
    )

    assert result["error"] == ERR_CANCELLED
    assert result["id"] is None
    assert result["slots"] == {}


def test_terminal_slot_collection_shows_template_hint_and_renders_sentence(monkeypatch) -> None:
    spec = AskSpec(question="Tell me what to play", expected_slots=["album", "artist"])
    prompts: list[str] = []

    def _input(prompt: str) -> str:
        prompts.append(prompt)
        return ["The White Album", "The Beatles"][len(prompts) - 1]

    interaction = InteractionSpec(
        id="template-fill",
        prompt=spec.question,
        mode=InteractionMode.TEMPLATE_FILL,
        slots=(SlotSpec(name="album"), SlotSpec(name="artist")),
        templates=(AnswerTemplate(id="play_album", sentences=("play {album} by {artist}",)),),
    )
    monkeypatch.setattr(terminal, "ask_spec_to_interaction", lambda _: interaction)

    result = terminal.ask_question(spec, input_fn=_input)

    assert prompts[0] == "Template: play {album} by {artist}\nAlbum: "
    assert prompts[1] == "Artist: "
    assert result["sentence"] == "play The White Album by The Beatles"


def test_terminal_slot_collection_template_with_missing_slots_uses_fallback_sentence(monkeypatch) -> None:
    spec = AskSpec(question="Tell me what to play", expected_slots=["album", "artist"])

    interaction = InteractionSpec(
        id="template-fill",
        prompt=spec.question,
        mode=InteractionMode.TEMPLATE_FILL,
        slots=(SlotSpec(name="album"), SlotSpec(name="artist")),
        templates=(AnswerTemplate(id="play_album", sentences=("play {album} by {genre}",)),),
    )
    monkeypatch.setattr(terminal, "ask_spec_to_interaction", lambda _: interaction)

    result = terminal.ask_question(
        spec,
        input_fn=_iter_input(["The White Album", "The Beatles"]),
    )

    assert result["sentence"] == "album=The White Album, artist=The Beatles"


def test_terminal_choice_then_slot_collection_renders_sentence_from_template(monkeypatch) -> None:
    spec = AskSpec(
        question="What should we play?",
        answers=[
            Answer(
                id="white_album",
                title="The White Album",
                sentences=["white album"],
                slot_bindings={"album": "The White Album"},
            )
        ],
        expected_slots=["album", "artist"],
    )

    interaction = InteractionSpec(
        id="ask.choice",
        prompt=spec.question,
        mode=InteractionMode.CHOICE,
        choices=tuple(spec.answers or ()),
        slots=(SlotSpec(name="album"), SlotSpec(name="artist")),
        templates=(AnswerTemplate(id="white_album", sentences=("play {album} by {artist}",)),),
    )
    monkeypatch.setattr(terminal, "ask_spec_to_interaction", lambda _: interaction)

    result = terminal.ask_question(
        spec,
        input_fn=_iter_input(["1", "The Beatles"]),
        prefer_interactive=False,
    )

    assert result["id"] == "white_album"
    assert result["slots"] == {"album": "The White Album", "artist": "The Beatles"}
    assert result["sentence"] == "play The White Album by The Beatles"
