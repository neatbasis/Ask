from __future__ import annotations

from ask.storage import get_storage_backend
from ask.types import AskResult, AskSessionRecord, AskSpec


def persist_ask_session(*, channel: str, spec: AskSpec, result: AskResult) -> str:
    return get_storage_backend().persist_ask_session(channel=channel, spec=spec, result=result)


def get_ask_session(ask_session_id: str) -> AskSessionRecord | None:
    return get_storage_backend().get_ask_session(ask_session_id)


def clear_ask_sessions() -> None:
    get_storage_backend().clear_ask_sessions()
