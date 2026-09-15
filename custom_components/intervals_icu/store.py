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

from . import day_context, importer, plan, ramp_tests, section_marks
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
            # THE EXCEPTION TO FILLING IN: a version mark must never be filled
            # in as CURRENT. An archive written before the mark existed carries
            # no `dfa_version`, so update() left the skeleton's value standing -
            # and drop_outdated_dfa then compared current against current and
            # dropped nothing. The migration could not fire in exactly the case
            # it was built for: the 0,0 bpm of 06.06.2026 was computed by the
            # maths of 0.8.0, survived the fix in 0.9.0 and sat in the archive
            # ever since. Same class as the 0.35.0 gap, one level up: there a
            # missing block was never created, here a missing mark was created
            # WRONG. Absent means ancient.
            for mark in ("dfa_version", "fields_version"):
                if mark not in stored:
                    base[mark] = 0
            self.data = base
            # ...but update() only reaches the TOP level. A goal profile
            # written before 0.33.0 keeps its old shape and carries no
            # calendar anchor, so the 3:1 plan silently restarts every
            # Monday. Repair it once, here, instead of waiting for the
            # athlete to re-save the goal by chance.
            if (repaired := plan.migrate_goal(self.data.get("goal"))) is not None:
                self.data["goal"] = repaired
                self.schedule_save()
            # Same pattern for the day-context block: the empty_data() entry
            # covers archives that never had one, the migration normalises
            # entries a broken writer left behind.
            if (ctx := day_context.migrate(self.data.get("day_context"))) is not None:
                self.data["day_context"] = ctx
                self.schedule_save()
            # Third block, same two obligations: an entry in empty_data() and a
            # migration here. The migration earns its keep with the version
            # mark - a record measured by an older algorithm keeps the
            # MARKING and loses only its NUMBERS, because the athlete's
            # statement that this ride was a test does not expire when the
            # maths changes. A no-op returns None and must not save.
            if (tests := ramp_tests.migrate(self.data.get(ramp_tests.BLOCK))) is not None:
                self.data[ramp_tests.BLOCK] = tests
                self.schedule_save()
            # Fuenfter Block, dieselben zwei Auflagen. Die Migration traegt
            # hier dieselbe Trennung wie bei ramp_tests, nur eine Ebene
            # feiner: ein Eintrag mit aelterer Messmarke verliert seine
            # STUNDEN und behaelt MARKEN UND ANKER - die Aussage des Athleten,
            # welcher Abschnitt welcher Familie gehoert, verfaellt nicht, wenn
            # sich die Mathematik aendert. Ein No-op gibt None und speichert
            # nicht.
            if (marks := section_marks.migrate(
                    self.data.get(section_marks.BLOCK))) is not None:
                self.data[section_marks.BLOCK] = marks
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
