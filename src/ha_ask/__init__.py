# ha_ask/__init__.py
from .types import AskSpec, Answer
from .dispatch import ask_question
from .specs import yes_no_spec
from .errors import (
    ERR_NO_MATCH, ERR_NO_RESPONSE, ERR_TIMEOUT,
    error_kind, is_ok, is_match, is_no_match, is_no_response, is_timeout, is_other_error
)
from .planning import PlannedQuestion, ProbeCandidate, plan_questions

from .finalize import finalize_schema
