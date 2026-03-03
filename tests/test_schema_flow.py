from __future__ import annotations

from typing import Any

from ha_ask.schema_flow import run_schema_flow


def test_run_schema_flow_person_profile_v1_canonical_sequence_and_finalize() -> None:
    responses: list[dict[str, Any]] = [
        {
            "id": "consent_yes",
            "sentence": "Yes",
            "slots": {"consent_to_contact": True},
            "meta": {"ask_session_id": "session-1", "replies": []},
            "error": None,
        },
        {
            "id": "contact_email",
            "sentence": "Email",
            "slots": {"preferred_contact_method": "email"},
            "meta": {"ask_session_id": "session-2", "replies": []},
            "error": None,
        },
        {
            "id": None,
            "sentence": "America/Los_Angeles",
            "slots": {},
            "meta": {"ask_session_id": "session-3", "replies": ["America/Los_Angeles"]},
            "error": None,
        },
    ]
    called_fields: list[str] = []

    def _fake_ask(**kwargs: Any) -> dict[str, Any]:
        spec = kwargs["spec"]
        called_fields.append(spec.question)
        return responses.pop(0)

    result = run_schema_flow(
        schema_name="person_profile_v1",
        partial_input={
            "full_name": "Alex Kim",
            "timezone": None,
            "preferred_contact_method": None,
            "consent_to_contact": None,
        },
        channel="mobile",
        api_url="https://example.local",
        token="token",
        ask_callable=_fake_ask,
        notify_service="mobile_app_phone",
    )

    assert called_fields == [
        "Do you consent to being contacted about this request?",
        "What is your preferred contact method?",
        "What timezone should we use for scheduling?",
    ]

    assert result["final_object"] == {
        "full_name": "Alex Kim",
        "preferred_contact_method": "email",
        "timezone": "America/Los_Angeles",
        "consent_to_contact": True,
    }
    assert result["unresolved_fields"] == []
    assert result["errors"] == []

    consent_evidence = result["evidence_map"]["consent_to_contact"]
    assert consent_evidence["answer_id"] == "consent_yes"
    assert consent_evidence["slot_binding"] == {"consent_to_contact": True}

    timezone_evidence = result["evidence_map"]["timezone"]
    assert timezone_evidence["raw_reply"] == "America/Los_Angeles"
    assert timezone_evidence["parsed_value"] == "America/Los_Angeles"
    assert timezone_evidence["parse_status"] == "success"

    lifecycle_stages = set(result["draft_lifecycle"].keys())
    assert lifecycle_stages == {
        "created_at",
        "planned_at",
        "asked_at",
        "applied_at",
        "finalized_at",
    }

    question_statuses = [item["status"] for item in result["question_lifecycle"]]
    assert question_statuses == ["applied", "applied", "applied"]
