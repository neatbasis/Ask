from __future__ import annotations

import pytest

from ha_ask.channels import terminal
from ha_ask.errors import ERR_CANCELLED, error_kind, is_cancelled, is_other_error
from ha_ask.types import AskSpec


def _result(channel: str, error: str | None):
    return {"id": None, "sentence": None, "slots": {}, "meta": {"channel": channel}, "error": error}


def test_error_kind_classifies_cancelled_as_canonical() -> None:
    assert error_kind(ERR_CANCELLED) == ERR_CANCELLED


def test_other_error_helper_does_not_treat_cancelled_as_other() -> None:
    assert is_other_error(_result("terminal", ERR_CANCELLED)) is False


@pytest.mark.parametrize("channel", ["terminal", "mobile", "discord", "satellite"])
def test_is_cancelled_helper_is_channel_agnostic(channel: str) -> None:
    assert is_cancelled(_result(channel, ERR_CANCELLED)) is True


def test_terminal_keyboard_interrupt_returns_canonical_cancelled_error() -> None:
    spec = AskSpec(question="Proceed?")

    def raise_ctrl_c(_: str) -> str:
        raise KeyboardInterrupt()

    result = terminal.ask_question(spec, input_fn=raise_ctrl_c)

    assert result["error"] == ERR_CANCELLED


@pytest.mark.parametrize("token", ["\x1b", "esc", "ESC", " escape "])
def test_terminal_escape_tokens_return_canonical_cancelled_error(token: str) -> None:
    spec = AskSpec(question="Proceed?")

    result = terminal.ask_question(spec, input_fn=lambda _: token)

    assert result["error"] == ERR_CANCELLED
