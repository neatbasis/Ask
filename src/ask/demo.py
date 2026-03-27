from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, TypedDict

from .schema_flow import ScenarioName, run_schema_flow_with_report


class PlannedQuestionSpec(TypedDict):
    field_path: str
    question: str
    mode: str


class DemoScenarioConstants(TypedDict):
    initial_payload: dict[str, Any]
    expected_final_json: dict[str, Any]
    planned_questions: list[PlannedQuestionSpec]
    demo_answers: dict[str, str]


class DemoResult(TypedDict):
    flow_result: dict[str, Any]
    report: dict[str, Any]
    report_path: str


def _extract_json_block(markdown: str, heading: str) -> dict[str, Any]:
    pattern = rf"{re.escape(heading)}[\s\S]*?```json\n([\s\S]*?)\n```"
    match = re.search(pattern, markdown)
    if match is None:
        raise ValueError(f"missing_json_block:{heading}")
    return json.loads(match.group(1))


def _extract_planned_questions(markdown: str) -> list[PlannedQuestionSpec]:
    pattern = (
        r"\d+\. \*\*Field:\*\* `([^`]+)`\s+"
        r"\*\*Question:\*\* `([^`]+)`\s+"
        r"\*\*Mode:\*\* (choice|reply)"
    )
    matches = re.findall(pattern, markdown)
    if not matches:
        raise ValueError("missing_planned_questions")
    return [
        {"field_path": field, "question": question, "mode": mode}
        for field, question, mode in matches
    ]


def _extract_demo_answers(markdown: str) -> dict[str, str]:
    block_match = re.search(
        r"### Canonical answers to use during demo\n\n([\s\S]*?)\n## 3\)",
        markdown,
    )
    if block_match is None:
        raise ValueError("missing_demo_answers")

    answers: dict[str, str] = {}
    for field, answer in re.findall(
        r"\d+\. `([^`]+)` -> (?:choose|reply) `([^`]+)`",
        block_match.group(1),
    ):
        answers[field] = answer
    if not answers:
        raise ValueError("missing_demo_answers_entries")
    return answers


def load_demo_constants(path: str | Path = "docs/demo_scenario.md") -> DemoScenarioConstants:
    markdown = Path(path).read_text(encoding="utf-8")
    initial_payload = _extract_json_block(markdown, "## 1) Initial partial payload")
    expected_final_json = _extract_json_block(
        markdown, "## 4) Final schema instance expected after completion"
    )
    planned_questions = _extract_planned_questions(markdown)
    demo_answers = _extract_demo_answers(markdown)
    return {
        "initial_payload": initial_payload,
        "expected_final_json": expected_final_json,
        "planned_questions": planned_questions,
        "demo_answers": demo_answers,
    }


def _response_for(field_path: str, answer_value: str) -> dict[str, Any]:
    if field_path == "consent_to_contact":
        return {
            "id": answer_value,
            "sentence": "Yes",
            "slots": {"consent_to_contact": True},
            "meta": {"ask_session_id": "demo-session-consent", "replies": []},
            "error": None,
        }
    if field_path == "preferred_contact_method":
        return {
            "id": answer_value,
            "sentence": "Email",
            "slots": {"preferred_contact_method": "email"},
            "meta": {"ask_session_id": "demo-session-contact", "replies": []},
            "error": None,
        }
    if field_path == "timezone":
        return {
            "id": None,
            "sentence": answer_value,
            "slots": {},
            "meta": {"ask_session_id": "demo-session-timezone", "replies": [answer_value]},
            "error": None,
        }
    raise ValueError(f"unsupported_field:{field_path}")


def run_demo(
    *,
    schema_name: ScenarioName = "person_profile_v1",
    docs_path: str | Path = "docs/demo_scenario.md",
    report_output_path: str | Path = "artifacts/demo_report.json",
) -> DemoResult:
    constants = load_demo_constants(docs_path)

    required_unresolved = {"consent_to_contact", "preferred_contact_method", "timezone"}
    unresolved_from_input = {
        field_path for field_path, value in constants["initial_payload"].items() if value is None
    }
    if unresolved_from_input != required_unresolved:
        raise AssertionError("initial_unresolved_mismatch")

    expected_order = [item["field_path"] for item in constants["planned_questions"]]
    expected_questions = [item["question"] for item in constants["planned_questions"]]

    calls: list[str] = []

    def _ask_callable(**kwargs: Any) -> dict[str, Any]:
        if kwargs.get("channel") != "mobile":
            raise AssertionError("non_mobile_channel_detected")
        spec = kwargs["spec"]
        calls.append(spec.question)

        planned_index = len(calls) - 1
        expected_field = expected_order[planned_index]
        demo_answer = constants["demo_answers"][expected_field]
        return _response_for(expected_field, demo_answer)

    run_result = run_schema_flow_with_report(
        schema_name=schema_name,
        partial_input=constants["initial_payload"],
        channel="mobile",
        api_url="https://example.local",
        token="demo-token",
        ask_callable=_ask_callable,
        notify_action="notify.mobile_app_phone",
    )
    flow_result = run_result["flow_result"]

    if calls != expected_questions:
        raise AssertionError("planned_question_order_mismatch")

    if flow_result["final_object"] != constants["expected_final_json"]:
        raise AssertionError("final_object_mismatch")

    required_keys_by_mode = {
        "choice": [
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
        ],
        "reply": [
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
        ],
    }

    evidence = flow_result["evidence_map"]
    mode_by_field = {item["field_path"]: item["mode"] for item in constants["planned_questions"]}
    for field_path in expected_order:
        entry = evidence[field_path]
        for required_key in required_keys_by_mode[mode_by_field[field_path]]:
            if required_key not in entry:
                raise AssertionError(f"missing_evidence:{field_path}:{required_key}")

    if not evidence["consent_to_contact"].get("answer_id") == "consent_yes":
        raise AssertionError("consent_mapping_mismatch")
    if not evidence["preferred_contact_method"].get("answer_id") == "contact_email":
        raise AssertionError("contact_mapping_mismatch")

    report = run_result["report"]

    output_path = Path(report_output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "flow_result": flow_result,
        "report": report,
        "report_path": str(output_path),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the reference demo scenario from docs/demo_scenario.md")
    parser.add_argument("--docs", default="docs/demo_scenario.md", help="Path to scenario markdown")
    parser.add_argument(
        "--output", default="artifacts/demo_report.json", help="Path to output report"
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = run_demo(docs_path=args.docs, report_output_path=args.output)
    print(json.dumps(result["report"], indent=2, sort_keys=True))
    print(f"Wrote demo report to {result['report_path']}")
    return 0


__all__ = ["load_demo_constants", "run_demo", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
