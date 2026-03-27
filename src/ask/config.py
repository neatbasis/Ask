from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping


def normalize_rest_api_url(url: str) -> str:
    url = url.rstrip("/")
    if not url.endswith("/api"):
        url += "/api"
    return url + "/"


def derive_ws_url(rest_api_url: str) -> str:
    rest = normalize_rest_api_url(rest_api_url)
    if rest.startswith("https://"):
        ws_base = "wss://" + rest[len("https://") :]
    elif rest.startswith("http://"):
        ws_base = "ws://" + rest[len("http://") :]
    else:
        ws_base = "ws://" + rest
    return ws_base.rstrip("/") + "/websocket"


def parse_ha_action(action: str) -> tuple[str, str]:
    candidate = action.strip()
    if not candidate:
        raise ValueError("invalid_ha_action:empty")
    if "." not in candidate:
        raise ValueError("invalid_ha_action:expected_domain_dot_service")
    domain, service = candidate.split(".", 1)
    if not domain or not service:
        raise ValueError("invalid_ha_action:expected_domain_dot_service")
    return domain, service


@dataclass(init=False)
class Config:
    ha_api_url: str | None
    ha_api_token: str | None
    notify_action: str | None
    satellite_entity_id: str | None
    discord_turn_service_url: str | None

    def __init__(
        self,
        ha_api_url: str | None = None,
        ha_api_token: str | None = None,
        *,
        api_url: str | None = None,
        token: str | None = None,
        notify_action: str | None = None,
        satellite_entity_id: str | None = None,
        discord_turn_service_url: str | None = None,
    ) -> None:
        self.ha_api_url = ha_api_url if ha_api_url is not None else api_url
        self.ha_api_token = ha_api_token if ha_api_token is not None else token
        self.notify_action = notify_action
        self.satellite_entity_id = satellite_entity_id
        self.discord_turn_service_url = discord_turn_service_url
        self.__post_init__()

    @property
    def api_url(self) -> str | None:
        """Compatibility alias; prefer `ha_api_url`."""
        return self.ha_api_url

    @api_url.setter
    def api_url(self, value: str | None) -> None:
        self.ha_api_url = value

    @property
    def token(self) -> str | None:
        """Compatibility alias; prefer `ha_api_token`."""
        return self.ha_api_token

    @token.setter
    def token(self, value: str | None) -> None:
        self.ha_api_token = value

    def __post_init__(self) -> None:
        if self.ha_api_url:
            self.ha_api_url = normalize_rest_api_url(self.ha_api_url)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Config":
        env = environ if environ is not None else os.environ
        return cls(
            ha_api_url=env.get("HA_API_URL"),
            ha_api_token=env.get("HA_API_TOKEN") or env.get("HA_API_SECRET"),
            notify_action=env.get("HA_NOTIFY_ACTION"),
            satellite_entity_id=env.get("HA_SATELLITE_ENTITY_ID"),
            discord_turn_service_url=env.get("DISCORD_TURN_SERVICE_URL"),
        )

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Config":
        return cls(
            ha_api_url=data.get("ha_api_url") if data.get("ha_api_url") is not None else data.get("api_url"),
            ha_api_token=data.get("ha_api_token") if data.get("ha_api_token") is not None else data.get("token"),
            notify_action=data.get("notify_action"),
            satellite_entity_id=data.get("satellite_entity_id"),
            discord_turn_service_url=data.get("discord_turn_service_url"),
        )

    def to_dict(self) -> dict[str, str | None]:
        return {
            "ha_api_url": self.ha_api_url,
            "ha_api_token": self.ha_api_token,
            "api_url": self.ha_api_url,
            "token": self.ha_api_token,
            "notify_action": self.notify_action,
            "satellite_entity_id": self.satellite_entity_id,
            "discord_turn_service_url": self.discord_turn_service_url,
        }


def load_config() -> dict[str, str | None]:
    """Deprecated compatibility wrapper; prefer `Config.from_env()`.

    This function is kept during migration from free-function config loading.
    """

    return Config.from_env().to_dict()
