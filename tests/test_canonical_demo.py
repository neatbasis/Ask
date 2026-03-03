from __future__ import annotations

import json
from pathlib import Path

from ha_ask.canonical_demo import load_demo_constants, run_canonical_demo


def test_load_demo_constants_reads_markdown_contract() -> None:
    constants = load_demo_constants("docs/demo_scenario.md")

    assert constants["initial_payload"] == {
        "full_name": "Alex Kim",
        "timezone": None,
        "preferred_contact_method": None,
        "consent_to_contact": None,
    }
    assert [item["field_path"] for item in constants["planned_questions"]] == [
        "consent_to_contact",
        "preferred_contact_method",
        "timezone",
    ]
    assert constants["canonical_answers"] == {
        "consent_to_contact": "consent_yes",
        "preferred_contact_method": "contact_email",
        "timezone": "America/Los_Angeles",
    }


def test_run_canonical_demo_writes_report_and_validates_expected_final_json(tmp_path: Path) -> None:
    output_path = tmp_path / "demo_report.json"

    result = run_canonical_demo(report_output_path=output_path)

    assert result["flow_result"]["final_object"] == {
        "full_name": "Alex Kim",
        "preferred_contact_method": "email",
        "timezone": "America/Los_Angeles",
        "consent_to_contact": True,
    }
    assert output_path.exists()

    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert persisted == result["report"]

    evidence = result["flow_result"]["evidence_map"]
    assert evidence["consent_to_contact"]["answer_id"] == "consent_yes"
    assert evidence["consent_to_contact"]["answer_text"] == "Yes"
    assert evidence["preferred_contact_method"]["answer_id"] == "contact_email"
    assert evidence["preferred_contact_method"]["answer_text"] == "Email"
    assert evidence["timezone"]["raw_reply"] == "America/Los_Angeles"
