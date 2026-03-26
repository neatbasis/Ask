from __future__ import annotations

import json
import re
from pathlib import Path

from ha_ask.demo import load_demo_constants, run_demo
from ha_ask.evidence import REQUIRED_EVIDENCE_KEYS_BY_FIELD


def _required_evidence_keys_from_demo_contract(path: str) -> dict[str, set[str]]:
    document = Path(path).read_text(encoding="utf-8")
    section_match = re.search(
        r"## 5\) Required evidence artifacts per resolved field(?P<section>.*?)(\n## |\Z)",
        document,
        flags=re.S,
    )
    assert section_match is not None

    section = section_match.group("section")
    parsed: dict[str, set[str]] = {}
    for field_match in re.finditer(r"###\s+`([^`]+)`(?P<body>.*?)(?=\n### |\Z)", section, flags=re.S):
        field_path = field_match.group(1)
        body = field_match.group("body")
        keys: set[str] = set()
        for line in body.splitlines():
            if not line.strip().startswith("-") or ":" not in line:
                continue
            key_segment = line.split(":", maxsplit=1)[0]
            keys.update({token.strip() for token in re.findall(r"`([^`]+)`", key_segment)})
        parsed[field_path] = keys
    return parsed


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
    assert constants["demo_answers"] == {
        "consent_to_contact": "consent_yes",
        "preferred_contact_method": "contact_email",
        "timezone": "America/Los_Angeles",
    }


def test_run_demo_writes_report_and_validates_expected_final_json(tmp_path: Path) -> None:
    output_path = tmp_path / "demo_report.json"

    result = run_demo(report_output_path=output_path)

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


def test_run_demo_evidence_contract_contains_required_keys_by_mode() -> None:
    result = run_demo()
    constants = load_demo_constants("docs/demo_scenario.md")

    required_keys_by_mode = {
        "choice": {
            "field_path",
            "source",
            "channel",
            "question_text",
            "answer_id",
            "answer_text",
            "slot_binding",
            "ask_session_id",
            "asked_at",
            "answered_at",
        },
        "reply": {
            "field_path",
            "source",
            "channel",
            "question_text",
            "raw_reply",
            "parsed_value",
            "parse_status",
            "ask_session_id",
            "asked_at",
            "answered_at",
        },
    }

    evidence = result["flow_result"]["evidence_map"]
    for planned in constants["planned_questions"]:
        field_path = planned["field_path"]
        mode = planned["mode"]
        assert required_keys_by_mode[mode].issubset(set(evidence[field_path].keys()))


def test_required_evidence_keys_align_with_demo_scenario_section_5_and_are_present() -> None:
    required_by_field = _required_evidence_keys_from_demo_contract("docs/demo_scenario.md")
    assert required_by_field == REQUIRED_EVIDENCE_KEYS_BY_FIELD

    result = run_demo()
    evidence = result["flow_result"]["evidence_map"]

    for field_path, required_keys in required_by_field.items():
        assert required_keys.issubset(set(evidence[field_path].keys()))


def test_demo_cli_main_writes_report(tmp_path: Path, monkeypatch) -> None:
    from ha_ask.demo import main

    output_path = tmp_path / "cli_report.json"
    monkeypatch.setattr("sys.argv", ["demo", "--output", str(output_path)])

    exit_code = main()

    assert exit_code == 0
    assert output_path.exists()
