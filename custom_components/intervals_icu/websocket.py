"""WebSocket API for the Intervals.icu panel.

The panel does not read entities - it asks these commands for whole series,
which keeps hundreds of days of history out of the state machine.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import analytics, coach as coach_module, derive, importer, plan as plan_lib, workouts as workout_lib
from .api import IntervalsError
from .const import DOMAIN

# Streams offered to the panel's activity detail view. Fetched live on
# demand and thinned before they cross the socket - they are never stored.
DETAIL_STREAMS: tuple[str, ...] = (
    "time",
    "watts",
    "heartrate",
    "cadence",
    "velocity_smooth",
    "altitude",
    "dfa_a1",
)

# A chart never needs more points than it has pixels. Buckets are averaged,
# so a thinned power line still carries the right mean level.
MAX_STREAM_POINTS = 900


def _archives(hass: HomeAssistant) -> dict[str, Any]:
    """Return every loaded athlete archive, keyed by athlete id."""
    result: dict[str, Any] = {}
    for entry in hass.config_entries.async_entries(DOMAIN):
        coordinator = getattr(entry, "runtime_data", None)
        if coordinator is not None and getattr(coordinator, "archive", None) is not None:
            result[str(entry.unique_id)] = coordinator
    return result


def _pick(hass: HomeAssistant, athlete_id: str | None) -> Any | None:
    """Return the requested athlete's coordinator, or the only one there is."""
    found = _archives(hass)
    if athlete_id:
        return found.get(athlete_id)
    return next(iter(found.values()), None)


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register all panel commands."""
    for handler in (
        websocket_athletes,
        websocket_pmc,
        websocket_activities,
        websocket_activity,
        websocket_streams,
        websocket_laps,
        websocket_coach,
        websocket_signals,
        websocket_workouts,
        websocket_plan_workout,
        websocket_night,
        websocket_context,
        websocket_today,
        websocket_goal,
        websocket_set_goal,
        websocket_thresholds,
        websocket_calendar,
        websocket_status,
        websocket_load,
        websocket_readiness,
        websocket_days,
    ):
        websocket_api.async_register_command(hass, handler)


@websocket_api.websocket_command({vol.Required("type"): "intervals_icu/athletes"})
@callback
def websocket_athletes(hass, connection, msg) -> None:
    """List the configured athletes."""
    connection.send_result(
        msg["id"],
        [
            {"athlete_id": athlete_id, "name": coordinator.config_entry.title}
            for athlete_id, coordinator in _archives(hass).items()
        ],
    )


def _require(hass, connection, msg):
    """Return the coordinator or send an error."""
    coordinator = _pick(hass, msg.get("athlete_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "no Intervals.icu athlete loaded")
        return None
    return coordinator


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/pmc",
        vol.Optional("athlete_id"): str,
    }
)
@callback
def websocket_pmc(hass, connection, msg) -> None:
    """Return the fitness / fatigue / form series."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    connection.send_result(msg["id"], importer.pmc_series(coordinator.archive.data))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/activities",
        vol.Optional("athlete_id"): str,
        vol.Optional("limit"): vol.All(int, vol.Range(min=1, max=1000)),
        vol.Optional("oldest"): str,
    }
)
@callback
def websocket_activities(hass, connection, msg) -> None:
    """Return activity summaries, newest first."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    connection.send_result(
        msg["id"],
        importer.activity_list(
            coordinator.archive.data,
            limit=msg.get("limit", 50),
            oldest=msg.get("oldest"),
        ),
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/activity",
        vol.Required("activity_id"): str,
        vol.Optional("athlete_id"): str,
    }
)
@callback
def websocket_activity(hass, connection, msg) -> None:
    """Return one activity including its DFA summary."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    data = coordinator.archive.data
    activity = data["activities"].get(msg["activity_id"])
    if activity is None:
        connection.send_error(msg["id"], "not_found", "unknown activity")
        return
    merged = dict(activity)
    merged["dfa"] = data["dfa"].get(msg["activity_id"]) or None
    connection.send_result(msg["id"], merged)


def _thin_channel(values: list[Any], step: int, first: bool = False) -> list[Any]:
    """Reduce a stream to one value per bucket.

    Numeric buckets are averaged so levels survive the thinning; ``first``
    keeps the first raw value instead, which is right for the time stream.
    A bucket without a single numeric value stays None, so gaps in the
    recording remain visible as gaps in the chart.
    """
    out: list[Any] = []
    for start in range(0, len(values), step):
        chunk = values[start : start + step]
        if first:
            out.append(chunk[0] if chunk else None)
            continue
        numbers = [float(v) for v in chunk if isinstance(v, (int, float))]
        out.append(round(sum(numbers) / len(numbers), 2) if numbers else None)
    return out


def thin_streams(by_name: dict[str, list[Any]]) -> dict[str, Any]:
    """Thin all requested streams to at most MAX_STREAM_POINTS points."""
    length = max((len(v) for v in by_name.values()), default=0)
    if not length:
        return {"points": 0, "sample_secs": 1, "channels": {}}

    step = max(1, -(-length // MAX_STREAM_POINTS))  # ceil division
    channels: dict[str, list[Any]] = {}
    for name, values in by_name.items():
        if name not in DETAIL_STREAMS or not values:
            continue
        thinned = _thin_channel(values, step, first=(name == "time"))
        # Channels that carry no data at all are dropped so the panel does
        # not draw an empty axis for them.
        if any(v is not None for v in thinned):
            channels[name] = thinned

    return {
        "points": len(next(iter(channels.values()), [])),
        "sample_secs": step,
        "channels": channels,
    }


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/streams",
        vol.Required("activity_id"): str,
        vol.Optional("athlete_id"): str,
    }
)
@websocket_api.async_response
async def websocket_streams(hass, connection, msg) -> None:
    """Fetch one activity's streams live and return them thinned.

    Streams are the one payload deliberately not kept in the archive - a
    year of per-second data has no business on disk. The detail view is the
    only consumer, so a live fetch per opened activity is the cheap path.
    """
    coordinator = _pick(hass, msg.get("athlete_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "no Intervals.icu athlete loaded")
        return
    try:
        streams = await coordinator.client.async_get_streams(
            msg["activity_id"], DETAIL_STREAMS
        )
    except IntervalsError as err:
        connection.send_error(msg["id"], "fetch_failed", str(err))
        return
    connection.send_result(msg["id"], thin_streams(derive.streams_to_dict(streams)))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/thresholds",
        vol.Optional("athlete_id"): str,
    }
)
@callback
def websocket_thresholds(hass, connection, msg) -> None:
    """Return the aerobic threshold read off each activity."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    connection.send_result(msg["id"], importer.threshold_series(coordinator.archive.data))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/calendar",
        vol.Optional("athlete_id"): str,
    }
)
@callback
def websocket_calendar(hass, connection, msg) -> None:
    """Return the planned workouts."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    planned = coordinator.data.get("planned") or []
    connection.send_result(
        msg["id"],
        [{**item, "start": str(item["start"]), "end": str(item["end"])} for item in planned],
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/status",
        vol.Optional("athlete_id"): str,
    }
)
@callback
def websocket_status(hass, connection, msg) -> None:
    """Return what the archive holds and whether an import is running."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    stats = importer.archive_stats(coordinator.archive.data)
    stats["importing"] = bool(getattr(coordinator, "import_running", False))
    stats["athlete"] = coordinator.config_entry.title
    connection.send_result(msg["id"], stats)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/load",
        vol.Optional("athlete_id"): str,
    }
)
@callback
def websocket_load(hass, connection, msg) -> None:
    """Return the whole training load picture: weeks, ACWR, intensity, HRV."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    connection.send_result(msg["id"], analytics.summary(coordinator.archive.data))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/readiness",
        vol.Optional("athlete_id"): str,
    }
)
@callback
def websocket_readiness(hass, connection, msg) -> None:
    """Return the readiness traffic light and today's load budget."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    connection.send_result(msg["id"], analytics.readiness(coordinator.archive.data))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/days",
        vol.Optional("athlete_id"): str,
        vol.Optional("weeks"): vol.All(int, vol.Range(min=1, max=52)),
    }
)
@callback
def websocket_days(hass, connection, msg) -> None:
    """Return the calendar grid: a record per day plus weekly summaries."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    connection.send_result(
        msg["id"],
        analytics.calendar_days(
            coordinator.archive.data,
            (coordinator.data or {}).get("events"),
            weeks=msg.get("weeks", 12),
        ),
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/laps",
        vol.Required("activity_id"): str,
        vol.Optional("athlete_id"): str,
    }
)
@websocket_api.async_response
async def websocket_laps(hass, connection, msg) -> None:
    """Fetch one activity's laps live.

    Laps are not archived: they belong to a single opened activity and would
    multiply the archive for no gain. The API returns them on the activity
    itself when asked with intervals=true.
    """
    coordinator = _pick(hass, msg.get("athlete_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "no Intervals.icu athlete loaded")
        return
    try:
        payload = await coordinator.client.async_get_intervals(str(msg["activity_id"]))
    except Exception as err:  # noqa: BLE001 - surfaced to the panel as a message
        connection.send_error(msg["id"], "fetch_failed", str(err))
        return
    connection.send_result(msg["id"], derive.normalize_laps(payload))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/coach",
        vol.Optional("athlete_id"): str,
    }
)
@callback
def websocket_coach(hass, connection, msg) -> None:
    """Return the trainer view: state, next session, week ahead, evidence."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    data = coordinator.archive.data
    ready = analytics.readiness(data)
    connection.send_result(
        msg["id"], coach_module.coach(data, (ready or {}).get("budget"))
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/signals",
        vol.Optional("athlete_id"): str,
        vol.Optional("days"): vol.All(int, vol.Range(min=28, max=400)),
    }
)
@callback
def websocket_signals(hass, connection, msg) -> None:
    """Return every signal per day, normalised, with state bands and sessions."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    connection.send_result(
        msg["id"],
        coach_module.signals(coordinator.archive.data, int(msg.get("days") or 180)),
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/workouts",
        vol.Optional("athlete_id"): str,
    }
)
@callback
def websocket_workouts(hass, connection, msg) -> None:
    """Return concrete sessions for today, with the athlete's own numbers."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    data = coordinator.archive.data
    ready = analytics.readiness(data) or {}
    rec = coach_module.recommend(data, ready.get("budget"))
    anchors = rec.get("anchors") or {}

    ftp = None
    for settings in (data.get("sport_settings") or {}).values():
        if isinstance(settings, dict) and settings.get("ftp"):
            ftp = float(settings["ftp"])
            break
    if ftp is None:
        ftp = anchors.get("ftp")

    budget = (ready.get("budget") or {}).get("recommended")
    picks = workout_lib.suggest(
        (rec.get("state") or {}).get("state", "unknown"),
        ftp=ftp,
        aerobic_hr=anchors.get("aerobic_hr"),
        budget=budget,
        hard_days_last_7=coach_module._hard_days_recent(data, 7),
        layoff_days=(rec.get("layoff") or {}).get("days"),
    )
    connection.send_result(msg["id"], {
        "ftp": ftp,
        "aerobic_hr": anchors.get("aerobic_hr"),
        "budget": budget,
        "state": (rec.get("state") or {}).get("state"),
        "workouts": picks,
    })


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/plan_workout",
        vol.Required("workout"): str,
        vol.Required("date"): str,
        vol.Optional("sport"): str,
        vol.Optional("athlete_id"): str,
    }
)
@websocket_api.async_response
async def websocket_plan_workout(hass, connection, msg) -> None:
    """Write one planned workout to the athlete's Intervals.icu calendar.

    The only call in this integration that changes anything outside Home
    Assistant. It runs on an explicit click, writes exactly one event, and is
    never retried automatically - see api.async_create_event.
    """
    coordinator = _pick(hass, msg.get("athlete_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "no Intervals.icu athlete loaded")
        return
    entry = workout_lib.BY_KEY.get(str(msg["workout"]))
    if entry is None:
        connection.send_error(msg["id"], "not_found", f"unknown workout {msg['workout']}")
        return
    payload = workout_lib.to_event(
        entry, str(msg["date"]), str(msg.get("sport") or "Ride"),
        note="Vorgeschlagen von Home Assistant",
    )
    try:
        created = await coordinator.client.async_create_event(payload)
    except Exception as err:  # noqa: BLE001 - surfaced to the panel as a message
        connection.send_error(msg["id"], "write_failed", str(err))
        return
    connection.send_result(msg["id"], {
        "ok": True,
        "name": entry["title"],
        "date": str(msg["date"]),
        "id": (created or {}).get("id") if isinstance(created, dict) else None,
    })


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/night",
        vol.Required("activity_id"): str,
        vol.Optional("athlete_id"): str,
    }
)
@callback
def websocket_night(hass, connection, msg) -> None:
    """What the night after one session showed, against this athlete's norm."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    connection.send_result(
        msg["id"],
        coach_module.night_after(coordinator.archive.data, str(msg["activity_id"])),
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/context",
        vol.Required("activity_id"): str,
        vol.Optional("athlete_id"): str,
    }
)
@callback
def websocket_context(hass, connection, msg) -> None:
    """Where this session's numbers sit among the athlete's comparable ones."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    connection.send_result(
        msg["id"],
        coach_module.session_context(coordinator.archive.data, str(msg["activity_id"])),
    )


def _state_for_plan(data: dict[str, Any]) -> dict[str, Any]:
    """What the archive knows that the plan should take into account."""
    longest = 0.0
    for activity in (data.get("activities") or {}).values():
        hours = (activity.get("moving_time") or 0) / 3600
        longest = max(longest, hours)
    wellness = data.get("wellness") or {}
    recent = [wellness[d] for d in sorted(wellness)[-28:]]
    loads = [float(row.get("load") or 0) for row in recent]
    return {
        "longest_ride_hours": round(longest, 1),
        "weekly_load": round(sum(loads) / 4) if loads else None,
    }


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/goal",
        vol.Optional("athlete_id"): str,
    }
)
@callback
def websocket_goal(hass, connection, msg) -> None:
    """Return the stored goal profile, the plan it produces, and the options."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    data = coordinator.archive.data
    profile = data.get("goal") or plan_lib.default_goal()
    state = _state_for_plan(data)
    connection.send_result(msg["id"], {
        "profile": profile,
        "state": state,
        "goals": {key: {k: v for k, v in entry.items() if k != "mix"}
                  for key, entry in plan_lib.GOALS.items()},
        "plan": plan_lib.plan(profile, state),
    })


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/set_goal",
        vol.Required("profile"): dict,
        vol.Optional("athlete_id"): str,
    }
)
@websocket_api.async_response
async def websocket_set_goal(hass, connection, msg) -> None:
    """Store the goal profile in the archive.

    A local write only - nothing here is sent to intervals.icu.
    """
    coordinator = _pick(hass, msg.get("athlete_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "no Intervals.icu athlete loaded")
        return
    profile = plan_lib.default_goal()
    incoming = msg["profile"] or {}
    for key in profile:
        if key in incoming:
            profile[key] = incoming[key]
    coordinator.archive.data["goal"] = profile
    await coordinator.archive.async_save_now()
    state = _state_for_plan(coordinator.archive.data)
    connection.send_result(msg["id"], {
        "profile": profile, "state": state,
        "plan": plan_lib.plan(profile, state),
    })


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/today",
        vol.Optional("athlete_id"): str,
    }
)
@callback
def websocket_today(hass, connection, msg) -> None:
    """Everything that bears on what is possible today - and nothing beyond."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    data = coordinator.archive.data
    ready = analytics.readiness(data) or {}
    connection.send_result(msg["id"], coach_module.today(data, ready.get("budget")))
