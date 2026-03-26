"""Compatibility package for Ask.

Prefer importing from `ask` in new code.
`ha_ask` remains supported as a migration shim.
"""

# ha_ask/__init__.py
from .types import AskSpec, Answer, ChoiceSpec, FreeformSpec
from .dispatch import (
    ask_choice,
    ask_choice_async,
    ask_freeform,
    ask_freeform_async,
    ask_question,
    ask_question_async,
)
from .specs import yes_no_spec
from .client import AskClient
from .errors import (
    ERR_NO_MATCH, ERR_NO_RESPONSE, ERR_TIMEOUT, ERR_CANCELLED,
    error_kind, is_ok, is_match, is_no_match, is_no_response, is_timeout, is_cancelled, is_other_error
)
from .planning import PlannedQuestion, ProbeCandidate, plan_questions

from .finalize import finalize_schema

from .reporting import build_draft_report

from .schema_flow import run_schema_flow, SchemaFlowResult
from .canonical_demo import load_demo_constants, run_canonical_demo
from .demo import run_demo

# Back-compat export during spec migration:
# - Prefer `ChoiceSpec` / `FreeformSpec` in new code.
# - `AskSpec` remains supported for existing integrations.
