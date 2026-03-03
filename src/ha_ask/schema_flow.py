from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Literal, TypedDict

from .evidence import build_choice_evidence, build_reply_evidence
from .finalize import FinalizeRationale, finalize_schema
from .planning import ProbeCandidate, plan_questions
from .storage import get_storage_backend
from .types import Answer, AskResult, AskSpec, EvidenceMap

ScenarioName = Literal["person_profile_v1"]


class QuestionLifecycle(TypedDict):
    question_id: str
    field_path: str
    status: str
    status_history: list[dict[str, str]]
    planned_at: str
    asked_at: str
    answered_at: str
    applied_at: str


class SchemaFlowResult(TypedDict):
    schema_name: str
    draft_state: dict[str, Any]
    required_fields: list[str]
    unresolved_fields: list[str]
    evidence_map: EvidenceMap
    question_lifecycle: list[QuestionLifecycle]
    draft_lifecycle: dict[str, str]
    final_object: dict[str, Any] | None
    rationale: FinalizeRationale
    errors: list[dict[str, Any]]


AskCallable = Callable[..., AskResult]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")  # noqa: UP017


def _supported_scenario(
    schema_name: ScenarioName,
) -> tuple[list[str], list[ProbeCandidate], dict[str, AskSpec]]:
    if schema_name != "person_profile_v1":
        raise ValueError(f"unsupported_schema:{schema_name}")

    required_fields = [
        "full_name",
        "preferred_contact_method",
        "timezone",
        "consent_to_contact",
    ]

    candidates = [
        ProbeCandidate(
            probe_id="person_profile_v1.consent_to_contact",
            field_path="consent_to_contact",
            answer_id="consent_yes",
            question="Do you consent to being contacted about this request?",
            information_gain=0.98,
            p_answer=0.95,
            p_resolve=0.95,
            cost=0.1,
        ),
        ProbeCandidate(
            probe_id="person_profile_v1.preferred_contact_method",
            field_path="preferred_contact_method",
            answer_id="contact_email",
            question="What is your preferred contact method?",
            information_gain=0.92,
            p_answer=0.9,
            p_resolve=0.9,
            cost=0.14,
        ),
        ProbeCandidate(
            probe_id="person_profile_v1.timezone",
            field_path="timezone",
            answer_id="reply_timezone",
            question="What timezone should we use for scheduling?",
            information_gain=0.8,
            p_answer=0.85,
            p_resolve=0.8,
            cost=0.2,
        ),
    ]

    ask_specs: dict[str, AskSpec] = {
        "consent_to_contact": AskSpec(
            question="Do you consent to being contacted about this request?",
            answers=[
                Answer(
                    id="consent_yes",
                    title="Yes",
                    sentences=["yes"],
                    slot_bindings={"consent_to_contact": True},
                ),
                Answer(
                    id="consent_no",
                    title="No",
                    sentences=["no"],
                    slot_bindings={"consent_to_contact": False},
                ),
            ],
            allow_replies=True,
            expect_reply=False,
        ),
        "preferred_contact_method": AskSpec(
            question="What is your preferred contact method?",
            answers=[
                Answer(
                    id="contact_sms",
                    title="SMS",
                    sentences=["sms"],
                    slot_bindings={"preferred_contact_method": "sms"},
                ),
                Answer(
                    id="contact_email",
                    title="Email",
                    sentences=["email"],
                    slot_bindings={"preferred_contact_method": "email"},
                ),
                Answer(
                    id="contact_phone",
                    title="Phone call",
                    sentences=["phone"],
                    slot_bindings={"preferred_contact_method": "phone"},
                ),
            ],
            allow_replies=True,
            expect_reply=False,
        ),
        "timezone": AskSpec(
            question="What timezone should we use for scheduling?",
            answers=None,
            allow_replies=True,
            expect_reply=True,
        ),
    }
    return required_fields, candidates, ask_specs


def _normalize_timezone(raw_value: str) -> str:
    return raw_value.strip()


def _extract_reply_text(result: Mapping[str, Any]) -> str:
    sentence = result.get("sentence")
    if isinstance(sentence, str) and sentence.strip():
        return sentence

    meta = result.get("meta")
    if isinstance(meta, Mapping):
        replies = meta.get("replies")
        if isinstance(replies, list):
            for item in reversed(replies):
                if isinstance(item, str) and item.strip():
                    return item
    return ""


def _collect_slots(result: Mapping[str, Any]) -> dict[str, Any]:
    slots = result.get("slots")
    if not isinstance(slots, Mapping):
        return {}
    return {k: v for k, v in slots.items()}


def run_schema_flow(
    *,
    schema_name: ScenarioName,
    partial_input: Mapping[str, Any],
    channel: Literal["mobile", "satellite"],
    api_url: str,
    token: str,
    ask_callable: AskCallable,
    notify_service: str | None = None,
    satellite_entity_id: str | None = None,
) -> SchemaFlowResult:
    required_fields, candidates, specs_by_field = _supported_scenario(schema_name)
    storage = get_storage_backend()

    draft_state: dict[str, Any] = {field: partial_input.get(field) for field in required_fields}
    evidence_map: EvidenceMap = {}

    created_at = _utc_now_iso()
    draft_lifecycle: dict[str, str] = {"created_at": created_at}
    draft_id = storage.begin_schema_draft(
        schema_name=schema_name,
        partial_input=partial_input,
        required_fields=required_fields,
        created_at=created_at,
    )

    for field in required_fields:
        if draft_state.get(field) is not None:
            evidence_map[field] = {
                "field_path": field,
                "source": "initial_payload",
                "channel": "system",
                "question_text": None,
                "ask_session_id": "",
                "asked_at": created_at,
                "answered_at": created_at,
                "value": draft_state[field],
            }

    unresolved_before_plan = [field for field in required_fields if draft_state.get(field) is None]
    planned_questions = plan_questions(
        [candidate for candidate in candidates if candidate.field_path in unresolved_before_plan]
    )
    draft_lifecycle["planned_at"] = _utc_now_iso()
    storage.record_draft_transition(
        draft_id=draft_id,
        state="planned",
        at=draft_lifecycle["planned_at"],
    )

    question_lifecycle: list[QuestionLifecycle] = []

    for planned in planned_questions:
        ask_spec = specs_by_field[planned.field_path]
        status_history: list[dict[str, str]] = []

        planned_at = _utc_now_iso()
        status_history.append({"status": "planned", "at": planned_at})

        asked_at = _utc_now_iso()
        status_history.append({"status": "asked", "at": asked_at})

        ask_kwargs: dict[str, Any] = {
            "channel": channel,
            "spec": ask_spec,
            "api_url": api_url,
            "token": token,
        }
        if notify_service:
            ask_kwargs["notify_service"] = notify_service
        if satellite_entity_id:
            ask_kwargs["satellite_entity_id"] = satellite_entity_id

        result = ask_callable(**ask_kwargs)

        answered_at = _utc_now_iso()
        status_history.append({"status": "answered", "at": answered_at})

        resolved_fields: list[str] = []
        slots = _collect_slots(result)
        for field_path, value in slots.items():
            draft_state[field_path] = value
            resolved_fields.append(field_path)

        if planned.field_path == "timezone" and planned.field_path not in slots:
            raw_reply = _extract_reply_text(result)
            if raw_reply:
                draft_state["timezone"] = _normalize_timezone(raw_reply)
                resolved_fields.append("timezone")

        applied_at = _utc_now_iso()
        status_history.append({"status": "applied", "at": applied_at})

        meta = result.get("meta") if isinstance(result.get("meta"), Mapping) else {}
        ask_session_id = str(meta.get("ask_session_id", ""))

        if planned.field_path == "timezone":
            raw_reply = _extract_reply_text(result)
            evidence_map[planned.field_path] = build_reply_evidence(
                field_path=planned.field_path,
                channel=channel,
                question_text=ask_spec.question,
                raw_reply=raw_reply,
                parsed_value=draft_state.get("timezone"),
                parse_status="success" if draft_state.get("timezone") else "failed",
                ask_session_id=ask_session_id,
                asked_at=asked_at,
                answered_at=answered_at,
            )
        else:
            matched_id = result.get("id") if isinstance(result.get("id"), str) else None
            answer_text = None
            if matched_id:
                for answer in ask_spec.answers or ():
                    if answer.id == matched_id:
                        answer_text = answer.title
                        break
            evidence_map[planned.field_path] = build_choice_evidence(
                field_path=planned.field_path,
                channel=channel,
                question_text=ask_spec.question,
                answer_id=matched_id,
                answer_text=answer_text,
                slot_binding={
                    field_name: draft_state[field_name]
                    for field_name in resolved_fields
                    if field_name == planned.field_path
                },
                ask_session_id=ask_session_id,
                asked_at=asked_at,
                answered_at=answered_at,
            )

        question_lifecycle.append(
            {
                "question_id": planned.probe_id,
                "field_path": planned.field_path,
                "status": "applied" if resolved_fields else "unresolved",
                "status_history": status_history,
                "planned_at": planned_at,
                "asked_at": asked_at,
                "answered_at": answered_at,
                "applied_at": applied_at,
            }
        )

    first_asked_at = question_lifecycle[0]["asked_at"] if question_lifecycle else _utc_now_iso()
    draft_lifecycle["asked_at"] = first_asked_at
    storage.record_draft_transition(draft_id=draft_id, state="asked", at=first_asked_at)
    draft_lifecycle["applied_at"] = _utc_now_iso()
    storage.record_draft_transition(
        draft_id=draft_id,
        state="applied",
        at=draft_lifecycle["applied_at"],
    )

    unresolved_fields = [field for field in required_fields if draft_state.get(field) is None]

    finalize_result = finalize_schema(
        schema_object=draft_state,
        evidence_map=evidence_map,
        required_fields=required_fields,
    )
    draft_lifecycle["finalized_at"] = _utc_now_iso()
    storage.record_draft_transition(
        draft_id=draft_id,
        state="finalized",
        at=draft_lifecycle["finalized_at"],
    )

    final_object = None
    if finalize_result["ok"] and finalize_result["finalized"] is not None:
        final_object = deepcopy(finalize_result["finalized"]["schema_object"])

    for field_path, evidence in evidence_map.items():
        storage.persist_evidence(draft_id=draft_id, field_path=field_path, evidence=evidence)
    storage.persist_finalized_schema(
        draft_id=draft_id,
        final_object=final_object,
        rationale=finalize_result["rationale"],
    )

    return {
        "schema_name": schema_name,
        "draft_state": draft_state,
        "required_fields": required_fields,
        "unresolved_fields": unresolved_fields,
        "evidence_map": evidence_map,
        "question_lifecycle": question_lifecycle,
        "draft_lifecycle": draft_lifecycle,
        "final_object": final_object,
        "rationale": finalize_result["rationale"],
        "errors": finalize_result["errors"],
    }


__all__ = ["QuestionLifecycle", "SchemaFlowResult", "run_schema_flow"]
