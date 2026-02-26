from __future__ import annotations

from ha_ask.finalize import finalize_schema


def test_finalize_succeeds_with_evidence_backed_values_and_declined_resolution() -> None:
    schema_object = {
        "full_name": "Alex Kim",
        "preferred_contact_method": "email",
        "timezone": None,
        "consent_to_contact": True,
    }
    evidence_map = {
        "full_name": {"source": "seed"},
        "preferred_contact_method": {"source": "ask_session"},
        "consent_to_contact": {"source": "ask_session"},
    }
    resolutions = {"timezone": {"status": "declined", "reason": "user skipped"}}

    result = finalize_schema(
        schema_object=schema_object,
        evidence_map=evidence_map,
        required_fields=[
            "full_name",
            "preferred_contact_method",
            "timezone",
            "consent_to_contact",
        ],
        resolutions=resolutions,
    )

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["finalized"] is not None
    assert result["finalized"]["schema_object"] == schema_object
    assert result["finalized"]["evidence_map"] == evidence_map

    decisions = {d["field_path"]: d for d in result["rationale"]["decisions"]}
    assert decisions["timezone"]["status"] == "accepted"
    assert decisions["timezone"]["reason"] == "explicit_resolution"
    assert decisions["timezone"]["resolution"] == "declined"


def test_finalize_fails_with_machine_readable_missing_evidence_and_unresolved_errors() -> None:
    schema_object = {
        "full_name": "Alex Kim",
        "preferred_contact_method": "email",
        "timezone": None,
        "consent_to_contact": None,
    }
    evidence_map = {
        "full_name": {"source": "seed"},
    }

    result = finalize_schema(
        schema_object=schema_object,
        evidence_map=evidence_map,
        required_fields=[
            "full_name",
            "preferred_contact_method",
            "timezone",
            "consent_to_contact",
        ],
        resolutions={"timezone": "unknown"},
    )

    assert result["ok"] is False
    assert result["finalized"] is None

    errors = {error["code"]: error for error in result["errors"]}
    assert errors["required_fields_missing_evidence"]["field_paths"] == ["preferred_contact_method"]
    assert errors["required_fields_unresolved"]["field_paths"] == ["consent_to_contact"]

    decisions = {d["field_path"]: d for d in result["rationale"]["decisions"]}
    assert decisions["preferred_contact_method"]["reason"] == "value_missing_evidence"
    assert decisions["consent_to_contact"]["reason"] == "missing_value_and_resolution"
