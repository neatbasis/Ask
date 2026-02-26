from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence


@dataclass(frozen=True)
class ProbeCandidate:
    """Candidate probe/question that can be asked to resolve uncertainty."""

    probe_id: str
    field_path: str
    answer_id: str
    question: str
    information_gain: float
    p_answer: float
    p_resolve: float
    cost: float


@dataclass(frozen=True)
class PlannedQuestion:
    """Deterministically planned question with transparent score metadata."""

    probe_id: str
    field_path: str
    answer_id: str
    question: str
    score: float
    score_components: Dict[str, float]


def _score(candidate: ProbeCandidate) -> float:
    return (
        candidate.information_gain * candidate.p_answer * candidate.p_resolve
        - candidate.cost
    )


def _sort_key(item: PlannedQuestion) -> tuple[float, str, str, str]:
    # Primary: score descending (negated for ascending sort API)
    # Tie-breakers (deterministic): field path lexical, then answer id lexical.
    # Final probe_id tie-break to guarantee total order across equivalent entries.
    return (-item.score, item.field_path, item.answer_id, item.probe_id)


def plan_questions(
    candidates: Sequence[ProbeCandidate],
    *,
    cooled_down_fields: Iterable[str] = (),
    max_questions: int | None = None,
) -> List[PlannedQuestion]:
    """
    Plan questions using deterministic policy.

    Policy:
    1) score = IG × p(answer) × p(resolve) − cost
    2) deterministic tie-breakers: field path lexical, then answer id lexical
    3) one-probe-per-field cooldown per planning call
    4) include full score metadata for each returned question
    """
    blocked_fields = set(cooled_down_fields)

    scored: List[PlannedQuestion] = []
    for candidate in candidates:
        if candidate.field_path in blocked_fields:
            continue

        score = _score(candidate)
        scored.append(
            PlannedQuestion(
                probe_id=candidate.probe_id,
                field_path=candidate.field_path,
                answer_id=candidate.answer_id,
                question=candidate.question,
                score=score,
                score_components={
                    "information_gain": candidate.information_gain,
                    "p_answer": candidate.p_answer,
                    "p_resolve": candidate.p_resolve,
                    "cost": candidate.cost,
                    "score": score,
                },
            )
        )

    ordered = sorted(scored, key=_sort_key)

    # One-probe-per-field cooldown enforcement.
    selected: List[PlannedQuestion] = []
    seen_fields: set[str] = set()
    for planned in ordered:
        if planned.field_path in seen_fields:
            continue
        seen_fields.add(planned.field_path)
        selected.append(planned)
        if max_questions is not None and len(selected) >= max_questions:
            break

    return selected


__all__ = [
    "PlannedQuestion",
    "ProbeCandidate",
    "plan_questions",
]
