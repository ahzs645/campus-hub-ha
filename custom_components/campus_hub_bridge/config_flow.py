"""Config flow for Campus Hub Bridge."""

from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_API_TOKEN,
    CONF_CAMPUS_HUB_URL,
    CONF_ENTITY_ALLOWLIST,
    CONF_EXPOSE_ATTRIBUTES,
    CONF_INCLUDED_DOMAINS,
    DEFAULT_EXPOSE_ATTRIBUTES,
    DEFAULT_INCLUDED_DOMAINS,
    DEFAULT_NAME,
    DOMAIN,
)

CONF_NAME = "name"
UNIQUE_ID = DOMAIN


def _csv_to_list(value: str) -> list[str]:
    """Convert a comma-separated string into a normalized list."""
    return [item.strip() for item in value.split(",") if item.strip()]


def _list_to_csv(value: list[str] | str | None) -> str:
    """Convert list settings back to the form representation."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return ", ".join(value)


def _build_defaults(source: dict[str, Any] | None = None, *, token: str | None = None) -> dict[str, Any]:
    """Build form defaults from an existing entry or an empty state."""
    source = source or {}
    return {
        CONF_NAME: str(source.get(CONF_NAME) or DEFAULT_NAME),
        CONF_API_TOKEN: str(source.get(CONF_API_TOKEN) or token or secrets.token_urlsafe(24)),
        CONF_CAMPUS_HUB_URL: str(source.get(CONF_CAMPUS_HUB_URL) or ""),
        CONF_INCLUDED_DOMAINS: _list_to_csv(source.get(CONF_INCLUDED_DOMAINS, DEFAULT_INCLUDED_DOMAINS)),
        CONF_ENTITY_ALLOWLIST: _list_to_csv(source.get(CONF_ENTITY_ALLOWLIST, [])),
        CONF_EXPOSE_ATTRIBUTES: bool(source.get(CONF_EXPOSE_ATTRIBUTES, DEFAULT_EXPOSE_ATTRIBUTES)),
    }


def _build_user_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults[CONF_NAME]): str,
            vol.Required(CONF_API_TOKEN, default=defaults[CONF_API_TOKEN]): str,
            vol.Optional(CONF_CAMPUS_HUB_URL, default=defaults[CONF_CAMPUS_HUB_URL]): str,
            vol.Required(CONF_INCLUDED_DOMAINS, default=defaults[CONF_INCLUDED_DOMAINS]): str,
            vol.Optional(CONF_ENTITY_ALLOWLIST, default=defaults[CONF_ENTITY_ALLOWLIST]): str,
            vol.Required(CONF_EXPOSE_ATTRIBUTES, default=defaults[CONF_EXPOSE_ATTRIBUTES]): bool,
        }
    )


def _build_options_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_API_TOKEN, default=defaults[CONF_API_TOKEN]): str,
            vol.Optional(CONF_CAMPUS_HUB_URL, default=defaults[CONF_CAMPUS_HUB_URL]): str,
            vol.Required(CONF_INCLUDED_DOMAINS, default=defaults[CONF_INCLUDED_DOMAINS]): str,
            vol.Optional(CONF_ENTITY_ALLOWLIST, default=defaults[CONF_ENTITY_ALLOWLIST]): str,
            vol.Required(CONF_EXPOSE_ATTRIBUTES, default=defaults[CONF_EXPOSE_ATTRIBUTES]): bool,
        }
    )


def _normalize_input(user_input: dict[str, Any], *, include_name: bool) -> tuple[dict[str, Any], dict[str, str]]:
    """Normalize config flow form input into storage shape."""
    errors: dict[str, str] = {}

    api_token = str(user_input.get(CONF_API_TOKEN, "")).strip()
    campus_hub_url = str(user_input.get(CONF_CAMPUS_HUB_URL, "")).strip()
    included_domains = _csv_to_list(str(user_input.get(CONF_INCLUDED_DOMAINS, "")))
    entity_allowlist = _csv_to_list(str(user_input.get(CONF_ENTITY_ALLOWLIST, "")))

    normalized: dict[str, Any] = {
        CONF_API_TOKEN: api_token,
        CONF_CAMPUS_HUB_URL: campus_hub_url,
        CONF_INCLUDED_DOMAINS: included_domains,
        CONF_ENTITY_ALLOWLIST: entity_allowlist,
        CONF_EXPOSE_ATTRIBUTES: bool(user_input.get(CONF_EXPOSE_ATTRIBUTES, DEFAULT_EXPOSE_ATTRIBUTES)),
    }

    if include_name:
        name = str(user_input.get(CONF_NAME, "")).strip() or DEFAULT_NAME
        normalized[CONF_NAME] = name

    if not api_token:
        errors[CONF_API_TOKEN] = "required"

    if campus_hub_url:
        parsed = urlparse(campus_hub_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors[CONF_CAMPUS_HUB_URL] = "invalid_url"

    return normalized, errors


class CampusHubBridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Campus Hub Bridge."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Return the options flow for this handler."""
        return CampusHubBridgeOptionsFlow(config_entry)

    def __init__(self) -> None:
        self._initial_token = secrets.token_urlsafe(24)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial setup step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        defaults = _build_defaults(token=self._initial_token)
        errors: dict[str, str] = {}

        if user_input is not None:
            defaults = _build_defaults(user_input, token=self._initial_token)
            normalized, errors = _normalize_input(user_input, include_name=True)

            if not errors:
                await self.async_set_unique_id(UNIQUE_ID)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=normalized[CONF_NAME],
                    data={
                        CONF_NAME: normalized[CONF_NAME],
                        CONF_API_TOKEN: normalized[CONF_API_TOKEN],
                    },
                    options={
                        CONF_CAMPUS_HUB_URL: normalized[CONF_CAMPUS_HUB_URL],
                        CONF_INCLUDED_DOMAINS: normalized[CONF_INCLUDED_DOMAINS],
                        CONF_ENTITY_ALLOWLIST: normalized[CONF_ENTITY_ALLOWLIST],
                        CONF_EXPOSE_ATTRIBUTES: normalized[CONF_EXPOSE_ATTRIBUTES],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_user_schema(defaults),
            errors=errors,
        )


class CampusHubBridgeOptionsFlow(config_entries.OptionsFlow):
    """Handle Campus Hub Bridge options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage integration options."""
        merged = {**self.config_entry.data, **self.config_entry.options}
        defaults = _build_defaults(merged)
        errors: dict[str, str] = {}

        if user_input is not None:
            defaults = _build_defaults(user_input)
            normalized, errors = _normalize_input(user_input, include_name=False)

            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_API_TOKEN: normalized[CONF_API_TOKEN],
                        CONF_CAMPUS_HUB_URL: normalized[CONF_CAMPUS_HUB_URL],
                        CONF_INCLUDED_DOMAINS: normalized[CONF_INCLUDED_DOMAINS],
                        CONF_ENTITY_ALLOWLIST: normalized[CONF_ENTITY_ALLOWLIST],
                        CONF_EXPOSE_ATTRIBUTES: normalized[CONF_EXPOSE_ATTRIBUTES],
                    },
                )

        return self.async_show_form(
            step_id="init",
            data_schema=_build_options_schema(defaults),
            errors=errors,
        )

