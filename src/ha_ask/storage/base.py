from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from ha_ask.types import AskResult, AskSessionRecord, AskSpec


class StorageBackend(ABC):
    @abstractmethod
    def persist_ask_session(self, *, channel: str, spec: AskSpec, result: AskResult) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_ask_session(self, ask_session_id: str) -> AskSessionRecord | None:
        raise NotImplementedError

    @abstractmethod
    def clear_ask_sessions(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def begin_schema_draft(
        self,
        *,
        schema_name: str,
        partial_input: Mapping[str, Any],
        required_fields: list[str],
        created_at: str,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def record_draft_transition(self, *, draft_id: str, state: str, at: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def persist_evidence(
        self, *, draft_id: str, field_path: str, evidence: Mapping[str, Any]
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def persist_finalized_schema(
        self,
        *,
        draft_id: str,
        final_object: Mapping[str, Any] | None,
        rationale: Mapping[str, Any],
    ) -> None:
        raise NotImplementedError
