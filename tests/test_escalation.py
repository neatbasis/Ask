from ha_ask.escalation import EscalationState, choose_next_channel, record_attempt
from ha_ask.errors import ERR_TIMEOUT


def test_escalation_moves_to_next_channel_after_timeout():
    state = EscalationState()
    timeout_result = {"id": None, "sentence": None, "slots": {}, "meta": {}, "error": ERR_TIMEOUT}
    state = record_attempt(state, "mobile", timeout_result)

    next_channel = choose_next_channel(current_channel="mobile", state=state)

    assert next_channel == "discord"


def test_escalation_stays_on_same_channel_before_limits():
    state = EscalationState(retries={"mobile": 1}, consecutive_timeouts=0)

    next_channel = choose_next_channel(
        current_channel="mobile",
        state=state,
        max_retries_per_channel=2,
        escalate_on_timeout=2,
    )

    assert next_channel == "mobile"


def test_escalation_returns_none_when_all_channels_exhausted():
    state = EscalationState(retries={"mobile": 3, "discord": 3, "satellite": 3}, consecutive_timeouts=3)

    next_channel = choose_next_channel(current_channel="mobile", state=state, max_retries_per_channel=2)

    assert next_channel is None
