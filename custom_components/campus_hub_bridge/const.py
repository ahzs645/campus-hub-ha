"""Constants for the Campus Hub Bridge integration."""

from __future__ import annotations

DOMAIN = "campus_hub_bridge"
NAME = "Campus Hub Bridge"
VERSION = "0.1.0"

CONF_API_TOKEN = "api_token"
CONF_CAMPUS_HUB_URL = "campus_hub_url"
CONF_INCLUDED_DOMAINS = "included_domains"
CONF_ENTITY_ALLOWLIST = "entity_allowlist"
CONF_EXPOSE_ATTRIBUTES = "expose_attributes"

DEFAULT_NAME = "Campus Hub"
DEFAULT_INCLUDED_DOMAINS = [
    "sensor",
    "binary_sensor",
    "camera",
    "media_player",
    "weather",
    "light",
    "switch",
]
DEFAULT_EXPOSE_ATTRIBUTES = True

HEALTH_URL = "/api/campus_hub_bridge/health"
ENTITIES_URL = "/api/campus_hub_bridge/entities"
STATE_URL = "/api/campus_hub_bridge/state"

