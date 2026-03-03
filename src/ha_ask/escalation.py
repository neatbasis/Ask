from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Sequence

from .errors import ERR_TIMEOUT
from .types import AskResult


@dataclass(frozen=True)
class EscalationState:
    retries: Dict[str, int] = field(default_factory=dict)
    consecutive_timeouts: int = 0


def record_attempt(state: EscalationState, channel: str, result: AskResult) -> EscalationState:
    retries = dict(state.retries)
    retries[channel] = retries.get(channel, 0) + 1
    if result.get("error") == ERR_TIMEOUT:
        timeouts = state.consecutive_timeouts + 1
    else:
        timeouts = 0
    return EscalationState(retries=retries, consecutive_timeouts=timeouts)


def choose_next_channel(
    *,
    current_channel: str,
    state: EscalationState,
    available_channels: Sequence[str] = ("mobile", "discord", "satellite"),
    max_retries_per_channel: int = 2,
    escalate_on_timeout: int = 1,
) -> Optional[str]:
    if current_channel not in available_channels:
        return available_channels[0] if available_channels else None

    current_retries = state.retries.get(current_channel, 0)
    should_escalate = (
        current_retries >= max_retries_per_channel
        or state.consecutive_timeouts >= escalate_on_timeout
    )
    if not should_escalate:
        return current_channel

    for channel in _iter_channels_after(current_channel, available_channels):
        if state.retries.get(channel, 0) < max_retries_per_channel:
            return channel

    return None


def _iter_channels_after(current_channel: str, available_channels: Sequence[str]) -> Iterable[str]:
    idx = available_channels.index(current_channel)
    for channel in available_channels[idx + 1 :]:
        yield channel
