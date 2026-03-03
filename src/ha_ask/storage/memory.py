from __future__ import annotations

import time
import uuid
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from ha_ask.storage.base import StorageBackend
from ha_ask.types import AskResult, AskSessionRecord, AskSpec


class InMemoryStorageBackend(StorageBackend):
    def __init__(self) -> None:
        self._ask_sessions: dict[str, AskSessionRecord] = {}
        self._drafts: dict[str, dict[str, Any]] = {}

    def persist_ask_session(self, *, channel: str, spec: AskSpec, result: AskResult) -> str:
        meta = result.setdefault("meta", {})
        ask_session_id = str(meta.get("ask_session_id") or uuid.uuid4().hex)
        meta["ask_session_id"] = ask_session_id

        slot_evidence = meta.get("slot_evidence")
        if not isinstance(slot_evidence, dict):
            slot_evidence = {}
            meta["slot_evidence"] = slot_evidence

        replies = meta.get("replies")
        if not isinstance(replies, list):
            replies = []

        record: AskSessionRecord = {
            "ask_session_id": ask_session_id,
            "channel": channel,
            "prompt": spec.question,
            "chosen_answer_id": result.get("id"),
            "sentence": result.get("sentence"),
            "replies": replies,
            "slot_evidence": slot_evidence,
            "slots": result.get("slots") if isinstance(result.get("slots"), dict) else {},
            "t_sent": meta.get("t_sent"),
            "t_first_reply": meta.get("t_first_reply"),
            "t_done": meta.get("t_done"),
            "persisted_at": time.time(),
        }
        self._ask_sessions[ask_session_id] = record
        return ask_session_id

    def get_ask_session(self, ask_session_id: str) -> AskSessionRecord | None:
        return self._ask_sessions.get(ask_session_id)

    def clear_ask_sessions(self) -> None:
        self._ask_sessions.clear()

    def begin_schema_draft(
        self,
        *,
        schema_name: str,
        partial_input: Mapping[str, Any],
        required_fields: list[str],
        created_at: str,
    ) -> str:
        draft_id = uuid.uuid4().hex
        self._drafts[draft_id] = {
            "draft_id": draft_id,
            "schema_name": schema_name,
            "partial_input": dict(partial_input),
            "required_fields": list(required_fields),
            "state_transitions": [{"state": "created", "at": created_at}],
            "stage_timestamps": {"created": created_at},
            "question_episodes": [],
            "evidence": {},
            "unresolved_snapshots": [],
            "final_object": None,
            "rationale": None,
        }
        return draft_id

    def record_draft_transition(self, *, draft_id: str, state: str, at: str) -> None:
        draft = self._drafts.get(draft_id)
        if not draft:
            return
        draft["state_transitions"].append({"state": state, "at": at})

    def persist_stage_timestamp(self, *, draft_id: str, stage: str, at: str) -> None:
        draft = self._drafts.get(draft_id)
        if not draft:
            return
        draft["stage_timestamps"][stage] = at

    def persist_question_episode(
        self,
        *,
        draft_id: str,
        question_id: str,
        field_path: str,
        status: str,
        status_history: list[Mapping[str, str]],
        planned_at: str,
        asked_at: str,
        answered_at: str,
        applied_at: str,
        ask_session_id: str,
    ) -> None:
        draft = self._drafts.get(draft_id)
        if not draft:
            return
        draft["question_episodes"].append(
            {
                "question_id": question_id,
                "field_path": field_path,
                "status": status,
                "status_history": deepcopy([dict(item) for item in status_history]),
                "planned_at": planned_at,
                "asked_at": asked_at,
                "answered_at": answered_at,
                "applied_at": applied_at,
                "ask_session_id": ask_session_id,
            }
        )

    def persist_evidence(
        self, *, draft_id: str, field_path: str, evidence: Mapping[str, Any]
    ) -> None:
        draft = self._drafts.get(draft_id)
        if not draft:
            return
        draft["evidence"][field_path] = deepcopy(dict(evidence))

    def persist_unresolved_snapshot(
        self,
        *,
        draft_id: str,
        stage: str,
        unresolved_fields: list[str],
        captured_at: str,
    ) -> None:
        draft = self._drafts.get(draft_id)
        if not draft:
            return
        draft["unresolved_snapshots"].append(
            {
                "stage": stage,
                "unresolved_fields": list(unresolved_fields),
                "captured_at": captured_at,
            }
        )

    def persist_finalized_schema(
        self,
        *,
        draft_id: str,
        final_object: Mapping[str, Any] | None,
        rationale: Mapping[str, Any],
    ) -> None:
        draft = self._drafts.get(draft_id)
        if not draft:
            return
        draft["final_object"] = deepcopy(dict(final_object)) if final_object is not None else None
        draft["rationale"] = deepcopy(dict(rationale))

    def get_draft(self, draft_id: str) -> dict[str, Any] | None:
        draft = self._drafts.get(draft_id)
        return deepcopy(draft) if draft else None

    def clear_drafts(self) -> None:
        self._drafts.clear()
