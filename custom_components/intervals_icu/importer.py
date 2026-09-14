"""Import logic for the local Intervals.icu archive.

Kept free of Home Assistant imports so the whole import can be replayed
against recorded payloads in tests. Everything here works on a plain dict
that the Store persists as-is.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Callable

from . import derive

_LOGGER = logging.getLogger(__name__)

# Only these activity fields are stored. The API accepts a fields= parameter,
# so the payload is trimmed on the server side already: roughly 30 of about
# 200 fields, which keeps a full season well under a megabyte.
ACTIVITY_FIELDS: tuple[str, ...] = (
    "id",
    "start_date_local",
    "type",
    "name",
    "source",
    "icu_training_load",
    "icu_intensity",
    "icu_ctl",
    "icu_atl",
    "moving_time",
    "elapsed_time",
    "distance",
    "total_elevation_gain",
    "average_heartrate",
    "max_heartrate",
    "average_speed",
    "pace",
    "calories",
    "trimp",
    "icu_average_watts",
    "icu_weighted_avg_watts",
    "icu_joules",
    "icu_ftp",
    "icu_efficiency_factor",
    "decoupling",
    "polarization_index",
    "icu_hr_zone_times",
    "icu_zone_times",
    "icu_variability_index",
    "average_cadence",
    "average_speed",
    "max_heartrate",
    "icu_pm_ftp",
    "icu_rolling_ftp",
    "device_name",
    "gear",
    "race",
    "commute",
    "icu_rpe",
    "feel",
    "paired_event_id",
    "stream_types",
)

# Streams pulled per activity for the DFA alpha-1 summary.
DFA_STREAMS = ("dfa_a1", "heartrate", "watts")

# Intervals never hands out activities that came in through Strava.
UNAVAILABLE_NOTE = "_note"

# Bumped whenever the DFA maths changes. Stored summaries carrying an older
# version are dropped and recomputed - the streams themselves are not kept, so
# a fix would otherwise never reach the values already in the archive.
DFA_ALGO_VERSION = 7

# Bumped when ACTIVITY_FIELDS grows: stored summaries were fetched with the
# old field list and would otherwise never gain the new columns.
ACTIVITY_FIELDS_VERSION = 2


def empty_data(athlete_id: str) -> dict[str, Any]:
    """Return a fresh archive skeleton."""
    return {
        "athlete_id": athlete_id,
        "wellness": {},
        "activities": {},
        "dfa": {},
        "unavailable": [],
        # the athlete's goal profile - written by the panel, never by the API
        "goal": None,
        # hand-set measurement-condition labels per day (docs/ausbau.md B2).
        # MUST live in this skeleton: async_load fills missing keys at the
        # top level only, so a block the skeleton does not know never comes
        # into being on an old archive - the exact gap 0.35.0 repaired.
        "day_context": {},
        # markierte Stufentests und ihre gemessenen Zahlen (docs/ausbau.md N).
        # Vierter Block, der diesen Eintrag braucht, nach goal und day_context -
        # und das vierte Mal, dass sich hier sonst dieselbe Luecke oeffnet. Ein
        # neuer Archivblock OHNE Eintrag hier UND Migration in store.async_load
        # gilt als unfertig, nicht als Ausnahme (PROJEKTSTAND 7).
        "ramp_tests": {},
        "last_import": None,
        "full_import_done": False,
        "dfa_version": DFA_ALGO_VERSION,
        "fields_version": ACTIVITY_FIELDS_VERSION,
    }


def should_full_import(data: dict[str, Any]) -> bool:
    """Return True while the full history has not been walked yet.

    Deliberately its own marker instead of "is the archive empty": the routine
    refresh fills the recent window into the archive within seconds of setup,
    so emptiness stops being a usable signal almost immediately.
    """
    return not data.get("full_import_done")


def drop_outdated_dfa(data: dict[str, Any]) -> int:
    """Discard DFA summaries computed by an older version of the maths."""
    if data.get("dfa_version") == DFA_ALGO_VERSION:
        return 0
    dropped = len(data.get("dfa") or {})
    data["dfa"] = {}
    data["dfa_version"] = DFA_ALGO_VERSION
    return dropped


def needs_activity_refetch(data: dict[str, Any]) -> bool:
    """Return True when stored activities predate the current field list."""
    return data.get("fields_version") != ACTIVITY_FIELDS_VERSION


def mark_activities_current(data: dict[str, Any]) -> None:
    """Record that the archive now holds the current activity field set."""
    data["fields_version"] = ACTIVITY_FIELDS_VERSION


def is_unavailable(activity: dict[str, Any]) -> bool:
    """Return True for placeholder records the API cannot deliver.

    Activities synced from Strava come back as a stub carrying a note instead
    of data. Importing them would punch holes into every chart.
    """
    if UNAVAILABLE_NOTE in activity:
        return True
    return activity.get("type") is None and activity.get("icu_training_load") is None


def has_power(activity: dict[str, Any]) -> bool:
    """Return True when the activity carries a power stream."""
    return "watts" in (activity.get("stream_types") or [])


def has_dfa(activity: dict[str, Any]) -> bool:
    """Return True when Intervals computed DFA alpha-1 for this activity."""
    return "dfa_a1" in (activity.get("stream_types") or [])


def merge_wellness(data: dict[str, Any], rows: Any) -> int:
    """Merge wellness rows into the archive, returning the changed count."""
    changed = 0
    for row in derive.sort_rows(rows if isinstance(rows, list) else []):
        day = str(row["id"])
        if data["wellness"].get(day) != row:
            data["wellness"][day] = row
            changed += 1
    return changed


async def async_import_wellness(
    client: Any,
    data: dict[str, Any],
    oldest: date,
    newest: date,
) -> int:
    """Fetch a wellness range and merge it into the archive."""
    return merge_wellness(data, await client.async_get_wellness(oldest, newest))


def merge_activities(data: dict[str, Any], rows: Any) -> int:
    """Merge activity summaries into the archive, returning the changed count."""
    changed = 0

    for activity in rows if isinstance(rows, list) else []:
        if not isinstance(activity, dict) or not activity.get("id"):
            continue

        key = str(activity["id"])
        if is_unavailable(activity):
            if key not in data["unavailable"]:
                data["unavailable"].append(key)
            continue

        if data["activities"].get(key) != activity:
            data["activities"][key] = activity
            changed += 1

    return changed


async def async_import_activities(
    client: Any,
    data: dict[str, Any],
    oldest: date,
    newest: date,
) -> int:
    """Fetch an activity range and merge the summaries into the archive."""
    rows = await client.async_get_activities(oldest, newest, fields=ACTIVITY_FIELDS)
    return merge_activities(data, rows)


def pending_dfa(data: dict[str, Any]) -> list[str]:
    """Return activity ids that carry a DFA stream but have no summary yet."""
    return [
        key
        for key, activity in sorted(data["activities"].items())
        if has_dfa(activity) and key not in data["dfa"]
    ]


async def async_import_dfa(
    client: Any,
    data: dict[str, Any],
    limit: int | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> int:
    """Fetch streams for activities without a DFA summary and reduce them.

    Only the summary is kept; the per-second streams are thrown away again.
    A failing activity is remembered as an empty summary so it is not fetched
    over and over on every refresh.
    """
    todo = pending_dfa(data)
    if limit is not None:
        todo = todo[:limit]

    done = 0
    for key in todo:
        try:
            streams = await client.async_get_streams(key, DFA_STREAMS)
        except Exception as err:  # noqa: BLE001 - one bad activity must not stop the import
            _LOGGER.debug("streams for %s failed: %s", key, err)
            data["dfa"][key] = {}
            continue

        by_name = derive.streams_to_dict(streams)
        summary = derive.dfa_summary(
            by_name.get("dfa_a1"),
            by_name.get("heartrate"),
            by_name.get("watts"),
        )
        if summary:
            # Der Stundenverlauf entsteht HIER, aus den ungeduennten Stroemen -
            # sie werden gleich danach weggeworfen und sind spaeter nicht mehr
            # zu haben. Genau diese Luecke hat Paket L bis 0.44.0 blockiert:
            # das Archiv trug ein Fenstermittel je Fahrt und keinen Verlauf.
            summary["hours"] = derive.dfa_hours(
                by_name.get("dfa_a1"), by_name.get("watts"), by_name.get("heartrate")
            )
            # Die Bloecke brauchen die Abschnittsgrenzen des Athleten, und die
            # stehen NICHT in den Stroemen. Zweiter Abruf, nur hier - Laps
            # werden sonst nirgends archiviert, und die Stroeme sind gleich
            # danach weg (docs/ausbau.md M4).
            laps: list[dict[str, Any]] = []
            try:
                laps = derive.normalize_laps(
                    await client.async_get_intervals(key)
                ).get("laps") or []
            except Exception as err:  # noqa: BLE001 - eine Fahrt ohne Laps ist kein Abbruch
                _LOGGER.debug("laps for %s failed: %s", key, err)
            summary["blocks"] = derive.drop_warmup_blocks(derive.dfa_blocks(
                by_name.get("dfa_a1"), by_name.get("watts"),
                by_name.get("heartrate"), laps,
            ))
        data["dfa"][key] = summary or {}
        done += 1
        if progress is not None:
            progress(done, len(todo))

    return done


def pmc_series(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the performance management series, oldest first."""
    series: list[dict[str, Any]] = []
    for day in sorted(data["wellness"]):
        row = data["wellness"][day]
        ctl = row.get("ctl")
        atl = row.get("atl")
        series.append(
            {
                "date": day,
                "ctl": ctl,
                "atl": atl,
                "form": (ctl - atl) if ctl is not None and atl is not None else None,
                "load": row.get("ctlLoad"),
            }
        )
    return series


def activity_list(
    data: dict[str, Any],
    limit: int | None = None,
    oldest: str | None = None,
) -> list[dict[str, Any]]:
    """Return activity summaries, newest first, with the DFA summary merged in."""
    items = []
    for key, activity in data["activities"].items():
        start = str(activity.get("start_date_local") or "")
        if oldest and start[:10] < oldest:
            continue
        merged = dict(activity)
        merged["dfa"] = data["dfa"].get(key) or None
        items.append(merged)

    items.sort(key=lambda item: str(item.get("start_date_local") or ""), reverse=True)
    return items[:limit] if limit else items


def threshold_series(
    data: dict[str, Any], since: str | None = None
) -> list[dict[str, Any]]:
    """Return the aerobic threshold read off each activity, oldest first.

    Only activities with enough samples inside the DFA threshold window carry
    a meaningful reading, so the sample count travels with the value.

    `since` is an inclusive lower bound on the date (YYYY-MM-DD) and has no
    upper bound on purpose: a reading dated in the future - a watch with a
    wrong clock - must not disappear without a word.
    """
    series: list[dict[str, Any]] = []
    for key, activity in data["activities"].items():
        summary = data["dfa"].get(key)
        if not summary:
            continue
        verdict = derive.threshold_verdict(summary)
        # Nothing was read at all - there is no value to show and no failure
        # to name. A reading that EXISTS but cannot be true (0,0 bpm) travels
        # on, flagged: it is shown and it pulls no median.
        if verdict["hr"] is None and verdict["power"] is None:
            continue
        if since and str(activity.get("start_date_local") or "")[:10] < since:
            continue
        series.append(
            {
                "date": str(activity.get("start_date_local") or "")[:10],
                "activity_id": key,
                "type": activity.get("type"),
                "hr": verdict["hr"],
                "power": verdict["power"],
                # The judgement is made HERE, once, and travels in the payload.
                # The frontend must not re-derive it - that is what let the
                # power curve keep a ride the heart rate curve had dropped.
                "hr_windows": verdict["hr_windows"],
                "power_windows": verdict["power_windows"],
                "hr_usable": verdict["hr_usable"],
                "power_usable": verdict["power_usable"],
                "usable": verdict["usable"],
                "failure": verdict["failure"],
                "reason": verdict["reason"],
                # The session's own numbers travel with the reading. Joining
                # them in the frontend against the activity list would work
                # only as far back as that list reaches (300 rows), and an
                # older reading would show empty columns without saying why -
                # a missing source dressed up as a missing value.
                "name": activity.get("name"),
                "moving_time": activity.get("moving_time"),
                "load": activity.get("icu_training_load"),
                "avg_hr": activity.get("average_heartrate"),
                # Die Gegengroesse zur Schwellenleistung, aus DENSELBEN Daten
                # und auf einem anderen Weg gerechnet. Fuer die Herzfrequenz
                # gab es sie laengst (avg_hr), fuer die Leistung nicht - und
                # damit liess sich eine gedrueckte Schwellenleistung nicht von
                # einer echten unterscheiden (§7, Randnotiz zur Migration).
                "avg_watts": activity.get("icu_average_watts"),
                "intensity": activity.get("icu_intensity"),
                "decoupling": activity.get("decoupling"),
            }
        )
    series.sort(key=lambda item: item["date"])
    return series


def archive_stats(data: dict[str, Any]) -> dict[str, Any]:
    """Return a short summary of what the archive currently holds."""
    days = sorted(data["wellness"])
    # The DFA readings have their OWN period, and it is shorter than the
    # archive's. Until 0.44.0 the header put "58 DFA" next to "489 Tage" and
    # thereby suggested the 58 were spread over those 489 - they all sit in
    # the last 105. Not a missing figure but a misleading neighbourhood
    # (docs/ausbau.md, "Historienbeginn"), so the period travels WITH its
    # count instead of borrowing the wellness one.
    dfa_days = sorted(
        str((data["activities"].get(key) or {}).get("start_date_local") or "")[:10]
        for key, summary in data["dfa"].items()
        if summary and (data["activities"].get(key) or {}).get("start_date_local")
    )
    act_days = sorted(
        str(activity.get("start_date_local") or "")[:10]
        for activity in data["activities"].values()
        if activity.get("start_date_local")
    )
    return {
        "wellness_days": len(days),
        "wellness_from": days[0] if days else None,
        "wellness_to": days[-1] if days else None,
        "activities": len(data["activities"]),
        "activities_from": act_days[0] if act_days else None,
        "activities_to": act_days[-1] if act_days else None,
        "unavailable": len(data["unavailable"]),
        "dfa_done": sum(1 for value in data["dfa"].values() if value),
        "dfa_from": dfa_days[0] if dfa_days else None,
        "dfa_to": dfa_days[-1] if dfa_days else None,
        "dfa_pending": len(pending_dfa(data)),
        "last_import": data.get("last_import"),
    }
