from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, TypedDict


LifecycleStage = str


class QuestionReportInput(TypedDict, total=False):
    question_id: str
    field_path: str
    asked_at: str
    answered_at: str
    resolved_fields: List[str]
    status: str
    retry_count: int


class DraftReportInput(TypedDict, total=False):
    lifecycle: Mapping[str, str]
    questions: List[QuestionReportInput]
    evidence_map: Mapping[str, Mapping[str, Any]]
    unresolved_fields: List[str]


_EXPECTED_LIFECYCLE: tuple[LifecycleStage, ...] = (
    "created",
    "planned",
    "asked",
    "applied",
    "finalized",
)


def _parse_iso8601(timestamp: str | None) -> datetime | None:
    if not timestamp:
        return None
    normalized = timestamp.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _duration_s(start: str | None, end: str | None) -> float | None:
    start_dt = _parse_iso8601(start)
    end_dt = _parse_iso8601(end)
    if start_dt is None or end_dt is None:
        return None
    return round((end_dt - start_dt).total_seconds(), 3)


def _collect_retry_count(questions: Iterable[QuestionReportInput]) -> int:
    return sum(max(0, int(item.get("retry_count", 0))) for item in questions)


def build_draft_report(payload: DraftReportInput) -> Dict[str, Any]:
    """Generate a single demo-ready artifact for draft/question lifecycle health."""
    lifecycle = payload.get("lifecycle", {})
    questions = payload.get("questions", [])
    evidence_map = payload.get("evidence_map", {})
    unresolved_fields = sorted(set(payload.get("unresolved_fields", [])))

    timeline = [
        {
            "stage": stage,
            "at": lifecycle.get(f"{stage}_at"),
            "elapsed_from_previous_s": (
                _duration_s(
                    lifecycle.get(f"{_EXPECTED_LIFECYCLE[index - 1]}_at") if index > 0 else None,
                    lifecycle.get(f"{stage}_at"),
                )
                if index > 0
                else None
            ),
        }
        for index, stage in enumerate(_EXPECTED_LIFECYCLE)
    ]

    total_resolved_fields = sum(len(item.get("resolved_fields", [])) for item in questions)
    per_question = []
    for item in questions:
        resolved_fields = sorted(set(item.get("resolved_fields", [])))
        contribution = (
            round(len(resolved_fields) / total_resolved_fields, 3)
            if total_resolved_fields > 0
            else 0.0
        )
        per_question.append(
            {
                "question_id": item.get("question_id"),
                "field_path": item.get("field_path"),
                "latency_s": _duration_s(item.get("asked_at"), item.get("answered_at")),
                "resolution_contribution": {
                    "resolved_fields": resolved_fields,
                    "resolved_count": len(resolved_fields),
                    "share_of_all_resolutions": contribution,
                },
                "retry_count": max(0, int(item.get("retry_count", 0))),
                "status": item.get("status", "unknown"),
            }
        )

    evidence_summary = []
    for field_path in sorted(evidence_map.keys()):
        evidence = evidence_map[field_path]
        evidence_summary.append(
            {
                "field_path": field_path,
                "source": evidence.get("source"),
                "channel": evidence.get("channel"),
                "ask_session_id": evidence.get("ask_session_id"),
                "answer_id": evidence.get("answer_id"),
                "answered_at": evidence.get("answered_at"),
                "provenance_keys": sorted(evidence.keys()),
            }
        )

    unresolved_from_questions = sorted(
        {
            item["field_path"]
            for item in per_question
            if item.get("status") not in {"resolved", "applied", "finalized"} and item.get("field_path")
        }
    )

    return {
        "draft_lifecycle_timeline": timeline,
        "per_question_latency": per_question,
        "field_evidence_provenance": evidence_summary,
        "retry_and_churn": {
            "total_retry_count": _collect_retry_count(questions),
            "question_churn_count": len(unresolved_from_questions),
            "unresolved_fields": sorted(set(unresolved_fields + unresolved_from_questions)),
        },
    }


__all__ = ["build_draft_report"]
