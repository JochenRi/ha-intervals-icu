"""Calendar platform for Intervals.icu planned workouts."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import IntervalsConfigEntry
from .entity import IntervalsEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IntervalsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Intervals.icu calendar."""
    async_add_entities([IntervalsCalendar(entry.runtime_data, entry)])


def _as_datetime(value: date | datetime) -> datetime:
    """Return a timezone aware datetime for ordering all-day entries."""
    if isinstance(value, datetime):
        return dt_util.as_local(value) if value.tzinfo else value.replace(
            tzinfo=dt_util.get_default_time_zone()
        )
    return datetime.combine(value, datetime.min.time()).replace(
        tzinfo=dt_util.get_default_time_zone()
    )


def _to_event(item: dict[str, Any]) -> CalendarEvent:
    """Convert a prepared event into a Home Assistant calendar event."""
    parts: list[str] = []
    if item.get("load") is not None:
        parts.append(f"Load {item['load']}")
    if item.get("moving_time"):
        parts.append(f"{int(item['moving_time']) // 60} min")
    if item.get("description"):
        parts.append(str(item["description"]))

    return CalendarEvent(
        uid=item["uid"] or None,
        summary=item["summary"],
        description="\n".join(parts) or None,
        start=item["start"],
        end=item["end"],
    )


class IntervalsCalendar(IntervalsEntity, CalendarEntity):
    """Planned workouts, races and notes from the Intervals.icu calendar."""

    _attr_translation_key = "planned"

    def __init__(self, coordinator, entry: IntervalsConfigEntry) -> None:
        """Initialise the calendar entity."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.unique_id}_calendar"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming event."""
        now = dt_util.now()
        for item in self.coordinator.data.get("planned") or []:
            event = _to_event(item)
            end = _as_datetime(event.end)
            if end > now:
                return event
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return every event overlapping the requested range, in order."""
        result: list[CalendarEvent] = []
        for item in self.coordinator.data.get("planned") or []:
            event = _to_event(item)
            if _as_datetime(event.end) > start_date and _as_datetime(event.start) < end_date:
                result.append(event)
        return result
