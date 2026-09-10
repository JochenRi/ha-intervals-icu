"""Pure data helpers for Intervals.icu payloads.

This module deliberately imports nothing from Home Assistant so the parsing
logic can be tested against recorded API payloads outside of HA.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

# Wellness keys that are metadata, not measurements.
_NON_VALUE_KEYS = {
    "id",
    "updated",
    "sportInfo",
    "comments",
    "locked",
    "tempWeight",
    "tempRestingHR",
    "menstrualPhase",
    "menstrualPhasePredicted",
}


def sort_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return wellness rows sorted oldest first, invalid rows dropped."""
    return sorted(
        (row for row in rows if isinstance(row, dict) and row.get("id")),
        key=lambda row: str(row["id"]),
    )


def latest_values(rows: list[dict[str, Any]]) -> dict[str, tuple[Any, str]]:
    """Return the most recent non-null value per wellness key.

    Intervals fills a day's row over the course of that day, so reading only
    "today" leaves most sensors unknown every morning. Each value is returned
    together with the date it belongs to.
    """
    result: dict[str, tuple[Any, str]] = {}
    for row in sort_rows(rows):
        day = str(row["id"])
        for key, value in row.items():
            if key in _NON_VALUE_KEYS or value is None:
                continue
            result[key] = (value, day)
    return result


def available_keys(rows: list[dict[str, Any]]) -> set[str]:
    """Return the wellness keys that carry at least one value in the window."""
    return set(latest_values(rows))


def temp_flags(rows: list[dict[str, Any]], key: str) -> bool | None:
    """Return the temp flag belonging to the newest row that has ``key``.

    Intervals marks carried-over values (for example a weight taken from the
    activity file instead of a scale) with tempWeight / tempRestingHR.
    """
    flag_key = {"weight": "tempWeight", "restingHR": "tempRestingHR"}.get(key)
    if flag_key is None:
        return None
    for row in reversed(sort_rows(rows)):
        if row.get(key) is not None:
            return bool(row.get(flag_key))
    return None


def sport_info(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return the newest per-sport estimates (eFTP, W', Pmax) keyed by sport."""
    result: dict[str, dict[str, Any]] = {}
    for row in sort_rows(rows):
        for info in row.get("sportInfo") or []:
            if isinstance(info, dict) and info.get("type"):
                result[str(info["type"])] = info
    return result


def sport_settings(athlete: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the athlete's per-sport settings, catch-all group last."""
    settings = [s for s in athlete.get("sportSettings") or [] if isinstance(s, dict)]
    return sorted(settings, key=lambda s: bool(s.get("other")))


def sport_label(setting: dict[str, Any]) -> str:
    """Return a stable, human readable label for a sport settings group."""
    types = setting.get("types") or []
    if setting.get("other") or not types:
        return "Other"
    return str(types[0])


def _parse_local(value: Any) -> datetime | None:
    """Parse an Intervals local timestamp (no timezone offset)."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def planned_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return calendar-ready dicts, sorted by start, for real calendar items.

    Notes (show_as_note) and events hidden from the athlete are skipped.
    """
    prepared: list[dict[str, Any]] = []

    for event in events:
        if not isinstance(event, dict) or event.get("hide_from_athlete"):
            continue

        start = _parse_local(event.get("start_date_local"))
        if start is None:
            continue

        end = _parse_local(event.get("end_date_local"))
        moving = event.get("moving_time")

        # Intervals returns midnight-to-midnight for undated workouts. Keep
        # those as all-day entries; use the planned duration when there is one.
        all_day = start.time().isoformat() == "00:00:00"
        if all_day:
            start_value: Any = start.date()
            end_value: Any = (end.date() if end else start.date() + timedelta(days=1))
            if end_value <= start_value:
                end_value = start_value + timedelta(days=1)
        else:
            start_value = start
            end_value = end or start + timedelta(seconds=int(moving or 3600))

        prepared.append(
            {
                "uid": str(event.get("id") or event.get("uid") or ""),
                "summary": str(event.get("name") or event.get("category") or "Workout"),
                "description": event.get("description") or None,
                "start": start_value,
                "end": end_value,
                "all_day": all_day,
                "category": event.get("category"),
                "type": event.get("type"),
                "load": event.get("icu_training_load"),
                "moving_time": moving,
                "intensity": event.get("icu_intensity"),
                "completed": bool(event.get("paired_activity_id")),
            }
        )

    return sorted(prepared, key=lambda item: str(item["start"]))


def next_event(events: list[dict[str, Any]], today: date) -> dict[str, Any] | None:
    """Return the next planned, not yet completed event on or after today."""
    for item in planned_events(events):
        start = item["start"]
        day = start if isinstance(start, date) and not isinstance(start, datetime) else start.date()
        if day >= today and not item["completed"]:
            return item
    return None


# --- DFA alpha-1 -------------------------------------------------------------
# Intervals delivers dfa_a1 as a per-second stream. The raw curve is noisy and
# useless as a sensor; what matters is how long a session sat in each band and
# at which heart rate / power the curve crossed the aerobic threshold.
#
# Bands follow the common reading of DFA alpha-1:
#   > 0.75  aerobic, below the first threshold
#   0.5-0.75 transition
#   < 0.5   above the second threshold

DFA_AEROBIC = 0.75
DFA_ANAEROBIC = 0.5
# Samples within this window are used to read off the threshold HR / power.
DFA_THRESHOLD_WINDOW = (0.70, 0.80)


def dfa_summary(
    dfa: list[Any] | None,
    heartrate: list[Any] | None = None,
    watts: list[Any] | None = None,
    sample_secs: int = 1,
    skip_secs: int = 0,
) -> dict[str, Any] | None:
    """Summarise a DFA alpha-1 stream.

    ``sample_secs`` is the spacing between two samples, so a thinned stream
    still yields correct durations. ``skip_secs`` drops the beginning of the
    session, where the algorithm has not settled yet.
    """
    if not dfa:
        return None

    skip = max(0, int(skip_secs // max(sample_secs, 1)))
    values: list[float] = []
    hr_window: list[float] = []
    watt_window: list[float] = []
    above = band = below = 0

    for index in range(skip, len(dfa)):
        raw = dfa[index]
        if raw is None:
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        # Guard against artefacts. A dfa_a1 of exactly 0 is what Intervals
        # writes before the algorithm has settled - it is not a measurement,
        # and counting it would inflate the anaerobic time.
        if not 0.0 < value <= 2.0:
            continue

        values.append(value)
        if value > DFA_AEROBIC:
            above += 1
        elif value >= DFA_ANAEROBIC:
            band += 1
        else:
            below += 1

        if DFA_THRESHOLD_WINDOW[0] < value < DFA_THRESHOLD_WINDOW[1]:
            if heartrate and index < len(heartrate) and heartrate[index] is not None:
                # A heart rate of zero is a dropped strap signal, not a
                # measurement. Left in, it drags the threshold reading towards
                # zero - visible as a spike straight down in the chart.
                if float(heartrate[index]) > 0:
                    hr_window.append(float(heartrate[index]))
            if watts and index < len(watts) and watts[index] is not None:
                # Zero watts means coasting, not an effort level; including it
                # would drag the threshold power down.
                if float(watts[index]) > 0:
                    watt_window.append(float(watts[index]))

    if not values:
        return None

    def _mean(items: list[float]) -> float | None:
        return round(sum(items) / len(items), 1) if items else None

    return {
        "samples": len(values),
        "mean": round(sum(values) / len(values), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "secs_aerobic": above * sample_secs,
        "secs_transition": band * sample_secs,
        "secs_anaerobic": below * sample_secs,
        "hr_at_threshold": _mean(hr_window),
        "power_at_threshold": _mean(watt_window),
        "threshold_samples": len(hr_window) or len(watt_window),
    }


def streams_to_dict(streams: Any) -> dict[str, list[Any]]:
    """Turn the API's list of stream objects into a name -> data mapping."""
    result: dict[str, list[Any]] = {}
    for stream in streams or []:
        if isinstance(stream, dict) and stream.get("type"):
            result[str(stream["type"])] = stream.get("data") or []
    return result
