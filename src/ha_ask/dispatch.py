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
    api_url: Optional[str] = None,
    token: Optional[str] = None,
    notify_action: Optional[str] = None,
    discord_action: Optional[str] = None,
    satellite_entity_id: Optional[str] = None,
) -> AskResult:
    result: AskResult

    if channel == "terminal":
        result = terminal_chan.ask_question(spec)
    elif channel == "satellite":
        if not api_url or not token:
            result = _MISSING_HA_CREDS_RESULT.copy()
        else:
            rest = normalize_rest_api_url(api_url)
            with Client(rest, token) as client:
                result = satellite_chan.ask_question(client, spec, entity_id=satellite_entity_id)
    elif channel == "mobile":
        if not notify_action:
            result = {"id": None, "sentence": None, "slots": {}, "meta": {}, "error": "missing_notify_action"}
        elif not api_url or not token:
            result = _MISSING_HA_CREDS_RESULT.copy()
        else:
            rest = normalize_rest_api_url(api_url)
            ws_url = derive_ws_url(api_url)
            with Client(rest, token) as client, WebsocketClient(ws_url, token) as ws:
                result = mobile_chan.ask_question(client, ws, spec, notify_action=notify_action)
    elif channel == "discord":
        service = discord_action or notify_action
        if not service:
            result = {"id": None, "sentence": None, "slots": {}, "meta": {}, "error": "missing_discord_action"}
        elif not api_url or not token:
            result = _MISSING_HA_CREDS_RESULT.copy()
        else:
            rest = normalize_rest_api_url(api_url)
            ws_url = derive_ws_url(api_url)
            with Client(rest, token) as client, WebsocketClient(ws_url, token) as ws:
                result = discord_chan.ask_question(client, ws, spec, notify_action=service)
    else:
        result = {"id": None, "sentence": None, "slots": {}, "meta": {}, "error": f"unknown_channel:{channel}"}

    persist_ask_session(channel=channel, spec=spec, result=result)
    return result


async def ask_question_async(
    *,
    channel: Channel,
    spec: AskSpec,
    api_url: Optional[str] = None,
    token: Optional[str] = None,
    notify_action: Optional[str] = None,
    discord_action: Optional[str] = None,
    satellite_entity_id: Optional[str] = None,
) -> AskResult:
    return await asyncio.to_thread(
        ask_question,
        channel=channel,
        spec=spec,
        api_url=api_url,
        token=token,
        notify_action=notify_action,
        discord_action=discord_action,
        satellite_entity_id=satellite_entity_id,
    )


def ask_choice(
    *,
    channel: Channel,
    question: str,
    choices: Sequence[Answer],
    api_url: Optional[str] = None,
    token: Optional[str] = None,
    notify_action: Optional[str] = None,
    discord_action: Optional[str] = None,
    satellite_entity_id: Optional[str] = None,
    allow_replies: bool = False,
    timeout_s: float = 180.0,
    title: Optional[str] = None,
) -> AskResult:
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
        api_url=api_url,
        token=token,
        notify_action=notify_action,
        discord_action=discord_action,
        satellite_entity_id=satellite_entity_id,
    )


async def ask_choice_async(
    *,
    channel: Channel,
    question: str,
    choices: Sequence[Answer],
    api_url: Optional[str] = None,
    token: Optional[str] = None,
    notify_action: Optional[str] = None,
    discord_action: Optional[str] = None,
    satellite_entity_id: Optional[str] = None,
    allow_replies: bool = False,
    timeout_s: float = 180.0,
    title: Optional[str] = None,
) -> AskResult:
    return await asyncio.to_thread(
        ask_choice,
        channel=channel,
        question=question,
        choices=choices,
        api_url=api_url,
        token=token,
        notify_action=notify_action,
        discord_action=discord_action,
        satellite_entity_id=satellite_entity_id,
        allow_replies=allow_replies,
        timeout_s=timeout_s,
        title=title,
    )


def ask_freeform(
    *,
    channel: Channel,
    question: str,
    api_url: Optional[str] = None,
    token: Optional[str] = None,
    notify_action: Optional[str] = None,
    discord_action: Optional[str] = None,
    satellite_entity_id: Optional[str] = None,
    expected_slots: Optional[Sequence[str]] = None,
    slot_schema: Optional[dict] = None,
    timeout_s: float = 180.0,
    title: Optional[str] = None,
) -> AskResult:
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
        api_url=api_url,
        token=token,
        notify_action=notify_action,
        discord_action=discord_action,
        satellite_entity_id=satellite_entity_id,
    )


async def ask_freeform_async(
    *,
    channel: Channel,
    question: str,
    api_url: Optional[str] = None,
    token: Optional[str] = None,
    notify_action: Optional[str] = None,
    discord_action: Optional[str] = None,
    satellite_entity_id: Optional[str] = None,
    expected_slots: Optional[Sequence[str]] = None,
    slot_schema: Optional[dict] = None,
    timeout_s: float = 180.0,
    title: Optional[str] = None,
) -> AskResult:
    return await asyncio.to_thread(
        ask_freeform,
        channel=channel,
        question=question,
        api_url=api_url,
        token=token,
        notify_action=notify_action,
        discord_action=discord_action,
        satellite_entity_id=satellite_entity_id,
        expected_slots=expected_slots,
        slot_schema=slot_schema,
        timeout_s=timeout_s,
        title=title,
    )
