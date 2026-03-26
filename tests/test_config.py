from ha_ask.config import Config, derive_ws_url, normalize_rest_api_url


def test_config_direct_construction_normalizes_url():
    cfg = Config(api_url="http://ha.local", token="abc")

    assert cfg.api_url == "http://ha.local/api/"
    assert cfg.token == "abc"


def test_config_from_env_uses_mapping():
    env = {
        "HA_API_URL": "https://ha.example",
        "HA_API_SECRET": "secret",
        "HA_NOTIFY_ACTION": "notify.mobile_app_phone",
        "HA_SATELLITE_ENTITY_ID": "assist_satellite.kitchen",
        "DISCORD_TURN_SERVICE_URL": "http://discord-turn.local",
    }

    cfg = Config.from_env(env)

    assert cfg.api_url == "https://ha.example/api/"
    assert cfg.token == "secret"
    assert cfg.notify_action == "notify.mobile_app_phone"
    assert cfg.satellite_entity_id == "assist_satellite.kitchen"
    assert cfg.discord_turn_service_url == "http://discord-turn.local"


def test_config_optional_fields_default_to_none():
    cfg = Config.from_mapping({"api_url": "http://ha.local", "token": "secret"})

    assert cfg.notify_action is None
    assert cfg.satellite_entity_id is None
    assert cfg.discord_turn_service_url is None


def test_config_mapping_and_to_dict_include_discord_turn_service_url():
    cfg = Config.from_mapping(
        {
            "api_url": "http://ha.local",
            "token": "secret",
            "discord_turn_service_url": "http://discord-turn.local",
        }
    )

    assert cfg.discord_turn_service_url == "http://discord-turn.local"
    assert cfg.to_dict()["discord_turn_service_url"] == "http://discord-turn.local"


def test_url_helpers_normalize_and_derive_ws():
    assert normalize_rest_api_url("http://ha.local") == "http://ha.local/api/"
    assert normalize_rest_api_url("http://ha.local/api") == "http://ha.local/api/"
    assert derive_ws_url("https://ha.local") == "wss://ha.local/api/websocket"
