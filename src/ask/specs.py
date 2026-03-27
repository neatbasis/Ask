# ha_ask/specs.py
from __future__ import annotations

from typing import Optional, Sequence

from .types import Answer, ChoiceSpec


def yes_no_spec(
    question: str,
    *,
    title: Optional[str] = None,
    timeout_s: float = 180.0,
    allow_replies: bool = False,
    # Extend/override vocab
    yes: Optional[Sequence[str]] = None,
    no: Optional[Sequence[str]] = None,
) -> ChoiceSpec:
    """
    Reusable Yes/No choice spec (Assist-native).

    - Works for satellite (answers matching) and mobile (buttons via Answer.title).
    - Add synonyms to reduce 'id=None' due to natural variants ("yep", "ok", etc.).
    """
    yes_default = [
        "yes", "yeah", "yep", "yup", "sure", "of course", "ok", "okay", "alright", "certainly", "affirmative",
    ]
    no_default = [
        "no", "nope", "nah", "negative",
    ]


    yes_sents = list(dict.fromkeys((yes or yes_default)))  # de-dupe, keep order
    no_sents = list(dict.fromkeys((no or no_default)))

    return ChoiceSpec(
        question=question,
        answers=[
            Answer("yes", yes_sents, title="Yes"),
            Answer("no", no_sents, title="No"),
        ],
        allow_replies=allow_replies,
        timeout_s=timeout_s,
        title=title,
    )
