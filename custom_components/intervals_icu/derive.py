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
        # TWO counts, not one. Until 0.44.0 this was
        #     "threshold_samples": len(hr_window) or len(watt_window)
        # and the `or` made the number lie: when the strap failed, the WATT
        # count was reported as the heart rate's backing. The ride of
        # 06.06.2026 showed "24 windows" next to a threshold that had no
        # window at all. A count belongs to the value it stands next to.
        "hr_windows": len(hr_window),
        "power_windows": len(watt_window),
    }


try:  # inside the package (Home Assistant)
    from .const import THRESHOLD_MIN_HR, THRESHOLD_MIN_POWER, THRESHOLD_MIN_WINDOWS
except ImportError:  # standalone (test suite loads this file directly)
    from const import THRESHOLD_MIN_HR, THRESHOLD_MIN_POWER, THRESHOLD_MIN_WINDOWS

# Andriolo's representative method cuts the DFA axis into intervals, averages
# power and alpha WITHIN each interval and correlates only those midpoints -
# that is what clears the cardiac lag. Width and minimum count are house
# settings: the published work bins by group, not by a stated width.
DFA_BIN_WIDTH = 0.05
FATIGUE_MIN_BINS = 3


def _read_at(points: list[tuple[float, float]], at: float = 0.75) -> float | None:
    """Bin, fit, read at a given alpha - ONE routine for every read-off.

    Two copies of this would be two answers to one question; the same class
    that has cost this project four releases.
    """
    if len(points) < 2:
        return None
    buckets: dict[int, list[tuple[float, float]]] = {}
    for alpha, value in points:
        buckets.setdefault(int(alpha / DFA_BIN_WIDTH), []).append((alpha, value))
    mids = [
        (sum(a for a, _ in items) / len(items), sum(v for _, v in items) / len(items))
        for items in buckets.values()
    ]
    if len(mids) < FATIGUE_MIN_BINS:
        return None
    if not min(a for a, _ in mids) <= at <= max(a for a, _ in mids):
        return None
    n = len(mids)
    mean_a = sum(a for a, _ in mids) / n
    mean_v = sum(v for _, v in mids) / n
    var = sum((a - mean_a) ** 2 for a, _ in mids)
    if var <= 0:
        return None
    slope = sum((a - mean_a) * (v - mean_v) for a, v in mids) / var
    return round(slope * at + (mean_v - slope * mean_a), 1)


def dfa_hours(
    dfa: list[Any] | None,
    watts: list[Any] | None,
    heartrate: list[Any] | None = None,
    sample_secs: int = 1,
    hour_secs: int = 3600,
) -> list[dict[str, Any]]:
    """Read P(alpha = 0.75) off EACH hour of a ride, separately.

    One reading per ride cannot show fatigue - the whole question is whether
    hour two sits below hour one. The archive held a single window mean per
    ride until 0.45.0, so this is where the hour-by-hour figures come from.

    The read-off is Andriolo's: bin the alpha axis, average both quantities
    inside each bin, fit a line through the BIN MIDPOINTS, read it at 0.75.
    Never extrapolated - if 0.75 lies outside the alpha range actually
    ridden in that hour, the hour carries no value and says so. An
    extrapolated threshold is an invention with a decimal point.
    """
    if not dfa:
        return []
    out: list[dict[str, Any]] = []
    per_hour = max(1, int(hour_secs // max(sample_secs, 1)))
    total = len(dfa)
    hour = 0
    while hour * per_hour < total:
        start, stop = hour * per_hour, min(total, (hour + 1) * per_hour)
        points: list[tuple[float, float]] = []
        hr_points: list[tuple[float, float]] = []
        dropped = 0
        low = 0
        low_ok = low_bad = 0
        for index in range(start, stop):
            alpha = _number(dfa[index])
            watt = _number(watts[index]) if watts and index < len(watts) else None
            pulse = _number(heartrate[index]) if heartrate and index < len(heartrate) else None
            if alpha is None or not 0.0 < alpha <= 2.0:
                dropped += 1
                continue
            if alpha < 0.5:
                if watt is None or watt <= 0:
                    low_bad += 1
                else:
                    low_ok += 1
            if pulse is not None and pulse > 0:
                hr_points.append((alpha, pulse))
            if watt is None or watt <= 0:
                dropped += 1
                continue
            points.append((alpha, watt))
            if alpha < 1.0:
                low += 1

        row: dict[str, Any] = {
            "hour": hour + 1,
            "points": len(points),
            "dropped": dropped,
            # Andriolo's artefact criterion (5 % of beats) is not reproducible
            # here - Intervals hands over no artefact field. This is the
            # SUBSTITUTE and is labelled as one: share of points thrown away.
            "dropped_share": round(dropped / max(1, dropped + len(points)) * 100, 1),
            # Andriolo requires at least half the points below alpha 1.0. On
            # everyday data that leaves too little to decide anything, so it
            # travels as a FIGURE per hour instead of acting as a filter.
            "dynamic_share": round(low / len(points) * 100, 1) if points else None,
            "bins": 0,
            "p075": None,
            "alpha_min": None,
            "alpha_max": None,
            # Die ZWEITE Schwelle, alpha 0,5 (ROGERS: VT2). ERHOBEN, NICHT
            # BENUTZT: kein Renderer liest sie, kein Trainer-Pfad haengt daran.
            # Die Literatur nennt die obere Schwelle die methodisch stabilere
            # (HRVT2 ICC 0,97 gegen HRVT1 0,87), das SIGNAL dort aber deutlich
            # schlechter - deshalb wird erst gemessen und dann entschieden.
            "p050": None,
            # Signalqualitaet im unteren Band, getrennt ausgewiesen: verworfene
            # Punkte gesamt sagen nichts darueber, ob es GERADE DORT schlechter
            # wird, wo die zweite Schwelle liegt.
            "low_points": 0,
            "low_dropped": 0,
            "low_dropped_share": None,
            # Dieselbe Ablesung fuer die HERZFREQUENZ. Sie ist die praktisch
            # wichtigere Haelfte: wer sich nach Stunden noch an die ausgeruhte
            # Schwellen-HF haelt, faehrt zu hart (docs/ausbau.md L1b).
            "hr075": None,
        }
        row["hr075"] = _read_at(hr_points)
        row["p050"] = _read_at(points, 0.5)
        row["low_points"] = low_ok
        row["low_dropped"] = low_bad
        row["low_dropped_share"] = (
            round(low_bad / (low_ok + low_bad) * 100, 1) if (low_ok + low_bad) else None
        )
        if len(points) >= 2:
            buckets: dict[int, list[tuple[float, float]]] = {}
            for alpha, watt in points:
                buckets.setdefault(int(alpha / DFA_BIN_WIDTH), []).append((alpha, watt))
            mids = [
                (sum(a for a, _ in items) / len(items), sum(w for _, w in items) / len(items))
                for items in buckets.values()
            ]
            row["bins"] = len(mids)
            row["alpha_min"] = round(min(a for a, _ in mids), 3)
            row["alpha_max"] = round(max(a for a, _ in mids), 3)
            if len(mids) >= FATIGUE_MIN_BINS and row["alpha_min"] <= 0.75 <= row["alpha_max"]:
                n = len(mids)
                mean_a = sum(a for a, _ in mids) / n
                mean_w = sum(w for _, w in mids) / n
                var = sum((a - mean_a) ** 2 for a, _ in mids)
                if var > 0:
                    slope = sum((a - mean_a) * (w - mean_w) for a, w in mids) / var
                    intercept = mean_w - slope * mean_a
                    row["p075"] = round(slope * 0.75 + intercept, 1)
                    row["slope"] = round(slope, 1)
                    resid = sum((w - (slope * a + intercept)) ** 2 for a, w in mids)
                    tot = sum((w - mean_w) ** 2 for _, w in mids)
                    row["r2"] = round(1 - resid / tot, 3) if tot > 0 else None
        out.append(row)
        hour += 1
    return out


def threshold_verdict(summary: dict[str, Any] | None) -> dict[str, Any]:
    """Judge ONE threshold reading: measurement, or failure?

    THE one place. Before 0.45.0 this judgement stood in five places with
    four different rules - coach.anchors (hr > 0 and >= 5 windows), the
    panel's isSolid (same), the panel's power row (windows only),
    importer.threshold_series (>= 1 window) and analytics (nothing at all).
    The heart rate curve therefore dropped the 06.06. failure while the
    power curve below it kept the same ride.

    The defect class is the one from §7: the check sat at the INPUT - every
    single sample was filtered - and nobody looked at the RESULT. A mean over
    nothing is still a mean, and it carried a count that belonged to another
    value.

    Returns the reading plus its verdict. `usable` decides whether the value
    may pull a median, a mean or a curve; `shown` stays True either way,
    because a failure that silently disappears is the other half of the same
    mistake (§7 class 4, the silent exit).
    """
    summary = summary if isinstance(summary, dict) else {}
    hr = _number(summary.get("hr_at_threshold"))
    power = _number(summary.get("power_at_threshold"))
    hr_windows = int(summary.get("hr_windows") or 0)
    power_windows = int(summary.get("power_windows") or 0)

    hr_ok = hr is not None and hr >= THRESHOLD_MIN_HR
    power_ok = power is not None and power >= THRESHOLD_MIN_POWER

    # Each value against ITS OWN count - that is the whole point of splitting
    # the field. A ride whose strap failed may still carry a usable power
    # reading, and vice versa.
    hr_usable = hr_ok and hr_windows >= THRESHOLD_MIN_WINDOWS
    power_usable = power_ok and power_windows >= THRESHOLD_MIN_WINDOWS

    reason = None
    if hr is not None and not hr_ok:
        reason = "hr_implausible"
    elif power is not None and not power_ok:
        reason = "power_implausible"
    elif hr is None and power is None:
        reason = "no_reading"
    elif not (hr_usable or power_usable):
        reason = "too_few_windows"

    return {
        "hr": hr,
        "power": power,
        "hr_windows": hr_windows,
        "power_windows": power_windows,
        "hr_usable": hr_usable,
        "power_usable": power_usable,
        "usable": hr_usable or power_usable,
        "failure": reason in ("hr_implausible", "power_implausible"),
        "reason": reason,
    }


def streams_to_dict(streams: Any) -> dict[str, list[Any]]:
    """Turn the API's list of stream objects into a name -> data mapping."""
    result: dict[str, list[Any]] = {}
    for stream in streams or []:
        if isinstance(stream, dict) and stream.get("type"):
            result[str(stream["type"])] = stream.get("data") or []
    return result


# --- best mean power over a moving-time axis (docs/ausbau.md J1/K1) --------
# Gaps longer than this count as neither work nor riding time. Without a
# moving-time axis the window breaks at every stop: the first run of the J1
# measurement produced 20-minute values with no matching 5-minute values,
# which is impossible and is what gave the error away.
MOVING_GAP_S = 60


def _time_axis(streams: dict[str, Any]) -> list[float] | None:
    """The time channel, as seconds. Missing or degenerate returns None."""
    raw = streams.get("time") if isinstance(streams, dict) else None
    if not isinstance(raw, list) or len(raw) < 2:
        return None
    out: list[float] = []
    for value in raw:
        number = _number(value)
        if number is None:
            return None
        out.append(number)
    return out


def best_mean_watts(streams: Any, seconds: float) -> float | None:
    """The best mean power over `seconds` of MOVING time.

    Why moving time and not sample count: the streams handed out by this
    integration are thinned to at most 900 points, so the step between samples
    is 7-18 s depending on ride length, and a pause leaves a hole in the time
    channel rather than in the index. Counting samples would silently measure
    a different window on every ride.

    The mean is weighted by the duration each sample represents, not by the
    number of samples - on a thinned stream those are different quantities.
    Returns None when the ride never carries `seconds` of continuous riding:
    an absent value, never a value from a shorter window, because a maximum
    over less material is a different number (J1 Befund 2).
    """
    if not isinstance(streams, dict) or seconds <= 0:
        return None
    axis = _time_axis(streams)
    watts_raw = streams.get("watts")
    if axis is None or not isinstance(watts_raw, list) or len(watts_raw) != len(axis):
        return None

    # (duration, energy) per sample, restarting at every pause.
    runs: list[list[tuple[float, float]]] = [[]]
    for index in range(1, len(axis)):
        step = axis[index] - axis[index - 1]
        power = _number(watts_raw[index])
        if step <= 0 or step > MOVING_GAP_S or power is None:
            if runs[-1]:
                runs.append([])
            continue
        runs[-1].append((step, max(0.0, power) * step))

    best: float | None = None
    for run in runs:
        if not run:
            continue
        # widening/narrowing window over one uninterrupted run
        start = 0
        span = 0.0
        energy = 0.0
        for end in range(len(run)):
            span += run[end][0]
            energy += run[end][1]
            while span - run[start][0] >= seconds:
                span -= run[start][0]
                energy -= run[start][1]
                start += 1
            if span >= seconds and span > 0:
                mean = energy / span
                if best is None or mean > best:
                    best = mean
    return best


def test_measures(streams: Any, short_min: float, long_min: float) -> dict[str, Any]:
    """The two protocol numbers of one marked test ride.

    Deliberately the best effort of the WHOLE ride rather than a search for
    the protocol's shape. At the fresh appointment the two all-outs are the
    only maximal efforts on the ride; at the fatigued one they sit behind the
    fatigue block, which is ridden at 80 % and cannot beat them. Looking for
    the protocol in the data instead would be recognition - exactly what K2
    hands to the athlete, and what J1 showed goes wrong when a ride is asked
    to confirm a shape it was never ridden to.

    `reason` is filled whenever a value is missing, because a block that draws
    nothing must say why (Fehlerklasse 4, der stille Ausstieg).
    """
    out: dict[str, Any] = {"p5": None, "p20": None, "reason": None}
    if not isinstance(streams, dict) or not streams.get("watts"):
        out["reason"] = "Die Fahrt trägt keinen Leistungsstrom."
        return out
    if _time_axis(streams) is None:
        out["reason"] = "Die Fahrt trägt keine brauchbare Zeitachse."
        return out
    out["p5"] = best_mean_watts(streams, short_min * 60.0)
    out["p20"] = best_mean_watts(streams, long_min * 60.0)
    if out["p20"] is None:
        out["reason"] = (
            f"Kein zusammenhängender {long_min:.0f}-Minuten-Abschnitt in der "
            "Bewegungszeit — als Termin brauchbar ist die Fahrt damit nicht."
        )
    elif out["p5"] is None:
        out["reason"] = f"Kein zusammenhängender {short_min:.0f}-Minuten-Abschnitt."
    return out


# --- laps ----------------------------------------------------------------
# The API returns the laps on the activity itself (intervals=true), and the
# field names are not documented. Every value therefore has a list of
# candidate names, newest naming first: an unknown payload degrades to a
# missing value rather than to an exception, and `normalize_laps` reports
# which keys it actually saw so the mapping can be corrected against a real
# account instead of guessed.
_LAP_FIELDS: dict[str, tuple[str, ...]] = {
    "label": ("label", "name", "type"),
    "type": ("type", "group_id"),
    # BEIDE werden gehalten, und WELCHER richtig ist, haengt am Aufrufer -
    # der Hinweis hier nannte bis 0.48.1 nur die eine Haelfte und fuehrte
    # damit zur falschen Wahl (PROJEKTSTAND §7):
    #   * PANEL: bekommt einen GEDUENNTEN Strom (sample_secs 5-18). Der Index
    #     zaehlt im Original und passt dort nicht -> ueber die ZEIT zuordnen.
    #   * IMPORT: rechnet auf dem UNGEDUENNTEN 1-Hz-Strom. Dort ist der Index
    #     exakt, die SEKUNDEN aber nicht: `start_s` laeuft in verstrichener
    #     Zeit, der Strom in Bewegungszeit. Bei der Einheit vom 01.09.2026
    #     endet der letzte Index bei 2859 (= Zahl der Stromwerte), die
    #     Sekundenachse bei 2973 -> 114 Stellen Versatz, genau die Standzeit.
    #     -> ueber den INDEX zuordnen.
    "start_s": ("start_time",),
    "end_s": ("end_time",),
    "start_index": ("start_index",),
    "end_index": ("end_index",),
    "start": ("start_time", "start_index", "start"),
    "moving_time": ("moving_time", "elapsed_time", "duration"),
    "distance": ("distance",),
    "avg_watts": ("average_watts", "avg_watts", "icu_average_watts", "watts"),
    "np_watts": ("weighted_average_watts", "icu_weighted_avg_watts", "normalized_watts"),
    "max_watts": ("max_watts",),
    "avg_hr": ("average_heartrate", "avg_hr", "heartrate"),
    "max_hr": ("max_heartrate", "max_hr"),
    "avg_cadence": ("average_cadence", "avg_cadence", "cadence"),
    "avg_speed": ("average_speed", "avg_speed", "speed"),
    "intensity": ("intensity", "icu_intensity"),
    "zone": ("zone", "power_zone", "hr_zone"),
    "load": ("icu_training_load", "training_load", "load"),
    "decoupling": ("decoupling", "icu_hr_pw_decoupling", "hr_pw_decoupling"),
    "ef": ("efficiency_factor", "icu_efficiency_factor", "ef"),
    "dfa_a1": ("average_dfa_a1", "dfa_a1", "avg_dfa_a1", "icu_dfa_a1"),
    "w_balance": ("wbal_start", "w_balance", "wbal"),
}

_LAP_LISTS = ("icu_intervals", "intervals", "laps", "icu_laps")


def normalize_laps(payload: Any) -> dict[str, Any]:
    """Pull the laps out of an activity payload into a stable shape.

    Returns {"laps": [...], "seen_keys": [...], "source": "<field>"}. The
    caller can show the laps; `seen_keys` exists so an unmapped payload can
    be diagnosed from the panel instead of from a debugger.
    """
    if not isinstance(payload, dict):
        return {"laps": [], "seen_keys": [], "source": None}

    raw: list[Any] = []
    source: str | None = None
    for key in _LAP_LISTS:
        value = payload.get(key)
        if isinstance(value, list) and value:
            raw, source = value, key
            break

    seen: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            for key in item:
                if key not in seen:
                    seen.append(key)

    laps: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        lap: dict[str, Any] = {"n": index + 1}
        for target, candidates in _LAP_FIELDS.items():
            for name in candidates:
                if item.get(name) is not None:
                    lap[target] = item[name]
                    break
        # Efficiency factor is the one number worth deriving when missing:
        # watts per heartbeat is what shows a fading effort across a series.
        if lap.get("ef") is None:
            watts, hr = lap.get("np_watts") or lap.get("avg_watts"), lap.get("avg_hr")
            try:
                if watts and hr and float(hr) > 0:
                    lap["ef"] = round(float(watts) / float(hr), 2)
            except (TypeError, ValueError):
                pass
        laps.append(lap)

    return {"laps": laps, "seen_keys": sorted(seen), "source": source}


# --- what counts as a steady endurance session --------------------------------
# ONE definition, used by the durability tile and by the decoupling series in
# the load tab. Before 0.39.0 the series filtered on duration alone while its
# own docstring promised "steady" - the tile and the chart could therefore show
# decoupling from two different populations without anything saying so.

try:  # inside the package (Home Assistant)
    from .const import (
        DURABILITY_EXCLUDED_TYPES,
        DURABILITY_MAX_INTENSITY,
        DURABILITY_VI_FULL,
        DURABILITY_VI_NONE,
        DURABILITY_MIN_MINUTES,
        FATIGUE_MAX_ABOVE_Z2,
        FATIGUE_MIN_MINUTES,
        BLOCK_MIN_POINTS,
        BLOCK_MIN_SECONDS,
        BLOCK_WARMUP_DISCARD_S,
    )
except ImportError:  # standalone (test suite loads this file directly)
    from const import (
        DURABILITY_EXCLUDED_TYPES,
        DURABILITY_MAX_INTENSITY,
        DURABILITY_VI_FULL,
        DURABILITY_VI_NONE,
        DURABILITY_MIN_MINUTES,
        FATIGUE_MAX_ABOVE_Z2,
        FATIGUE_MIN_MINUTES,
        BLOCK_MIN_POINTS,
        BLOCK_MIN_SECONDS,
        BLOCK_WARMUP_DISCARD_S,
    )


def _number(value: Any) -> float | None:
    """Return a float, or None when the field is missing or unusable."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def variability_index(activity: dict[str, Any]) -> float | None:
    """Return normalised power / average power, or None when not computable.

    The criterion for an interpretable decoupling reading is a STEADY effort,
    not a low average intensity: a rolling group ride at intensity 70 passes an
    intensity filter while a steady tempo ride at 81 does not. Both fields this
    needs are already in the archive.
    """
    normalised = _number(activity.get("icu_weighted_avg_watts"))
    average = _number(activity.get("icu_average_watts"))
    if not normalised or not average:
        return None
    return normalised / average


def _median(values: list[float]) -> float | None:
    """Echter Median - bei GERADER Anzahl das Mittel der beiden mittleren.

    Eine Fassung mit `sorted(v)[n // 2]` greift dort den OBEREN Wert. Der
    Fehler taeuscht sich nach der Datenlage: bei ungerader Blockzahl faellt er
    nie auf, bei gerader immer - und die SweetSpot-Einheiten haben IMMER zwei
    Bloecke (PROJEKTSTAND §7).
    """
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    if n % 2:
        return ordered[n // 2]
    return (ordered[n // 2 - 1] + ordered[n // 2]) / 2.0


def dfa_blocks(
    dfa: list[Any] | None,
    watts: list[Any] | None,
    heartrate: list[Any] | None,
    laps: list[dict[str, Any]] | None,
    sample_secs: int = 1,
) -> list[dict[str, Any]]:
    """Ein Wert je BLOCK, direkt abgelesen - kein Fit, keine Interpolation.

    Die Blockgrenzen kommen aus Intervals' eigenen Abschnitten, nicht aus einer
    Erkennung: die Zuordnung trifft der Athlet (K2). Eine Segmentierung aus dem
    Leistungsstrom hielte einen Berg, eine Ampel oder eine Pause fuer einen
    Block - Runde 1 aus L0 in neuer Verkleidung.

    Die ersten BLOCK_WARMUP_DISCARD_S Sekunden fallen weg. Ohne das misst der
    Blockwert den EINSCHWINGVORGANG mit: alpha startet hoch und faellt
    innerhalb der ersten zwei Minuten, was 69 bis 83 % der Streuung ausmacht
    (PROJEKTSTAND §7).
    """
    if not dfa or not laps:
        return []
    out: list[dict[str, Any]] = []
    for lap in laps:
        if not isinstance(lap, dict):
            continue
        # ueber den INDEX, nicht ueber die Sekunden: siehe normalize_laps.
        start = _number(lap.get("start_index"))
        end = _number(lap.get("end_index"))
        dur = _number(lap.get("moving_time")) or 0.0
        label = str(lap.get("label") or "")
        if start is None or end is None or dur < BLOCK_MIN_SECONDS:
            continue
        alphas: list[float] = []
        power: list[float] = []
        pulse: list[float] = []
        # Verworfen wird nach SEKUNDEN, gezaehlt wird in Stromstellen - auf dem
        # ungeduennten 1-Hz-Strom ist das dasselbe, und sample_secs traegt den
        # Unterschied, falls je ein geduennter Strom hier ankommt.
        kept = start + BLOCK_WARMUP_DISCARD_S / max(sample_secs, 1)
        for index in range(len(dfa)):
            # `end_index` zeigt auf die Stelle NACH dem Block: bei der Einheit
            # vom 01.09.2026 endet der letzte Lap auf 2859 bei 2856 Werten.
            # Mit `<=` liefe der erste Wert des Folgeabschnitts mit - bei einem
            # Intervall waere das der erste Wert der Pause.
            if index < kept or index >= end:
                continue
            value = _number(dfa[index])
            if value is None or not 0.0 < value <= 2.0:
                continue
            alphas.append(value)
            watt = _number(watts[index]) if watts and index < len(watts) else None
            if watt and watt > 0:
                power.append(watt)
            beat = _number(heartrate[index]) if heartrate and index < len(heartrate) else None
            if beat and beat > 0:
                pulse.append(beat)
        if len(alphas) < BLOCK_MIN_POINTS:
            continue
        mean_a = sum(alphas) / len(alphas)
        out.append({
            "label": label,
            "start_index": round(start),
            # Intervals' EIGENER Abschnittswert - eine FREMDE Quelle, und die
            # einzige in diesem Paket. Er ist ein Mittel ueber den GANZEN Block
            # samt Anlauf und liegt deshalb systematisch hoeher als unser
            # Median; als Ersatz taugt er nicht. Aber die REIHENFOLGE muss
            # stimmen: laeuft sie auseinander, stimmt etwas am Ausschnitt.
            "lap_alpha": _number(lap.get("dfa_a1")),
            "minutes": round(dur / 60.0, 1),
            "points": len(alphas),
            "discarded_s": BLOCK_WARMUP_DISCARD_S,
            "alpha": round(_median(alphas), 3),
            "alpha_sd": round((sum((x - mean_a) ** 2 for x in alphas) / len(alphas)) ** 0.5, 3),
            "watts": round(_median(power)) if power else None,
            "hr": round(_median(pulse)) if pulse else None,
        })
    return out


def drop_warmup_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Abschnitte aussortieren, die als Arbeit etikettiert sind, aber keine ist.

    Geraete etikettieren einen Einroll- oder Ausrollteil gelegentlich als WORK.
    Die Leitzahl "erster Arbeitsblock" trifft dann den falschen - am 02.07.2026
    stand sie bei 182 W statt 238 W, am 19.07. bei 197 statt 278.

    NICHT UEBER DIE LEISTUNG: bei der Tempo-Einheit vom 13.09.2026 traegt der
    lockere Abschnitt 164 W und der echte vierte Block 165 W - zwischen ihnen
    liegen 0,6 Prozentpunkte, jede Wattschwelle wirft beide zusammen weg.

    NICHT GEGEN DEN KORRIDOR: das waere zirkulaer. Die Regelung soll gerade
    melden, wenn alpha ueber dem Korridor liegt (so kam der +5-%-Schritt vom
    23.07. zustande). Wer Bloecke oberhalb des Korridors entfernt, loescht
    genau den Befund, den er messen will. Es liegt nahe und ist falsch.

    SONDERN als AUSREISSER gegen die Einheit selbst: ein Block faellt raus,
    wenn sein alpha mehr als drei Streuungen der UEBRIGEN Bloecke ueber deren
    Median liegt UND er weniger Leistung traegt als der staerkste. Beide
    Bedingungen aus den Zahlen der Einheit, keine gesetzte Grenze.

    Das Abstandsmass ist nicht schmueckend: am 11.08.2026 liegt ein ECHTER
    Block mit alpha 0,431 ueber dem staerksten (0,426). Ohne die drei
    Streuungen fiele er raus.
    """
    work = [b for b in blocks if b.get("label") == "WORK"]
    if len(work) < 3:
        return blocks
    powers = [b["watts"] for b in work if b.get("watts")]
    if not powers:
        return blocks
    top = max(powers)
    drop: list[int] = []
    for i, b in enumerate(work):
        rest = [x["alpha"] for j, x in enumerate(work)
                if j != i and x.get("alpha") is not None]
        if len(rest) < 2 or b.get("alpha") is None or not b.get("watts"):
            continue
        mid = _median(rest)
        mean = sum(rest) / len(rest)
        sd = (sum((x - mean) ** 2 for x in rest) / len(rest)) ** 0.5
        if b["alpha"] > mid + 3 * sd and b["watts"] < top:
            drop.append(id(b))
    if not drop:
        return blocks
    out = []
    for b in blocks:
        if id(b) in drop:
            out.append({**b, "label": "WARMUP_LABELLED_WORK",
                        "dropped_reason": "alpha-Ausreisser gegen die eigene Einheit"})
        else:
            out.append(b)
    return out


def above_endurance_share(activity: dict[str, Any]) -> float | None:
    """Return the share of time spent ABOVE zone 2, in percent.

    Zone 3 upwards is where a session stops being base work: tempo, threshold,
    VO2max. The SweetSpot entry that Intervals adds is an OVERLAPPING band
    between zones 3 and 4 and is deliberately left out - counting it would
    count the same seconds twice.
    """
    zones = activity.get("icu_zone_times")
    if not isinstance(zones, (list, tuple)) or not zones:
        return None
    ordered: list[tuple[int, float]] = []
    for entry in zones:
        if isinstance(entry, dict):
            name = str(entry.get("id") or "")
            secs = _number(entry.get("secs"))
            if not name.startswith("Z") or not name[1:].isdigit() or secs is None:
                continue
            ordered.append((int(name[1:]), secs))
        else:
            secs = _number(entry)
            if secs is not None:
                ordered.append((len(ordered) + 1, secs))
    if not ordered:
        return None
    total = sum(secs for _, secs in ordered)
    if total <= 0:
        return None
    return sum(secs for number, secs in ordered if number >= 3) / total * 100


def fatigue_curve_reason(
    activity: dict[str, Any], min_minutes: float = FATIGUE_MIN_MINUTES
) -> str | None:
    """Return None when a ride may lend its HOUR-BY-HOUR course, else why not.

    TWO CRITERIA, TWO QUESTIONS - and neither replaces the other. The
    variability index asks how JUMPY the pedalling was; this asks whether the
    session was STRUCTURED. A 20-minute block is extremely even, just at a
    different level, so the VI reads it as a quiet ride: measured on ten rides,
    the VI ranges overlap completely (structured 1,031-1,275 against base
    1,000-1,088) and DURABILITY_VI_NONE would have admitted all three of the
    rides that wrecked round 3 in docs/ausbau.md L0.

    Structured sessions are excluded BEFORE the measurement, never after. A
    goodness-of-fit criterion applied afterwards narrows the selection onto
    exactly the structured rides and collects the confounder instead of
    dropping it - that is how round 3 turned a training plan into "fatigue".
    """
    if not isinstance(activity, dict):
        return "no_activity"
    if (activity.get("moving_time") or 0) / 60 < min_minutes:
        return "short"
    share = above_endurance_share(activity)
    if share is None:
        return "no_zones"
    if share > FATIGUE_MAX_ABOVE_Z2:
        return "structured"
    # The jumpiness question, asked SEPARATELY and answered with the house's
    # own limit. A ride can be unstructured and still too jumpy to read.
    index = variability_index(activity)
    if index is not None and index > DURABILITY_VI_NONE:
        return "variable"
    return None


def steady_endurance_reason(
    activity: dict[str, Any], min_minutes: float = DURABILITY_MIN_MINUTES
) -> str | None:
    """Return None when the session qualifies, else why it does not.

    Reasons are returned rather than a bare False so the panel can say what was
    left out instead of showing a number whose population is invisible.
    """
    if not isinstance(activity, dict):
        return "no_activity"
    if (activity.get("moving_time") or 0) / 60 < min_minutes:
        return "short"
    if str(activity.get("type") or "") in DURABILITY_EXCLUDED_TYPES:
        return "indoor"
    if (_number(activity.get("icu_intensity")) or 0) >= DURABILITY_MAX_INTENSITY:
        return "intense"
    index = variability_index(activity)
    if index is None:
        # NOT "variable" - nobody knows whether it was. Until 0.39.0 both cases
        # were counted together and the tile said "64 too wavy" over 53 rides
        # with no power meter at all (PROJEKTSTAND section 7).
        return "no_power"
    if index > DURABILITY_VI_NONE:
        return "variable"
    return None


def steady_weight(activity: dict[str, Any]) -> float:
    """Return how much a qualifying ride counts, from 1.0 down to 0.0.

    An exclusion is a yes/no decision about a stepless quantity. The variability
    index says how evenly a ride was pedalled, and evenness fades - so it weighs
    the ride instead of admitting it (docs/ausbau.md G3). Callers must have
    asked steady_endurance_reason() first; a ride without power has no weight to
    give, which is why it is dropped rather than weighted zero.
    """
    index = variability_index(activity)
    if index is None:
        return 0.0
    span = DURABILITY_VI_NONE - DURABILITY_VI_FULL
    return max(0.0, min(1.0, (DURABILITY_VI_NONE - index) / span)) if span else 0.0
