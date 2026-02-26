from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from .reporting import DraftReportInput, build_draft_report


_CANONICAL_PAYLOAD: DraftReportInput = {
    "lifecycle": {
        "created_at": "2026-01-10T10:00:00Z",
        "planned_at": "2026-01-10T10:00:03Z",
        "asked_at": "2026-01-10T10:00:10Z",
        "applied_at": "2026-01-10T10:00:25Z",
        "finalized_at": "2026-01-10T10:00:30Z",
    },
    "questions": [
        {
            "question_id": "q1",
            "field_path": "consent_to_contact",
            "asked_at": "2026-01-10T10:00:10Z",
            "answered_at": "2026-01-10T10:00:12Z",
            "resolved_fields": ["consent_to_contact"],
            "status": "resolved",
            "retry_count": 0,
        },
        {
            "question_id": "q2",
            "field_path": "preferred_contact_method",
            "asked_at": "2026-01-10T10:00:12Z",
            "answered_at": "2026-01-10T10:00:18Z",
            "resolved_fields": ["preferred_contact_method"],
            "status": "resolved",
            "retry_count": 0,
        },
        {
            "question_id": "q3",
            "field_path": "timezone",
            "asked_at": "2026-01-10T10:00:18Z",
            "answered_at": "2026-01-10T10:00:24Z",
            "resolved_fields": ["timezone"],
            "status": "resolved",
            "retry_count": 0,
        },
    ],
    "evidence_map": {
        "consent_to_contact": {
            "source": "ask_session",
            "channel": "mobile",
            "ask_session_id": "demo-session-1",
            "answer_id": "consent_yes",
            "answered_at": "2026-01-10T10:00:12Z",
        },
        "preferred_contact_method": {
            "source": "ask_session",
            "channel": "mobile",
            "ask_session_id": "demo-session-2",
            "answer_id": "contact_email",
            "answered_at": "2026-01-10T10:00:18Z",
        },
        "timezone": {
            "source": "ask_session",
            "channel": "mobile",
            "ask_session_id": "demo-session-3",
            "answer_id": None,
            "answered_at": "2026-01-10T10:00:24Z",
        },
    },
    "unresolved_fields": [],
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate canonical demo artifact JSON.")
    parser.add_argument(
        "--output",
        default="artifacts/demo_report.json",
        help="Path to write the generated artifact JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report: Dict[str, Any] = build_draft_report(_CANONICAL_PAYLOAD)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"Wrote canonical demo artifact to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
