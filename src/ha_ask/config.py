"""Compatibility config shim.

Canonical configuration types live in `ask.config`.
"""

from ask.config import Config, derive_ws_url, load_config, normalize_rest_api_url, parse_ha_action

__all__ = ["Config", "normalize_rest_api_url", "derive_ws_url", "parse_ha_action", "load_config"]
