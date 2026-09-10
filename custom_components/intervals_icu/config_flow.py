"""Config and re-authentication flow for Intervals.icu."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import IntervalsAuthError, IntervalsClient, IntervalsError
from .const import CONF_ATHLETE_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

# The athlete ID is optional on purpose: with only the API key we can ask the
# API who it belongs to, which removes the most common setup mistake.
STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_ATHLETE_ID, default=""): str,
    }
)

STEP_REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): str})


class IntervalsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the user-facing setup."""

    VERSION = 1

    async def _async_validate(
        self, api_key: str, athlete_id: str
    ) -> tuple[str, str, dict[str, str]]:
        """Return (athlete_id, athlete_name, errors) for the given credentials."""
        client = IntervalsClient(
            session=async_get_clientsession(self.hass),
            api_key=api_key.strip(),
            athlete_id=athlete_id.strip() or None,
        )

        try:
            profile = await client.async_resolve_athlete()
        except IntervalsAuthError:
            return "", "", {"base": "invalid_auth"}
        except IntervalsError as err:
            _LOGGER.debug("connection check failed: %s", err)
            return "", "", {"base": "cannot_connect"}

        name = str(profile.get("name") or "Intervals.icu")
        return str(client.athlete_id), name, {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            resolved_id, name, errors = await self._async_validate(
                user_input[CONF_API_KEY], user_input.get(CONF_ATHLETE_ID, "")
            )
            if not errors:
                await self.async_set_unique_id(resolved_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_API_KEY: user_input[CONF_API_KEY].strip(),
                        CONF_ATHLETE_ID: resolved_id,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start re-authentication after the stored key stopped working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a fresh API key."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            resolved_id, _name, errors = await self._async_validate(
                user_input[CONF_API_KEY], entry.data[CONF_ATHLETE_ID]
            )
            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_API_KEY: user_input[CONF_API_KEY].strip(),
                        CONF_ATHLETE_ID: resolved_id,
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_SCHEMA,
            errors=errors,
        )
