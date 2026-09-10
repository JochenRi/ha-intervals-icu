"""Sensor platform for Intervals.icu.

Three families of sensors:

* wellness   - one per daily wellness field, showing the newest value that
               actually exists, with the date it belongs to as an attribute
* sport      - FTP / LTHR / max HR per sport plus the estimated values
               (eFTP, W', Pmax) Intervals derives from recent rides
* calendar   - the next planned workout

Fields that carry no value at all within the lookback window are still
created, but disabled, so nothing shows up as "unknown" forever and a value
that starts arriving later only needs one click.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfMass,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import derive, importer
from .coordinator import IntervalsConfigEntry, IntervalsCoordinator
from .entity import IntervalsEntity


@dataclass(frozen=True, kw_only=True)
class WellnessSensorDescription(SensorEntityDescription):
    """Describes a sensor fed by a single wellness field."""

    field: str
    transform: Callable[[Any], Any] | None = None


def _secs_to_hours(value: Any) -> float | None:
    """Convert a duration in seconds to hours."""
    try:
        return round(float(value) / 3600, 2)
    except (TypeError, ValueError):
        return None


WELLNESS_SENSORS: tuple[WellnessSensorDescription, ...] = (
    # --- training load ------------------------------------------------------
    WellnessSensorDescription(
        key="fitness", field="ctl", translation_key="fitness", icon="mdi:chart-line",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
    ),
    WellnessSensorDescription(
        key="fatigue", field="atl", translation_key="fatigue",
        icon="mdi:battery-charging-low",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
    ),
    WellnessSensorDescription(
        key="ramp_rate", field="rampRate", translation_key="ramp_rate",
        icon="mdi:slope-uphill",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
    ),
    WellnessSensorDescription(
        key="load", field="ctlLoad", translation_key="load", icon="mdi:weight",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0,
    ),
    # --- vitals -------------------------------------------------------------
    WellnessSensorDescription(
        key="resting_hr", field="restingHR", translation_key="resting_hr",
        icon="mdi:heart-pulse", native_unit_of_measurement="bpm",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0,
    ),
    WellnessSensorDescription(
        key="hrv", field="hrv", translation_key="hrv", icon="mdi:heart-flash",
        native_unit_of_measurement="ms",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0,
    ),
    WellnessSensorDescription(
        key="hrv_sdnn", field="hrvSDNN", translation_key="hrv_sdnn",
        icon="mdi:heart-flash", native_unit_of_measurement="ms",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0,
    ),
    WellnessSensorDescription(
        key="sleeping_hr", field="avgSleepingHR", translation_key="sleeping_hr",
        icon="mdi:heart", native_unit_of_measurement="bpm",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0,
    ),
    WellnessSensorDescription(
        key="spo2", field="spO2", translation_key="spo2", icon="mdi:lungs",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0,
    ),
    WellnessSensorDescription(
        key="respiration", field="respiration", translation_key="respiration",
        icon="mdi:lungs", native_unit_of_measurement="brpm",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0,
    ),
    WellnessSensorDescription(
        key="vo2max", field="vo2max", translation_key="vo2max", icon="mdi:run-fast",
        native_unit_of_measurement="ml/kg/min",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
    ),
    WellnessSensorDescription(
        key="blood_glucose", field="bloodGlucose", translation_key="blood_glucose",
        icon="mdi:water", native_unit_of_measurement="mmol/L",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
    ),
    WellnessSensorDescription(
        key="systolic", field="systolic", translation_key="systolic",
        icon="mdi:blood-bag", native_unit_of_measurement="mmHg",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0,
    ),
    WellnessSensorDescription(
        key="diastolic", field="diastolic", translation_key="diastolic",
        icon="mdi:blood-bag", native_unit_of_measurement="mmHg",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0,
    ),
    # --- sleep --------------------------------------------------------------
    WellnessSensorDescription(
        key="sleep_time", field="sleepSecs", translation_key="sleep_time",
        icon="mdi:sleep", device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS, transform=_secs_to_hours,
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
    ),
    WellnessSensorDescription(
        key="sleep_score", field="sleepScore", translation_key="sleep_score",
        icon="mdi:sleep", state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    WellnessSensorDescription(
        key="sleep_quality", field="sleepQuality", translation_key="sleep_quality",
        icon="mdi:sleep", state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    WellnessSensorDescription(
        key="readiness", field="readiness", translation_key="readiness",
        icon="mdi:battery-heart-variant", state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    # --- body / intake ------------------------------------------------------
    WellnessSensorDescription(
        key="weight", field="weight", translation_key="weight",
        device_class=SensorDeviceClass.WEIGHT,
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
    ),
    WellnessSensorDescription(
        key="body_fat", field="bodyFat", translation_key="body_fat",
        icon="mdi:percent", native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1,
    ),
    WellnessSensorDescription(
        key="steps", field="steps", translation_key="steps", icon="mdi:shoe-print",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0,
    ),
    WellnessSensorDescription(
        key="calories_consumed", field="kcalConsumed",
        translation_key="calories_consumed", icon="mdi:food-apple",
        native_unit_of_measurement="kcal",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0,
    ),
    WellnessSensorDescription(
        key="hydration", field="hydrationVolume", translation_key="hydration",
        icon="mdi:cup-water", native_unit_of_measurement="mL",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0,
    ),
    # --- subjective (entered by hand in Intervals) --------------------------
    WellnessSensorDescription(
        key="stress", field="stress", translation_key="stress", icon="mdi:flash-alert",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0,
    ),
    WellnessSensorDescription(
        key="mood", field="mood", translation_key="mood", icon="mdi:emoticon-outline",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0,
    ),
    WellnessSensorDescription(
        key="motivation", field="motivation", translation_key="motivation",
        icon="mdi:rocket-launch", state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    WellnessSensorDescription(
        key="soreness", field="soreness", translation_key="soreness",
        icon="mdi:arm-flex", state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    WellnessSensorDescription(
        key="subjective_fatigue", field="fatigue",
        translation_key="subjective_fatigue", icon="mdi:sleep-off",
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0,
    ),
)

# FTP / LTHR / max HR come from the athlete's sport settings.
SPORT_SETTING_FIELDS: tuple[tuple[str, str, str | None, str], ...] = (
    ("ftp", "FTP", UnitOfPower.WATT, "mdi:lightning-bolt"),
    ("lthr", "LTHR", "bpm", "mdi:heart-pulse"),
    ("max_hr", "Max HR", "bpm", "mdi:heart-flash"),
)

# eFTP, W' and Pmax are estimated by Intervals from recent activities.
SPORT_ESTIMATE_FIELDS: tuple[tuple[str, str, str | None, str], ...] = (
    ("eftp", "eFTP", UnitOfPower.WATT, "mdi:lightning-bolt-outline"),
    ("wPrime", "W prime", "J", "mdi:battery-high"),
    ("pMax", "Pmax", UnitOfPower.WATT, "mdi:flash-triangle"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IntervalsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Intervals.icu sensors."""
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    available: set[str] = data.get("available") or set()

    entities: list[SensorEntity] = [
        IntervalsWellnessSensor(coordinator, entry, description, description.field in available)
        for description in WELLNESS_SENSORS
    ]

    # Form is derived, not delivered: CTL minus ATL.
    entities.append(IntervalsFormSensor(coordinator, entry))

    for setting in data.get("sport_settings") or []:
        label = derive.sport_label(setting)
        for field, name, unit, icon in SPORT_SETTING_FIELDS:
            entities.append(
                IntervalsSportSettingSensor(
                    coordinator, entry, label, field, name, unit, icon,
                    setting.get(field) is not None,
                )
            )

    for label in data.get("sport_info") or {}:
        for field, name, unit, icon in SPORT_ESTIMATE_FIELDS:
            entities.append(
                IntervalsSportEstimateSensor(
                    coordinator, entry, label, field, name, unit, icon
                )
            )

    entities.extend(
        [
            IntervalsArchiveSensor(coordinator, entry),
            IntervalsNextWorkoutSensor(coordinator, entry),
            IntervalsNextWorkoutDateSensor(coordinator, entry),
            IntervalsNextWorkoutLoadSensor(coordinator, entry),
        ]
    )

    async_add_entities(entities)


class IntervalsWellnessSensor(IntervalsEntity, SensorEntity):
    """A single wellness field, showing its newest known value."""

    entity_description: WellnessSensorDescription

    def __init__(
        self,
        coordinator: IntervalsCoordinator,
        entry: IntervalsConfigEntry,
        description: WellnessSensorDescription,
        enabled: bool,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"
        self._attr_entity_registry_enabled_default = enabled

    def _latest(self) -> tuple[Any, str] | None:
        """Return the (value, date) tuple for this field."""
        latest: dict[str, tuple[Any, str]] = self.coordinator.data.get("latest") or {}
        return latest.get(self.entity_description.field)

    @property
    def native_value(self) -> Any:
        """Return the newest known value."""
        item = self._latest()
        if item is None:
            return None
        value = item[0]
        if self.entity_description.transform is not None:
            return self.entity_description.transform(value)
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the date the value belongs to and whether it is provisional."""
        item = self._latest()
        attributes: dict[str, Any] = {"value_date": item[1] if item else None}
        temp = derive.temp_flags(
            self.coordinator.data.get("wellness_rows") or [],
            self.entity_description.field,
        )
        if temp is not None:
            attributes["provisional"] = temp
        return attributes


class IntervalsFormSensor(IntervalsEntity, SensorEntity):
    """Form (TSB) is fitness minus fatigue."""

    _attr_translation_key = "form"
    _attr_icon = "mdi:scale-balance"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: IntervalsCoordinator, entry: IntervalsConfigEntry) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.unique_id}_form"

    @property
    def native_value(self) -> float | None:
        """Return CTL minus ATL."""
        latest = self.coordinator.data.get("latest") or {}
        ctl = latest.get("ctl")
        atl = latest.get("atl")
        if ctl is None or atl is None:
            return None
        try:
            return float(ctl[0]) - float(atl[0])
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the date the value belongs to."""
        latest = self.coordinator.data.get("latest") or {}
        ctl = latest.get("ctl")
        return {"value_date": ctl[1] if ctl else None}


class _IntervalsSportSensor(IntervalsEntity, SensorEntity):
    """Shared base for the per-sport sensors."""

    def __init__(
        self,
        coordinator: IntervalsCoordinator,
        entry: IntervalsConfigEntry,
        label: str,
        field: str,
        name: str,
        unit: str | None,
        icon: str,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, entry)
        self._label = label
        self._field = field
        self._attr_name = f"{name} {label}"
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0
        self._attr_unique_id = f"{entry.unique_id}_{label.lower()}_{field.lower()}"


class IntervalsSportSettingSensor(_IntervalsSportSensor):
    """A configured threshold (FTP, LTHR, max HR) for one sport."""

    def __init__(self, coordinator, entry, label, field, name, unit, icon, enabled) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, entry, label, field, name, unit, icon)
        self._attr_entity_registry_enabled_default = enabled

    @property
    def native_value(self) -> Any:
        """Return the configured value for this sport."""
        for setting in self.coordinator.data.get("sport_settings") or []:
            if derive.sport_label(setting) == self._label:
                return setting.get(self._field)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose which activity types this setting covers."""
        for setting in self.coordinator.data.get("sport_settings") or []:
            if derive.sport_label(setting) == self._label:
                return {"types": setting.get("types") or []}
        return {}


class IntervalsSportEstimateSensor(_IntervalsSportSensor):
    """An estimate Intervals derives from recent activities."""

    @property
    def native_value(self) -> Any:
        """Return the estimated value for this sport."""
        info = (self.coordinator.data.get("sport_info") or {}).get(self._label) or {}
        return info.get(self._field)


class IntervalsNextWorkoutSensor(IntervalsEntity, SensorEntity):
    """Name of the next planned workout."""

    _attr_translation_key = "next_workout"
    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator: IntervalsCoordinator, entry: IntervalsConfigEntry) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.unique_id}_next_workout"

    @property
    def native_value(self) -> str | None:
        """Return the workout name."""
        item = self.coordinator.data.get("next_event")
        return item["summary"][:255] if item else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the full workout details."""
        item = self.coordinator.data.get("next_event")
        if not item:
            return {}
        return {
            "sport": item.get("type"),
            "category": item.get("category"),
            "load": item.get("load"),
            "intensity": item.get("intensity"),
            "duration_min": (
                int(item["moving_time"]) // 60 if item.get("moving_time") else None
            ),
            "description": item.get("description"),
        }


class IntervalsNextWorkoutDateSensor(IntervalsEntity, SensorEntity):
    """Date of the next planned workout."""

    _attr_translation_key = "next_workout_date"
    _attr_icon = "mdi:calendar-clock"
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: IntervalsCoordinator, entry: IntervalsConfigEntry) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.unique_id}_next_workout_date"

    @property
    def native_value(self) -> date | None:
        """Return the start date."""
        item = self.coordinator.data.get("next_event")
        if not item:
            return None
        start = item["start"]
        return start.date() if isinstance(start, datetime) else start


class IntervalsNextWorkoutLoadSensor(IntervalsEntity, SensorEntity):
    """Planned training load of the next workout."""

    _attr_translation_key = "next_workout_load"
    _attr_icon = "mdi:weight-lifter"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator: IntervalsCoordinator, entry: IntervalsConfigEntry) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.unique_id}_next_workout_load"

    @property
    def native_value(self) -> Any:
        """Return the planned load."""
        item = self.coordinator.data.get("next_event")
        return item.get("load") if item else None


class IntervalsArchiveSensor(IntervalsEntity, SensorEntity):
    """How much history the local archive holds - and what is still missing."""

    _attr_translation_key = "archive"
    _attr_icon = "mdi:database-clock"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: IntervalsCoordinator, entry: IntervalsConfigEntry) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.unique_id}_archive"

    @property
    def native_value(self) -> int | None:
        """Return the number of stored activities."""
        return self._stats()["activities"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the full archive statistics."""
        return self._stats()

    def _stats(self) -> dict[str, Any]:
        """Read the numbers straight from the archive, not from a snapshot.

        The import runs in the background, well after the coordinator refresh
        that produced the snapshot - reading that would show stale counts.
        """
        stats = importer.archive_stats(self.coordinator.archive.data)
        stats["importing"] = bool(getattr(self.coordinator, "import_running", False))
        return stats

