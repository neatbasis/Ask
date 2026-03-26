from typing import Any, Dict, Optional, Sequence, Tuple
from homeassistant_api import Client as HAClient, WebsocketClient
from homeassistant_api.processing import Processing, process_json
import homeassistant_api.errors as ha_errors
from .errors import ERR_NO_RESPONSE
from .config import Config
from .types import Answer, AskResult, AskSpec

Channel = str

# processors
@Processing.processor("application/json")
def _json_processor(response):
    return process_json(response)

@Processing.processor("text/html")
def _html_processor(response):
    return response.text

@Processing.processor("text/plain")
def _text_processor(response):
    return response.text

InternalServerError = getattr(ha_errors, "InternalServerError", None)
BaseHAError = (
    getattr(ha_errors, "HomeAssistantAPIError", None)
    or getattr(ha_errors, "HomeAssistantApiError", None)
    or getattr(ha_errors, "HomeAssistantError", None)
    or getattr(ha_errors, "ClientError", None)
    or getattr(ha_errors, "ServerError", None)
    or Exception
)

def call_service_no_response(client: HAClient, domain: str, service: str, **service_data) -> Tuple[bool, Optional[str]]:
    try:
        client.trigger_service(domain, service, **service_data)
        return True, None
    except BaseHAError as e:
        is_500 = InternalServerError is not None and isinstance(e, InternalServerError)
        return False, (ERR_NO_RESPONSE if is_500 else f"{type(e).__name__}: {e}")

def call_service_with_response(client: HAClient, domain: str, service: str, **service_data) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    try:
        _result, data = client.trigger_service_with_response(domain, service, **service_data)
        if not isinstance(data, dict):
            data = {}
        return True, data, None
    except BaseHAError as e:
        is_500 = InternalServerError is not None and isinstance(e, InternalServerError)
        return False, {}, (ERR_NO_RESPONSE if is_500 else f"{type(e).__name__}: {e}")


class AskClient:
    """Configured object API for Ask dispatch calls.

    The client owns long-lived transport configuration and allows per-call overrides
    for channel recipient and transport fields.
    """

    def __init__(self, config: Config) -> None:
        self.config = config

    def ask_question(
        self,
        *,
        channel: Channel,
        spec: AskSpec,
        api_url: Optional[str] = None,
        token: Optional[str] = None,
        notify_action: Optional[str] = None,
        discord_action: Optional[str] = None,
        discord_turn_service_url: Optional[str] = None,
        satellite_entity_id: Optional[str] = None,
    ) -> AskResult:
        from .dispatch import ask_question

        return ask_question(
            channel=channel,
            spec=spec,
            api_url=api_url if api_url is not None else self.config.ha_api_url,
            token=token if token is not None else self.config.ha_api_token,
            notify_action=notify_action if notify_action is not None else self.config.notify_action,
            discord_action=discord_action,
            discord_turn_service_url=(
                discord_turn_service_url
                if discord_turn_service_url is not None
                else self.config.discord_turn_service_url
            ),
            satellite_entity_id=(
                satellite_entity_id
                if satellite_entity_id is not None
                else self.config.satellite_entity_id
            ),
        )

    async def ask_question_async(
        self,
        *,
        channel: Channel,
        spec: AskSpec,
        api_url: Optional[str] = None,
        token: Optional[str] = None,
        notify_action: Optional[str] = None,
        discord_action: Optional[str] = None,
        discord_turn_service_url: Optional[str] = None,
        satellite_entity_id: Optional[str] = None,
    ) -> AskResult:
        from .dispatch import ask_question_async

        return await ask_question_async(
            channel=channel,
            spec=spec,
            api_url=api_url if api_url is not None else self.config.ha_api_url,
            token=token if token is not None else self.config.ha_api_token,
            notify_action=notify_action if notify_action is not None else self.config.notify_action,
            discord_action=discord_action,
            discord_turn_service_url=(
                discord_turn_service_url
                if discord_turn_service_url is not None
                else self.config.discord_turn_service_url
            ),
            satellite_entity_id=(
                satellite_entity_id
                if satellite_entity_id is not None
                else self.config.satellite_entity_id
            ),
        )

    def ask_choice(
        self,
        *,
        channel: Channel,
        question: str,
        choices: Sequence[Answer],
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
        from .dispatch import ask_choice

        return ask_choice(
            channel=channel,
            question=question,
            choices=choices,
            api_url=api_url if api_url is not None else self.config.ha_api_url,
            token=token if token is not None else self.config.ha_api_token,
            notify_action=notify_action if notify_action is not None else self.config.notify_action,
            discord_action=discord_action,
            discord_turn_service_url=(
                discord_turn_service_url
                if discord_turn_service_url is not None
                else self.config.discord_turn_service_url
            ),
            satellite_entity_id=(
                satellite_entity_id
                if satellite_entity_id is not None
                else self.config.satellite_entity_id
            ),
            allow_replies=allow_replies,
            timeout_s=timeout_s,
            title=title,
        )

    async def ask_choice_async(
        self,
        *,
        channel: Channel,
        question: str,
        choices: Sequence[Answer],
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
        from .dispatch import ask_choice_async

        return await ask_choice_async(
            channel=channel,
            question=question,
            choices=choices,
            api_url=api_url if api_url is not None else self.config.ha_api_url,
            token=token if token is not None else self.config.ha_api_token,
            notify_action=notify_action if notify_action is not None else self.config.notify_action,
            discord_action=discord_action,
            discord_turn_service_url=(
                discord_turn_service_url
                if discord_turn_service_url is not None
                else self.config.discord_turn_service_url
            ),
            satellite_entity_id=(
                satellite_entity_id
                if satellite_entity_id is not None
                else self.config.satellite_entity_id
            ),
            allow_replies=allow_replies,
            timeout_s=timeout_s,
            title=title,
        )

    def ask_freeform(
        self,
        *,
        channel: Channel,
        question: str,
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
        from .dispatch import ask_freeform

        return ask_freeform(
            channel=channel,
            question=question,
            api_url=api_url if api_url is not None else self.config.ha_api_url,
            token=token if token is not None else self.config.ha_api_token,
            notify_action=notify_action if notify_action is not None else self.config.notify_action,
            discord_action=discord_action,
            discord_turn_service_url=(
                discord_turn_service_url
                if discord_turn_service_url is not None
                else self.config.discord_turn_service_url
            ),
            satellite_entity_id=(
                satellite_entity_id
                if satellite_entity_id is not None
                else self.config.satellite_entity_id
            ),
            expected_slots=expected_slots,
            slot_schema=slot_schema,
            timeout_s=timeout_s,
            title=title,
        )

    async def ask_freeform_async(
        self,
        *,
        channel: Channel,
        question: str,
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
        from .dispatch import ask_freeform_async

        return await ask_freeform_async(
            channel=channel,
            question=question,
            api_url=api_url if api_url is not None else self.config.ha_api_url,
            token=token if token is not None else self.config.ha_api_token,
            notify_action=notify_action if notify_action is not None else self.config.notify_action,
            discord_action=discord_action,
            discord_turn_service_url=(
                discord_turn_service_url
                if discord_turn_service_url is not None
                else self.config.discord_turn_service_url
            ),
            satellite_entity_id=(
                satellite_entity_id
                if satellite_entity_id is not None
                else self.config.satellite_entity_id
            ),
            expected_slots=expected_slots,
            slot_schema=slot_schema,
            timeout_s=timeout_s,
            title=title,
        )
