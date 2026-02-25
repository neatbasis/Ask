from typing import Any, Dict, Optional, Tuple
from homeassistant_api import Client, WebsocketClient
from homeassistant_api.processing import Processing, process_json
import homeassistant_api.errors as ha_errors
from .errors import ERR_NO_RESPONSE

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

def call_service_no_response(client: Client, domain: str, service: str, **service_data) -> Tuple[bool, Optional[str]]:
    try:
        client.trigger_service(domain, service, **service_data)
        return True, None
    except BaseHAError as e:
        is_500 = InternalServerError is not None and isinstance(e, InternalServerError)
        return False, (ERR_NO_RESPONSE if is_500 else f"{type(e).__name__}: {e}")

def call_service_with_response(client: Client, domain: str, service: str, **service_data) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    try:
        _result, data = client.trigger_service_with_response(domain, service, **service_data)
        if not isinstance(data, dict):
            data = {}
        return True, data, None
    except BaseHAError as e:
        is_500 = InternalServerError is not None and isinstance(e, InternalServerError)
        return False, {}, (ERR_NO_RESPONSE if is_500 else f"{type(e).__name__}: {e}")
