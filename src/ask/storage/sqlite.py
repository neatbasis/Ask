from __future__ import annotations

import json
import sqlite3
import time
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ask.storage.base import StorageBackend
from ask.types import AskResult, AskSessionRecord, AskSpec


class SQLiteStorageBackend(StorageBackend):
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS ask_sessions (
                    ask_session_id TEXT PRIMARY KEY,
                    channel TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    chosen_answer_id TEXT,
                    sentence TEXT,
                    replies_json TEXT NOT NULL,
                    slot_evidence_json TEXT NOT NULL,
                    slots_json TEXT NOT NULL,
                    t_sent REAL,
                    t_first_reply REAL,
                    t_done REAL,
                    persisted_at REAL NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_drafts (
                    draft_id TEXT PRIMARY KEY,
                    schema_name TEXT NOT NULL,
                    partial_input_json TEXT NOT NULL,
                    required_fields_json TEXT NOT NULL,
                    final_object_json TEXT,
                    rationale_json TEXT
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS draft_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    draft_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    at TEXT NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS draft_stage_timestamps (
                    draft_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    at TEXT NOT NULL,
                    PRIMARY KEY(draft_id, stage)
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS question_episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    draft_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    field_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    status_history_json TEXT NOT NULL,
                    planned_at TEXT NOT NULL,
                    asked_at TEXT NOT NULL,
                    answered_at TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    ask_session_id TEXT NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS draft_evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    draft_id TEXT NOT NULL,
                    field_path TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    UNIQUE(draft_id, field_path)
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS draft_unresolved_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    draft_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    unresolved_fields_json TEXT NOT NULL,
                    captured_at TEXT NOT NULL
                )
                """
            )

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

        slots = result.get("slots") if isinstance(result.get("slots"), dict) else {}
        record: AskSessionRecord = {
            "ask_session_id": ask_session_id,
            "channel": channel,
            "prompt": spec.question,
            "chosen_answer_id": result.get("id"),
            "sentence": result.get("sentence"),
            "replies": replies,
            "slot_evidence": slot_evidence,
            "slots": slots,
            "t_sent": meta.get("t_sent"),
            "t_first_reply": meta.get("t_first_reply"),
            "t_done": meta.get("t_done"),
            "persisted_at": time.time(),
        }

        with self._connect() as con:
            con.execute(
                """
                INSERT OR REPLACE INTO ask_sessions (
                    ask_session_id, channel, prompt, chosen_answer_id, sentence,
                    replies_json, slot_evidence_json, slots_json,
                    t_sent, t_first_reply, t_done, persisted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["ask_session_id"],
                    record["channel"],
                    record["prompt"],
                    record["chosen_answer_id"],
                    record["sentence"],
                    json.dumps(record["replies"]),
                    json.dumps(record["slot_evidence"]),
                    json.dumps(record["slots"]),
                    record["t_sent"],
                    record["t_first_reply"],
                    record["t_done"],
                    record["persisted_at"],
                ),
            )
        return ask_session_id

    def get_ask_session(self, ask_session_id: str) -> AskSessionRecord | None:
        with self._connect() as con:
            row = con.execute(
                """
                SELECT ask_session_id, channel, prompt, chosen_answer_id, sentence,
                       replies_json, slot_evidence_json, slots_json,
                       t_sent, t_first_reply, t_done, persisted_at
                FROM ask_sessions WHERE ask_session_id = ?
                """,
                (ask_session_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "ask_session_id": row[0],
            "channel": row[1],
            "prompt": row[2],
            "chosen_answer_id": row[3],
            "sentence": row[4],
            "replies": json.loads(row[5]),
            "slot_evidence": json.loads(row[6]),
            "slots": json.loads(row[7]),
            "t_sent": row[8],
            "t_first_reply": row[9],
            "t_done": row[10],
            "persisted_at": row[11],
        }

    def clear_ask_sessions(self) -> None:
        with self._connect() as con:
            con.execute("DELETE FROM ask_sessions")

    def begin_schema_draft(
        self,
        *,
        schema_name: str,
        partial_input: Mapping[str, Any],
        required_fields: list[str],
        created_at: str,
    ) -> str:
        draft_id = uuid.uuid4().hex
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO schema_drafts (
                    draft_id, schema_name, partial_input_json, required_fields_json
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    draft_id,
                    schema_name,
                    json.dumps(dict(partial_input)),
                    json.dumps(required_fields),
                ),
            )
            con.execute(
                "INSERT INTO draft_transitions (draft_id, state, at) VALUES (?, ?, ?)",
                (draft_id, "created", created_at),
            )
        return draft_id

    def record_draft_transition(self, *, draft_id: str, state: str, at: str) -> None:
        with self._connect() as con:
            con.execute(
                "INSERT INTO draft_transitions (draft_id, state, at) VALUES (?, ?, ?)",
                (draft_id, state, at),
            )

    def persist_stage_timestamp(self, *, draft_id: str, stage: str, at: str) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO draft_stage_timestamps (draft_id, stage, at)
                VALUES (?, ?, ?)
                ON CONFLICT(draft_id, stage) DO UPDATE SET at = excluded.at
                """,
                (draft_id, stage, at),
            )

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
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO question_episodes (
                    draft_id, question_id, field_path, status,
                    status_history_json, planned_at, asked_at,
                    answered_at, applied_at, ask_session_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    draft_id,
                    question_id,
                    field_path,
                    status,
                    json.dumps([dict(item) for item in status_history]),
                    planned_at,
                    asked_at,
                    answered_at,
                    applied_at,
                    ask_session_id,
                ),
            )

    def persist_evidence(
        self, *, draft_id: str, field_path: str, evidence: Mapping[str, Any]
    ) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO draft_evidence (draft_id, field_path, evidence_json)
                VALUES (?, ?, ?)
                ON CONFLICT(draft_id, field_path)
                DO UPDATE SET evidence_json = excluded.evidence_json
                """,
                (draft_id, field_path, json.dumps(dict(evidence))),
            )

    def persist_unresolved_snapshot(
        self,
        *,
        draft_id: str,
        stage: str,
        unresolved_fields: list[str],
        captured_at: str,
    ) -> None:
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO draft_unresolved_snapshots (
                    draft_id, stage, unresolved_fields_json, captured_at
                ) VALUES (?, ?, ?, ?)
                """,
                (draft_id, stage, json.dumps(unresolved_fields), captured_at),
            )

    def persist_finalized_schema(
        self,
        *,
        draft_id: str,
        final_object: Mapping[str, Any] | None,
        rationale: Mapping[str, Any],
    ) -> None:
        with self._connect() as con:
            con.execute(
                """
                UPDATE schema_drafts
                SET final_object_json = ?, rationale_json = ?
                WHERE draft_id = ?
                """,
                (
                    json.dumps(dict(final_object)) if final_object is not None else None,
                    json.dumps(dict(rationale)),
                    draft_id,
                ),
            )

    def get_draft_transitions(self, draft_id: str) -> list[tuple[str, str]]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT state, at FROM draft_transitions WHERE draft_id = ? ORDER BY id",
                (draft_id,),
            ).fetchall()
        return [(row[0], row[1]) for row in rows]
