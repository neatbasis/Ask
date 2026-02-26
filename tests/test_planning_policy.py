from __future__ import annotations

import random

import pytest

from ha_ask.planning import ProbeCandidate, plan_questions


def _candidates() -> list[ProbeCandidate]:
    # Designed so p1 and p2 tie on score; lexical tie-break picks city over date.
    return [
        ProbeCandidate(
            probe_id="p2",
            field_path="trip.date",
            answer_id="later",
            question="Should travel happen later?",
            information_gain=0.8,
            p_answer=0.5,
            p_resolve=0.5,
            cost=0.1,
        ),
        ProbeCandidate(
            probe_id="p1",
            field_path="trip.city",
            answer_id="berlin",
            question="Is Berlin the destination?",
            information_gain=0.8,
            p_answer=0.5,
            p_resolve=0.5,
            cost=0.1,
        ),
        ProbeCandidate(
            probe_id="p3",
            field_path="trip.city",
            answer_id="paris",
            question="Is Paris the destination?",
            information_gain=0.9,
            p_answer=0.8,
            p_resolve=0.8,
            cost=0.3,
        ),
        ProbeCandidate(
            probe_id="p4",
            field_path="trip.budget",
            answer_id="high",
            question="Is budget high?",
            information_gain=0.5,
            p_answer=0.4,
            p_resolve=0.5,
            cost=0.05,
        ),
    ]


def test_planning_policy_includes_score_components() -> None:
    planned = plan_questions(_candidates())

    first = planned[0]
    assert first.probe_id == "p3"
    assert first.score_components["information_gain"] == 0.9
    assert first.score_components["p_answer"] == 0.8
    assert first.score_components["p_resolve"] == 0.8
    assert first.score_components["cost"] == 0.3
    assert first.score_components["score"] == pytest.approx(0.276)


def test_planning_policy_enforces_one_probe_per_field_cooldown() -> None:
    planned = plan_questions(_candidates())
    planned_fields = [item.field_path for item in planned]

    # trip.city appears only once even though two probes target it.
    assert planned_fields.count("trip.city") == 1


def test_planning_policy_respects_cooled_down_fields() -> None:
    planned = plan_questions(_candidates(), cooled_down_fields={"trip.city"})

    assert [item.field_path for item in planned] == ["trip.date", "trip.budget"]


def test_planning_policy_is_deterministic_for_same_draft_state() -> None:
    baseline = plan_questions(_candidates())
    baseline_order = [item.probe_id for item in baseline]

    # Golden-style deterministic check under repeated candidate permutations.
    for seed in range(20):
        shuffled = _candidates()
        random.Random(seed).shuffle(shuffled)
        planned = plan_questions(shuffled)
        assert [item.probe_id for item in planned] == baseline_order
