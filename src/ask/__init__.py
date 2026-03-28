"""Canonical public package surface for Ask.

`ask` is the forward-looking package identity and implementation authority.
`ha_ask` remains available as a compatibility shim.
"""

from .client import AskClient
from .config import Config
from .dispatch import (
    ask_choice,
    ask_choice_async,
    ask_freeform,
    ask_freeform_async,
    ask_question,
    ask_question_async,
)
from .errors import (
    ERR_CANCELLED,
    ERR_NO_MATCH,
    ERR_NO_RESPONSE,
    ERR_TIMEOUT,
    error_kind,
    is_cancelled,
    is_match,
    is_no_match,
    is_no_response,
    is_ok,
    is_other_error,
    is_timeout,
)
from .specs import yes_no_spec
from .types import Answer, AskResult, AskSpec, ChoiceSpec, FreeformSpec

__all__ = [
    "AskClient",
    "ask_question",
    "ask_choice",
    "ask_freeform",
    "ask_question_async",
    "ask_choice_async",
    "ask_freeform_async",
    "AskSpec",
    "ChoiceSpec",
    "FreeformSpec",
    "Answer",
    "AskResult",
    "Config",
    "yes_no_spec",
    "ERR_NO_MATCH",
    "ERR_NO_RESPONSE",
    "ERR_TIMEOUT",
    "ERR_CANCELLED",
    "error_kind",
    "is_ok",
    "is_match",
    "is_no_match",
    "is_no_response",
    "is_timeout",
    "is_cancelled",
    "is_other_error",
]
