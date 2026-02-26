from ha_ask.reporting import build_draft_report


def test_build_draft_report_includes_requested_sections() -> None:
    payload = {
        "lifecycle": {
            "created_at": "2026-01-01T10:00:00Z",
            "planned_at": "2026-01-01T10:00:03Z",
            "asked_at": "2026-01-01T10:00:05Z",
            "applied_at": "2026-01-01T10:00:07Z",
            "finalized_at": "2026-01-01T10:00:09Z",
        },
        "questions": [
            {
                "question_id": "q-consent",
                "field_path": "consent_to_contact",
                "asked_at": "2026-01-01T10:00:05Z",
                "answered_at": "2026-01-01T10:00:06.500Z",
                "resolved_fields": ["consent_to_contact"],
                "status": "resolved",
                "retry_count": 1,
            },
            {
                "question_id": "q-timezone",
                "field_path": "timezone",
                "asked_at": "2026-01-01T10:00:06Z",
                "answered_at": "2026-01-01T10:00:08Z",
                "resolved_fields": ["timezone"],
                "status": "unresolved",
                "retry_count": 2,
            },
        ],
        "evidence_map": {
            "consent_to_contact": {
                "source": "ask_session",
                "channel": "mobile",
                "ask_session_id": "sess-1",
                "answer_id": "consent_yes",
                "answered_at": "2026-01-01T10:00:06.500Z",
            }
        },
        "unresolved_fields": ["preferred_contact_method"],
    }

    result = build_draft_report(payload)

    assert [item["stage"] for item in result["draft_lifecycle_timeline"]] == [
        "created",
        "planned",
        "asked",
        "applied",
        "finalized",
    ]
    assert result["draft_lifecycle_timeline"][1]["elapsed_from_previous_s"] == 3.0

    first_question = result["per_question_latency"][0]
    assert first_question["latency_s"] == 1.5
    assert first_question["resolution_contribution"]["share_of_all_resolutions"] == 0.5

    provenance = result["field_evidence_provenance"][0]
    assert provenance["field_path"] == "consent_to_contact"
    assert provenance["provenance_keys"] == [
        "answer_id",
        "answered_at",
        "ask_session_id",
        "channel",
        "source",
    ]

    churn = result["retry_and_churn"]
    assert churn["total_retry_count"] == 3
    assert churn["question_churn_count"] == 1
    assert churn["unresolved_fields"] == ["preferred_contact_method", "timezone"]
