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


@dataclass
class Config:
    api_url: str | None
    token: str | None
    notify_action: str | None = None
    satellite_entity_id: str | None = None

    def __post_init__(self) -> None:
        if self.api_url:
            self.api_url = normalize_rest_api_url(self.api_url)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Config":
        env = environ if environ is not None else os.environ
        return cls(
            api_url=env.get("HA_API_URL"),
            token=env.get("HA_API_SECRET"),
            notify_action=env.get("HA_NOTIFY_ACTION"),
            satellite_entity_id=env.get("HA_SATELLITE_ENTITY_ID"),
        )

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Config":
        return cls(
            api_url=data.get("api_url"),
            token=data.get("token"),
            notify_action=data.get("notify_action"),
            satellite_entity_id=data.get("satellite_entity_id"),
        )

    def to_dict(self) -> dict[str, str | None]:
        return {
            "api_url": self.api_url,
            "token": self.token,
            "notify_action": self.notify_action,
            "satellite_entity_id": self.satellite_entity_id,
        }


def load_config() -> dict[str, str | None]:
    """Deprecated compatibility wrapper; prefer `Config.from_env()`.

    This function is kept during migration from free-function config loading.
    """

    return Config.from_env().to_dict()
