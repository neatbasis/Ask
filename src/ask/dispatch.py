import asyncio
from typing import Literal, Optional, Sequence
from homeassistant_api import Client, WebsocketClient

from .types import Answer, AskSpec, AskResult
from .config import normalize_rest_api_url, derive_ws_url
from .channels import satellite as satellite_chan
from .channels import mobile as mobile_chan
from .channels import discord as discord_chan
from .channels import terminal as terminal_chan
from .session_store import persist_ask_session

Channel = Literal["terminal", "satellite", "mobile", "discord"]


_MISSING_HA_CREDS_RESULT: AskResult = {
    "id": None,
    "sentence": None,
    "slots": {},
    "meta": {},
    "error": "missing_ha_credentials",
}


def ask_question(
    *,
    channel: Channel,
    spec: AskSpec,
    ha_api_url: Optional[str] = None,
    ha_api_token: Optional[str] = None,
    api_url: Optional[str] = None,
    token: Optional[str] = None,
    notify_action: Optional[str] = None,
    discord_action: Optional[str] = None,
    discord_turn_service_url: Optional[str] = None,
    satellite_entity_id: Optional[str] = None,
) -> AskResult:
    """Dispatch an AskSpec over the selected channel.

    Args:
        channel: Transport channel (`"terminal"`, `"satellite"`, `"mobile"`, or `"discord"`).
        spec: Fully constructed ask specification.
        ha_api_url: Preferred Home Assistant base URL used by Home Assistant-backed
            channels. This remains the Home Assistant URL, not a Discord service URL.
        ha_api_token: Preferred Home Assistant long-lived token. For Discord channel
            usage this is passed through as an optional bearer token to the Discord
            turn service.
        api_url: Compatibility alias for `ha_api_url`.
        token: Compatibility alias for `ha_api_token`.
        notify_action: Home Assistant action string used for mobile notifications.
            For compatibility, Discord dispatch may also fall back to this value
            when `discord_action` is not provided.
        discord_action:
            Discord recipient reference used only when `channel="discord"`.

            Expected format:
            - "<user_id>"
            - "<user_id>:<channel_id>"

            Where:
            - `user_id` is the target Discord user snowflake
            - `channel_id` is an optional Discord DM channel snowflake

            If `channel_id` is omitted, the downstream Discord turn service may resolve
            or create the DM channel for the user.

            This is not a Home Assistant action string.

            Current compatibility behavior:
            if `discord_action` is not provided, dispatch may fall back to `notify_action`.
            Prefer supplying `discord_action` explicitly for Discord usage.
        discord_turn_service_url:
            Base URL of the DiscordTurnService instance used when `channel="discord"`.

            Example:
            - "http://discord-turn.local"
            - "https://discord-turn.example.com"

            Required for Discord channel usage.
        satellite_entity_id: Home Assistant Assist satellite entity for
            `channel="satellite"`.
    """
    result: AskResult
    resolved_api_url = ha_api_url if ha_api_url is not None else api_url
    resolved_token = ha_api_token if ha_api_token is not None else token

    if channel == "terminal":
        result = terminal_chan.ask_question(spec)
    elif channel == "satellite":
        if not resolved_api_url or not resolved_token:
            result = _MISSING_HA_CREDS_RESULT.copy()
        else:
            rest = normalize_rest_api_url(resolved_api_url)
            with Client(rest, resolved_token) as client:
                result = satellite_chan.ask_question(client, spec, entity_id=satellite_entity_id)
    elif channel == "mobile":
        if not notify_action:
            result = {"id": None, "sentence": None, "slots": {}, "meta": {}, "error": "missing_notify_action"}
        elif not resolved_api_url or not resolved_token:
            result = _MISSING_HA_CREDS_RESULT.copy()
        else:
            rest = normalize_rest_api_url(resolved_api_url)
            ws_url = derive_ws_url(resolved_api_url)
            with Client(rest, resolved_token) as client, WebsocketClient(ws_url, resolved_token) as ws:
                result = mobile_chan.ask_question(client, ws, spec, notify_action=notify_action)
    elif channel == "discord":
        recipient = discord_action or notify_action
        if not recipient:
            result = {"id": None, "sentence": None, "slots": {}, "meta": {}, "error": "missing_discord_action"}
        elif not discord_turn_service_url:
            result = {"id": None, "sentence": None, "slots": {}, "meta": {}, "error": "missing_discord_turn_url"}
        else:
            result = discord_chan.ask_question(
                spec=spec,
                service_url=discord_turn_service_url,
                recipient=recipient,
                bearer_token=resolved_token,
            )
    else:
        result = {"id": None, "sentence": None, "slots": {}, "meta": {}, "error": f"unknown_channel:{channel}"}

    persist_ask_session(channel=channel, spec=spec, result=result)
    return result


async def ask_question_async(
    *,
    channel: Channel,
    spec: AskSpec,
    ha_api_url: Optional[str] = None,
    ha_api_token: Optional[str] = None,
    api_url: Optional[str] = None,
    token: Optional[str] = None,
    notify_action: Optional[str] = None,
    discord_action: Optional[str] = None,
    discord_turn_service_url: Optional[str] = None,
    satellite_entity_id: Optional[str] = None,
) -> AskResult:
    """Async wrapper around :func:`ask_question` with identical parameters.

    Discord-specific parameters:
        - `discord_action`: Discord recipient reference for `channel="discord"`,
          not a Home Assistant action string. Accepted format is `"<user_id>"` or
          `"<user_id>:<channel_id>"`; if omitted, current compatibility behavior
          falls back to `notify_action`.
        - `discord_turn_service_url`: Base URL of the DiscordTurnService used for
          `channel="discord"` and required for Discord channel usage.
    """
    return await asyncio.to_thread(
        ask_question,
        channel=channel,
        spec=spec,
        ha_api_url=ha_api_url,
        ha_api_token=ha_api_token,
        api_url=api_url,
        token=token,
        notify_action=notify_action,
        discord_action=discord_action,
        discord_turn_service_url=discord_turn_service_url,
        satellite_entity_id=satellite_entity_id,
    )


def ask_choice(
    *,
    channel: Channel,
    question: str,
    choices: Sequence[Answer],
    ha_api_url: Optional[str] = None,
    ha_api_token: Optional[str] = None,
    api_url: Optional[str] = None,
    token: Optional[str] = None,
    notify_action: Optional[str] = None,
    discord_action: Optional[str] = None,
    discord_turn_service_url: Optional[str] = None,
    satellite_entity_id: Optional[str] = None,
    allow_replies: bool = False,
    timeout_s: float = 180.0,
    title: Optional[str] = None,
) -> AskResult:
    """Ask a multiple-choice question by building an :class:`AskSpec`.

    Parameter behavior mirrors :func:`ask_question`, including Discord routing:
        - `discord_action` is a Discord recipient reference (`"<user_id>"` or
          `"<user_id>:<channel_id>"`) used only with `channel="discord"`.
          It is not a Home Assistant action string; compatibility fallback to
          `notify_action` still applies when `discord_action` is omitted.
        - `discord_turn_service_url` is the DiscordTurnService base URL used only
          when `channel="discord"` and is required for Discord channel usage.
        - `ha_api_url` / `ha_api_token` are the preferred Home Assistant transport names.
        - `api_url` / `token` remain compatibility aliases.
    """
    spec = AskSpec(
        question=question,
        answers=choices,
        allow_replies=allow_replies,
        timeout_s=timeout_s,
        title=title,
    )
    return ask_question(
        channel=channel,
        spec=spec,
        ha_api_url=ha_api_url,
        ha_api_token=ha_api_token,
        api_url=api_url,
        token=token,
        notify_action=notify_action,
        discord_action=discord_action,
        discord_turn_service_url=discord_turn_service_url,
        satellite_entity_id=satellite_entity_id,
    )


async def ask_choice_async(
    *,
    channel: Channel,
    question: str,
    choices: Sequence[Answer],
    ha_api_url: Optional[str] = None,
    ha_api_token: Optional[str] = None,
    api_url: Optional[str] = None,
    token: Optional[str] = None,
    notify_action: Optional[str] = None,
    discord_action: Optional[str] = None,
    discord_turn_service_url: Optional[str] = None,
    satellite_entity_id: Optional[str] = None,
    allow_replies: bool = False,
    timeout_s: float = 180.0,
    title: Optional[str] = None,
) -> AskResult:
    """Async wrapper around :func:`ask_choice` with identical parameters.

    For `channel="discord"`, provide `discord_action` as a Discord recipient
    reference (`"<user_id>"` or `"<user_id>:<channel_id>"`) and set
    `discord_turn_service_url` to the DiscordTurnService base URL.
    """
    return await asyncio.to_thread(
        ask_choice,
        channel=channel,
        question=question,
        choices=choices,
        ha_api_url=ha_api_url,
        ha_api_token=ha_api_token,
        api_url=api_url,
        token=token,
        notify_action=notify_action,
        discord_action=discord_action,
        discord_turn_service_url=discord_turn_service_url,
        satellite_entity_id=satellite_entity_id,
        allow_replies=allow_replies,
        timeout_s=timeout_s,
        title=title,
    )


def ask_freeform(
    *,
    channel: Channel,
    question: str,
    ha_api_url: Optional[str] = None,
    ha_api_token: Optional[str] = None,
    api_url: Optional[str] = None,
    token: Optional[str] = None,
    notify_action: Optional[str] = None,
    discord_action: Optional[str] = None,
    discord_turn_service_url: Optional[str] = None,
    satellite_entity_id: Optional[str] = None,
    expected_slots: Optional[Sequence[str]] = None,
    slot_schema: Optional[dict] = None,
    timeout_s: float = 180.0,
    title: Optional[str] = None,
) -> AskResult:
    """Ask a free-form question by building an :class:`AskSpec`.

    Parameter behavior mirrors :func:`ask_question`. In particular for Discord:
        - `discord_action` is the Discord recipient reference (not a Home Assistant
          action string), in format `"<user_id>"` or `"<user_id>:<channel_id>"`.
          If omitted, current compatibility behavior may fall back to `notify_action`.
        - `discord_turn_service_url` is the DiscordTurnService base URL required
          when `channel="discord"`.
        - `ha_api_url` / `ha_api_token` are the preferred Home Assistant transport names.
        - `api_url` / `token` remain compatibility aliases.
    """
    spec = AskSpec(
        question=question,
        expected_slots=expected_slots,
        slot_schema=slot_schema,
        expect_reply=True,
        allow_replies=True,
        timeout_s=timeout_s,
        title=title,
    )
    return ask_question(
        channel=channel,
        spec=spec,
        ha_api_url=ha_api_url,
        ha_api_token=ha_api_token,
        api_url=api_url,
        token=token,
        notify_action=notify_action,
        discord_action=discord_action,
        discord_turn_service_url=discord_turn_service_url,
        satellite_entity_id=satellite_entity_id,
    )


async def ask_freeform_async(
    *,
    channel: Channel,
    question: str,
    ha_api_url: Optional[str] = None,
    ha_api_token: Optional[str] = None,
    api_url: Optional[str] = None,
    token: Optional[str] = None,
    notify_action: Optional[str] = None,
    discord_action: Optional[str] = None,
    discord_turn_service_url: Optional[str] = None,
    satellite_entity_id: Optional[str] = None,
    expected_slots: Optional[Sequence[str]] = None,
    slot_schema: Optional[dict] = None,
    timeout_s: float = 180.0,
    title: Optional[str] = None,
) -> AskResult:
    """Async wrapper around :func:`ask_freeform` with identical parameters.

    Discord channel usage expects:
        - `discord_action` as a Discord recipient reference (`"<user_id>"` or
          `"<user_id>:<channel_id>"`; falls back to `notify_action` for compatibility)
        - `discord_turn_service_url` as the required DiscordTurnService base URL
    """
    return await asyncio.to_thread(
        ask_freeform,
        channel=channel,
        question=question,
        ha_api_url=ha_api_url,
        ha_api_token=ha_api_token,
        api_url=api_url,
        token=token,
        notify_action=notify_action,
        discord_action=discord_action,
        discord_turn_service_url=discord_turn_service_url,
        satellite_entity_id=satellite_entity_id,
        expected_slots=expected_slots,
        slot_schema=slot_schema,
        timeout_s=timeout_s,
        title=title,
    )
