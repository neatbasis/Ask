from __future__ import annotations

from ha_ask.apply import (
    apply_answer_to_field,
    map_consent_button_id,
    map_contact_method_button_id,
    parse_timezone_reply,
)


def test_apply_answer_to_field_uses_deterministic_canonical_mappings() -> None:
    consent_result = apply_answer_to_field(
        "consent_to_contact",
        {
            "id": "consent_no",
            "sentence": "No",
            "slots": {"consent_to_contact": True},
            "meta": {},
            "error": None,
        },
        mapping_config=None,
    )

    assert consent_result["resolved_fields"] == ["consent_to_contact"]
    assert consent_result["applied_values"] == {"consent_to_contact": False}
    assert consent_result["evidence_fragments"]["consent_to_contact"]["mapping_source"] == "canonical_answer_id"

    contact_result = apply_answer_to_field(
        "preferred_contact_method",
        {
            "id": "contact_sms",
            "sentence": "SMS",
            "slots": {},
            "meta": {},
            "error": None,
        },
        mapping_config=None,
    )

    assert contact_result["resolved_fields"] == ["preferred_contact_method"]
    assert contact_result["applied_values"] == {"preferred_contact_method": "sms"}


def test_timezone_reply_parser_and_application_result_payload() -> None:
    parsed = parse_timezone_reply("America/Los_Angeles")
    assert parsed == {"parse_status": "success", "parsed_value": "America/Los_Angeles"}

    invalid = parse_timezone_reply("Not/A_Timezone")
    assert invalid == {"parse_status": "invalid", "parsed_value": None}

    applied = apply_answer_to_field(
        "timezone",
        {
            "id": None,
            "sentence": "America/New_York",
            "slots": {},
            "meta": {"replies": []},
            "error": None,
        },
        mapping_config=None,
    )

    assert applied["resolved_fields"] == ["timezone"]
    assert applied["parse_status"] == "success"
    assert applied["applied_values"] == {"timezone": "America/New_York"}
    assert applied["evidence_fragments"]["timezone"] == {
        "field_path": "timezone",
        "raw_reply": "America/New_York",
        "parsed_value": "America/New_York",
        "parse_status": "success",
    }


def test_canonical_button_id_mappers_return_machine_readable_status() -> None:
    assert map_consent_button_id("consent_yes") == {"parse_status": "success", "normalized_value": True}
    assert map_consent_button_id("consent_unknown") == {"parse_status": "invalid", "normalized_value": None}
    assert map_contact_method_button_id("contact_phone") == {"parse_status": "success", "normalized_value": "phone"}
    assert map_contact_method_button_id(None) == {"parse_status": "missing", "normalized_value": None}


def test_timezone_parser_normalizes_case_to_canonical_iana() -> None:
    parsed = parse_timezone_reply("america/new_york")
    assert parsed == {"parse_status": "success", "parsed_value": "America/New_York"}
