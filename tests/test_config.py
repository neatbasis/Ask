from ha_ask.config import Config, derive_ws_url, normalize_rest_api_url


def test_config_direct_construction_preferred_names_normalize_url():
    cfg = Config(ha_api_url="http://ha.local", ha_api_token="abc")

    assert cfg.ha_api_url == "http://ha.local/api/"
    assert cfg.ha_api_token == "abc"


def test_config_direct_construction_legacy_names_still_work():
    cfg = Config(api_url="http://ha.local", token="legacy")

    assert cfg.ha_api_url == "http://ha.local/api/"
    assert cfg.ha_api_token == "legacy"
    assert cfg.api_url == "http://ha.local/api/"
    assert cfg.token == "legacy"


def test_config_from_env_uses_mapping_and_ha_token_alias():
    env = {
        "HA_API_URL": "https://ha.example",
        "HA_API_TOKEN": "token-preferred",
        "HA_API_SECRET": "token-legacy",
        "HA_NOTIFY_ACTION": "notify.mobile_app_phone",
        "HA_SATELLITE_ENTITY_ID": "assist_satellite.kitchen",
        "DISCORD_TURN_SERVICE_URL": "http://discord-turn.local",
    }

    cfg = Config.from_env(env)

    assert cfg.ha_api_url == "https://ha.example/api/"
    assert cfg.ha_api_token == "token-preferred"
    assert cfg.notify_action == "notify.mobile_app_phone"
    assert cfg.satellite_entity_id == "assist_satellite.kitchen"
    assert cfg.discord_turn_service_url == "http://discord-turn.local"


def test_config_optional_fields_default_to_none():
    cfg = Config.from_mapping({"ha_api_url": "http://ha.local", "ha_api_token": "secret"})

    assert cfg.notify_action is None
    assert cfg.satellite_entity_id is None
    assert cfg.discord_turn_service_url is None


def test_config_from_mapping_accepts_both_styles_and_prefers_new_keys():
    cfg = Config.from_mapping(
        {
            "ha_api_url": "https://preferred.example",
            "ha_api_token": "preferred-token",
            "api_url": "https://legacy.example",
            "token": "legacy-token",
            "discord_turn_service_url": "http://discord-turn.local",
        }
    )

    assert cfg.ha_api_url == "https://preferred.example/api/"
    assert cfg.ha_api_token == "preferred-token"
    payload = cfg.to_dict()
    assert payload["ha_api_url"] == "https://preferred.example/api/"
    assert payload["api_url"] == "https://preferred.example/api/"
    assert payload["ha_api_token"] == "preferred-token"
    assert payload["token"] == "preferred-token"
    assert payload["discord_turn_service_url"] == "http://discord-turn.local"


def test_url_helpers_normalize_and_derive_ws():
    assert normalize_rest_api_url("http://ha.local") == "http://ha.local/api/"
    assert normalize_rest_api_url("http://ha.local/api") == "http://ha.local/api/"
    assert derive_ws_url("https://ha.local") == "wss://ha.local/api/websocket"
