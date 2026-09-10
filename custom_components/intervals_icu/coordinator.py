"""Data coordinator for the Intervals.icu integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import derive, importer
from .api import IntervalsAuthError, IntervalsClient, IntervalsError
from .const import (
    DEFAULT_SCAN_INTERVAL,
    DFA_BATCH_SIZE,
    DOMAIN,
    EVENTS_FUTURE_DAYS,
    EVENTS_PAST_DAYS,
    HISTORY_START_FALLBACK_DAYS,
    RECENT_DAYS,
    WELLNESS_LOOKBACK_DAYS,
)
from .store import IntervalsArchive

_LOGGER = logging.getLogger(__name__)

type IntervalsConfigEntry = ConfigEntry[IntervalsCoordinator]


class IntervalsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Keeps entities fed and the local archive up to date."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: IntervalsConfigEntry,
        client: IntervalsClient,
        archive: IntervalsArchive,
    ) -> None:
        """Set up the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
            config_entry=entry,
        )
        self.client = client
        self.archive = archive
        self.import_running = False

    async def _async_update_data(self) -> dict[str, Any]:
        """Return everything the entities need, already reduced."""
        today = date.today()

        try:
            athlete = await self.client.async_get_athlete()
            wellness = await self.client.async_get_wellness(
                today - timedelta(days=WELLNESS_LOOKBACK_DAYS), today
            )
            events = await self.client.async_get_events(
                today - timedelta(days=EVENTS_PAST_DAYS),
                today + timedelta(days=EVENTS_FUTURE_DAYS),
            )
        except IntervalsAuthError as err:
            # Triggers Home Assistant's re-authentication flow instead of
            # silently logging errors forever.
            raise ConfigEntryAuthFailed(str(err)) from err
        except IntervalsError as err:
            raise UpdateFailed(str(err)) from err

        rows = derive.sort_rows(wellness if isinstance(wellness, list) else [])
        event_list = events if isinstance(events, list) else []

        # The rows were fetched for the entities anyway - hand them straight to
        # the archive instead of asking the API a second time.
        if importer.merge_wellness(self.archive.data, rows):
            self.archive.schedule_save()

        return {
            "athlete": athlete,
            "wellness_rows": rows,
            "latest": derive.latest_values(rows),
            "available": derive.available_keys(rows),
            "sport_info": derive.sport_info(rows),
            "sport_settings": derive.sport_settings(athlete),
            "events": event_list,
            "planned": derive.planned_events(event_list),
            "next_event": derive.next_event(event_list, today),
            "archive": importer.archive_stats(self.archive.data),
        }

    def _history_start(self) -> date:
        """Return the first day worth importing."""
        athlete = (self.data or {}).get("athlete") or {}
        activated = str(athlete.get("icu_activated") or "")[:10]
        try:
            return date.fromisoformat(activated)
        except ValueError:
            return date.today() - timedelta(days=HISTORY_START_FALLBACK_DAYS)

    async def async_sync_archive(self, full: bool = False) -> None:
        """Bring the archive up to date.

        ``full`` walks the whole history; otherwise only the recent window is
        refreshed. DFA summaries are fetched in batches so a first import does
        not hold up anything else.
        """
        if self.import_running:
            return

        # Decided here as well, so a caller that asks for a routine sync while
        # the history has never been walked still gets the full import.
        full = full or importer.should_full_import(self.archive.data)
        # A grown field list means the stored summaries are missing columns;
        # only a full re-fetch closes that gap.
        refetch = importer.needs_activity_refetch(self.archive.data)
        full = full or refetch

        self.import_running = True
        today = date.today()
        oldest = self._history_start() if full else today - timedelta(days=RECENT_DAYS)

        try:
            changed = 0
            if full:
                changed += await importer.async_import_wellness(
                    self.client, self.archive.data, oldest, today
                )
            changed += await importer.async_import_activities(
                self.client, self.archive.data, oldest, today
            )

            if dropped := importer.drop_outdated_dfa(self.archive.data):
                _LOGGER.info(
                    "Intervals.icu: recomputing %s DFA summaries after an algorithm change",
                    dropped,
                )

            pending = len(importer.pending_dfa(self.archive.data))
            if pending:
                _LOGGER.info("Intervals.icu: %s activities still need a DFA summary", pending)

            # Push the archive sensor every few activities, otherwise its
            # state would sit at the setup snapshot until the next refresh.
            def _progress(done_count: int, total: int) -> None:
                if done_count % 10 == 0 or done_count == total:
                    self.async_update_listeners()

            self.async_update_listeners()
            done = await importer.async_import_dfa(
                self.client,
                self.archive.data,
                limit=None if (full or dropped) else DFA_BATCH_SIZE,
                progress=_progress,
            )

            importer.mark_activities_current(self.archive.data)
            self.archive.data["last_import"] = today.isoformat()
            if full:
                self.archive.data["full_import_done"] = True
            await self.archive.async_save_now()
            _LOGGER.info(
                "Intervals.icu archive updated: %s changed, %s DFA summaries, %s",
                changed,
                done,
                importer.archive_stats(self.archive.data),
            )
        except IntervalsError as err:
            _LOGGER.warning("Intervals.icu archive sync failed: %s", err)
        except asyncio.CancelledError:
            raise
        finally:
            self.import_running = False
            self.async_update_listeners()
