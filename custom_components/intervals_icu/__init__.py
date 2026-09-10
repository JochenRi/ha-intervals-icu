"""The Intervals.icu integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from . import websocket
from .api import IntervalsClient
from .const import (
    ARCHIVE_SYNC_INTERVAL,
    CONF_ATHLETE_ID,
    DOMAIN,
    PANEL_COMPONENT,
    PANEL_FILE,
    PANEL_ICON,
    PANEL_STATIC_PATH,
    PANEL_TITLE,
    PANEL_URL_PATH,
    PANEL_VERSION,
)
from .coordinator import IntervalsConfigEntry, IntervalsCoordinator
from .store import IntervalsArchive

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: IntervalsConfigEntry) -> bool:
    """Set up Intervals.icu from a config entry."""
    client = IntervalsClient(
        session=async_get_clientsession(hass),
        api_key=entry.data[CONF_API_KEY],
        athlete_id=entry.data[CONF_ATHLETE_ID],
    )

    archive = IntervalsArchive(hass, str(entry.unique_id))
    await archive.async_load()
    # Read before the first refresh: that refresh already writes the recent
    # window into the archive.
    needs_full = archive.needs_full_import

    coordinator = IntervalsCoordinator(hass, entry, client, archive)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    websocket.async_register(hass)
    await _async_register_panel(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # The first import walks the whole history and can take a minute. It runs
    # in the background so setup finishes immediately; later runs only touch
    # the recent window and one batch of DFA summaries.
    entry.async_create_background_task(
        hass,
        coordinator.async_sync_archive(full=needs_full),
        name="intervals_icu_archive_sync",
    )

    entry.async_on_unload(
        async_track_time_interval(
            hass,
            lambda _now: hass.async_create_task(coordinator.async_sync_archive()),
            ARCHIVE_SYNC_INTERVAL,
        )
    )

    return True


async def _async_register_panel(hass: HomeAssistant) -> None:
    """Serve the panel from the integration and add it to the sidebar.

    Registering twice raises, so a flag in hass.data guards the second config
    entry and any reload.
    """
    if hass.data.get(f"{DOMAIN}_panel_registered"):
        return

    folder = Path(__file__).parent / "frontend"
    module = folder / PANEL_FILE
    if not module.is_file():
        # Without this check the only symptom is the browser saying it cannot
        # load the panel - with no hint that a file is simply missing.
        _LOGGER.error(
            "Intervals.icu: %s is missing. The frontend folder did not make it "
            "into %s - copy the whole integration folder again",
            PANEL_FILE,
            folder,
        )
        return

    hass.data[f"{DOMAIN}_panel_registered"] = True

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                PANEL_STATIC_PATH,
                str(Path(__file__).parent / "frontend"),
                cache_headers=False,
            )
        ]
    )

    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_COMPONENT,
        frontend_url_path=PANEL_URL_PATH,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=f"{PANEL_STATIC_PATH}/{PANEL_FILE}?v={PANEL_VERSION}",
        embed_iframe=False,
        require_admin=False,
    )
    _LOGGER.info(
        "Intervals.icu panel registered at /%s, serving %s from %s",
        PANEL_URL_PATH,
        PANEL_FILE,
        folder,
    )


async def async_unload_entry(hass: HomeAssistant, entry: IntervalsConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: IntervalsConfigEntry) -> None:
    """Delete the local archive when the integration is removed."""
    archive = IntervalsArchive(hass, str(entry.unique_id))
    await archive.async_remove()
