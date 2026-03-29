"""HTTP API views for Campus Hub Bridge."""

from __future__ import annotations

import hmac
from typing import Any

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State, callback

from .const import (
    CONF_API_TOKEN,
    CONF_CAMPUS_HUB_URL,
    CONF_ENTITY_ALLOWLIST,
    CONF_EXPOSE_ATTRIBUTES,
    CONF_INCLUDED_DOMAINS,
    DEFAULT_EXPOSE_ATTRIBUTES,
    DEFAULT_INCLUDED_DOMAINS,
    DOMAIN,
    ENTITIES_URL,
    HEALTH_URL,
    NAME,
    STATE_URL,
    VERSION,
)


@callback
def _get_active_entry(hass: HomeAssistant) -> ConfigEntry | None:
    """Return the first active config entry."""
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


@callback
def _get_settings(hass: HomeAssistant) -> dict[str, Any] | None:
    """Get merged entry settings."""
    entry = _get_active_entry(hass)
    if entry is None:
        return None

    merged = {**entry.data, **entry.options}
    merged.setdefault(CONF_INCLUDED_DOMAINS, DEFAULT_INCLUDED_DOMAINS)
    merged.setdefault(CONF_ENTITY_ALLOWLIST, [])
    merged.setdefault(CONF_EXPOSE_ATTRIBUTES, DEFAULT_EXPOSE_ATTRIBUTES)
    merged.setdefault(CONF_CAMPUS_HUB_URL, "")
    return merged


def _extract_token(request: web.Request) -> str:
    """Read the scoped API token from headers or query params."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return request.query.get("token", "").strip()


def _parse_csv(value: str) -> list[str]:
    """Parse comma-separated query values."""
    return [item.strip() for item in value.split(",") if item.strip()]


@callback
def _is_entity_allowed(settings: dict[str, Any], state: State) -> bool:
    """Check whether an entity is exposed by the bridge settings."""
    entity_id = state.entity_id
    domain = entity_id.split(".", 1)[0]

    included_domains = set(settings.get(CONF_INCLUDED_DOMAINS, []))
    entity_allowlist = set(settings.get(CONF_ENTITY_ALLOWLIST, []))

    if entity_id in entity_allowlist:
        return True
    if domain in included_domains:
        return True
    return not included_domains and not entity_allowlist


@callback
def _serialize_state(state: State, *, include_attributes: bool) -> dict[str, Any]:
    """Convert a Home Assistant state into a Campus Hub friendly payload."""
    payload: dict[str, Any] = {
        "entity_id": state.entity_id,
        "domain": state.entity_id.split(".", 1)[0],
        "friendly_name": state.name,
        "state": state.state,
        "last_changed": state.last_changed.isoformat(),
        "last_updated": state.last_updated.isoformat(),
    }

    if include_attributes:
        payload["attributes"] = dict(state.attributes)

    return payload


@callback
def _serialize_entity_summary(state: State) -> dict[str, Any]:
    """Return the discovery payload for an entity."""
    attrs = state.attributes
    return {
        "entity_id": state.entity_id,
        "domain": state.entity_id.split(".", 1)[0],
        "friendly_name": state.name,
        "icon": attrs.get("icon"),
        "device_class": attrs.get("device_class"),
        "unit_of_measurement": attrs.get("unit_of_measurement"),
        "state": state.state,
    }


class CampusHubBridgeBaseView(HomeAssistantView):
    """Base view that enforces scoped token auth."""

    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    def _settings(self) -> dict[str, Any]:
        settings = _get_settings(self.hass)
        if settings is None:
            raise web.HTTPServiceUnavailable(
                text='{"error":"Campus Hub Bridge is not configured"}',
                content_type="application/json",
            )
        return settings

    def _authorize(self, request: web.Request) -> dict[str, Any]:
        settings = self._settings()
        provided_token = _extract_token(request)
        configured_token = str(settings.get(CONF_API_TOKEN, ""))

        if not configured_token or not provided_token or not hmac.compare_digest(provided_token, configured_token):
            raise web.HTTPUnauthorized(
                text='{"error":"Unauthorized"}',
                content_type="application/json",
            )

        return settings

    def _base_metadata(self, settings: dict[str, Any]) -> dict[str, Any]:
        return {
            "integration": NAME,
            "domain": DOMAIN,
            "version": VERSION,
            "campus_hub_url": settings.get(CONF_CAMPUS_HUB_URL, ""),
        }


class CampusHubBridgeHealthView(CampusHubBridgeBaseView):
    """Basic health endpoint for Campus Hub Bridge."""

    url = HEALTH_URL
    name = "api:campus_hub_bridge:health"

    async def get(self, request: web.Request) -> web.Response:
        settings = self._authorize(request)
        states = [state for state in self.hass.states.async_all() if _is_entity_allowed(settings, state)]

        return web.json_response(
            {
                **self._base_metadata(settings),
                "ok": True,
                "included_domains": settings.get(CONF_INCLUDED_DOMAINS, []),
                "entity_allowlist": settings.get(CONF_ENTITY_ALLOWLIST, []),
                "entity_count": len(states),
            }
        )


class CampusHubBridgeEntitiesView(CampusHubBridgeBaseView):
    """Return the exposed entity catalog."""

    url = ENTITIES_URL
    name = "api:campus_hub_bridge:entities"

    async def get(self, request: web.Request) -> web.Response:
        settings = self._authorize(request)
        entities = [
            _serialize_entity_summary(state)
            for state in self.hass.states.async_all()
            if _is_entity_allowed(settings, state)
        ]
        entities.sort(key=lambda item: item["entity_id"])

        return web.json_response(
            {
                **self._base_metadata(settings),
                "entities": entities,
                "count": len(entities),
            }
        )


class CampusHubBridgeStateView(CampusHubBridgeBaseView):
    """Return current entity state payloads."""

    url = STATE_URL
    name = "api:campus_hub_bridge:state"

    async def get(self, request: web.Request) -> web.Response:
        settings = self._authorize(request)

        requested_entity_ids = request.query.getall("entity_id", [])
        requested_entity_ids.extend(_parse_csv(request.query.get("entity_ids", "")))
        requested_set = {entity_id for entity_id in requested_entity_ids if entity_id}

        include_attributes = bool(settings.get(CONF_EXPOSE_ATTRIBUTES, DEFAULT_EXPOSE_ATTRIBUTES))

        states = []
        for state in self.hass.states.async_all():
            if not _is_entity_allowed(settings, state):
                continue
            if requested_set and state.entity_id not in requested_set:
                continue
            states.append(_serialize_state(state, include_attributes=include_attributes))

        states.sort(key=lambda item: item["entity_id"])

        return web.json_response(
            {
                **self._base_metadata(settings),
                "requested_entity_ids": sorted(requested_set),
                "states": states,
                "count": len(states),
            }
        )


@callback
def async_register_views(hass: HomeAssistant) -> None:
    """Register HTTP views for the integration."""
    hass.http.register_view(CampusHubBridgeHealthView(hass))
    hass.http.register_view(CampusHubBridgeEntitiesView(hass))
    hass.http.register_view(CampusHubBridgeStateView(hass))

