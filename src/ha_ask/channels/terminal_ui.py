from __future__ import annotations

import os
import sys
from collections.abc import Sequence

from ..types import Answer


class TerminalUIUnavailable(RuntimeError):
    """Raised when interactive terminal UI should not be used."""


def _label(answer: Answer) -> str:
    return answer.title or answer.id


def select_answer_interactive(question: str, answers: Sequence[Answer]) -> Answer | None:
    """
    Return the selected answer via interactive terminal UI.

    Returns None when the user cancels (Esc/cancel action).
    Raises TerminalUIUnavailable when prompt_toolkit cannot/should not be used.
    """

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise TerminalUIUnavailable("interactive terminal picker requires a TTY")

    if os.environ.get("TERM", "").lower() == "dumb":
        raise TerminalUIUnavailable("interactive terminal picker unavailable in dumb terminal")

    try:
        from prompt_toolkit.shortcuts import radiolist_dialog
    except Exception as exc:  # pragma: no cover - import-only guard
        raise TerminalUIUnavailable("prompt_toolkit is not available") from exc

    values = [(idx, _label(answer)) for idx, answer in enumerate(answers)]
    dialog_text = f"{question}\n\n↑/↓ move • Enter select • Esc cancel"
    selected_index = radiolist_dialog(
        title="Ask",
        text=dialog_text,
        values=values,
        ok_text="Select",
        cancel_text="Cancel",
    ).run()

    if selected_index is None:
        return None

    return answers[selected_index]
