"""Shared entity base for Intervals.icu."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import IntervalsConfigEntry, IntervalsCoordinator


class IntervalsEntity(CoordinatorEntity[IntervalsCoordinator]):
    """Base class binding every entity to one athlete device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: IntervalsCoordinator,
        entry: IntervalsConfigEntry,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self._config_entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(entry.unique_id))},
            manufacturer=MANUFACTURER,
            name=entry.title,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=f"https://intervals.icu/athlete/{entry.unique_id}/fitness",
        )
