"""Persistent archive for Intervals.icu data.

Uses Home Assistant's own storage helper, which writes JSON into .storage/.
A full season measured about 300 kB, so a single file is the right tool - no
database, no recorder load.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from . import importer, plan
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
# Writes are batched: the import touches the archive hundreds of times.
SAVE_DELAY = 15


class IntervalsArchive:
    """The local copy of wellness rows, activities and DFA summaries."""

    def __init__(self, hass: HomeAssistant, athlete_id: str) -> None:
        """Set up the archive without touching the disk yet."""
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{athlete_id}"
        )
        self.athlete_id = athlete_id
        self.data: dict[str, Any] = importer.empty_data(athlete_id)

    async def async_load(self) -> None:
        """Load the archive from disk, falling back to an empty one."""
        stored = await self._store.async_load()
        if isinstance(stored, dict) and stored.get("wellness") is not None:
            # Fill in keys added by later versions of the integration.
            base = importer.empty_data(self.athlete_id)
            base.update(stored)
            self.data = base
            # ...but update() only reaches the TOP level. A goal profile
            # written before 0.33.0 keeps its old shape and carries no
            # calendar anchor, so the 3:1 plan silently restarts every
            # Monday. Repair it once, here, instead of waiting for the
            # athlete to re-save the goal by chance.
            if (repaired := plan.migrate_goal(self.data.get("goal"))) is not None:
                self.data["goal"] = repaired
                self.schedule_save()
        _LOGGER.debug("archive loaded: %s", importer.archive_stats(self.data))

    @property
    def needs_full_import(self) -> bool:
        """Return True while the full history has not been imported yet."""
        return importer.should_full_import(self.data)

    def schedule_save(self) -> None:
        """Persist the archive shortly, batching rapid changes."""
        self._store.async_delay_save(lambda: self.data, SAVE_DELAY)

    async def async_save_now(self) -> None:
        """Persist the archive immediately."""
        await self._store.async_save(self.data)

    async def async_remove(self) -> None:
        """Delete the archive from disk."""
        await self._store.async_remove()
