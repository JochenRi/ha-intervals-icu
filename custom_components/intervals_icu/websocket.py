"""WebSocket API for the Intervals.icu panel.

The panel does not read entities - it asks these commands for whole series,
which keeps hundreds of days of history out of the state machine.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from . import analytics, blocks as blocks_lib, coach as coach_module, day_context as day_context_lib, derive, fatigue, importer, plan as plan_lib, ramp, ramp_tests as ramp_lib, reconcile as reconcile_lib, workouts as workout_lib
from .api import IntervalsError
from .const import (
    DECOUPLING_GOOD,
    DFA_BATCH_SIZE,
    DOMAIN,
    THRESHOLD_MIN_HR,
    THRESHOLD_MIN_POWER,
    THRESHOLD_MIN_WINDOWS,
)

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
    # GEPRUEFT UND LEER (0.47.2). Angefordert wurde der Kanal, um zu messen, ob
    # RR-Intervalle darin stehen - dann laege die DFA-Fensterbreite bei uns
    # statt bei Intervals. Die API liefert ihn NICHT, obwohl `stream_types` ihn
    # auffuehrt. Die Zeile bleibt trotzdem stehen: ein leerer Kanal wird
    # ohnehin verworfen, sie kostet nichts, und wuerde sie entfernt, prueft das
    # in zwei Jahren jemand ein zweites Mal. Fuegt Intervals ihn spaeter hinzu,
    # faellt es auf (docs/ausbau.md M5).
    "hrv",
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
        websocket_fatigue,
        websocket_blocks,
        websocket_calendar,
        websocket_status,
        websocket_load,
        websocket_readiness,
        websocket_days,
        websocket_day_context,
        websocket_set_day_context,
        websocket_set_ramp_test,
        websocket_ramp_tests,
        websocket_reconcile,
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
    summary = data["dfa"].get(msg["activity_id"]) or None
    if summary:
        # The judgement travels WITH the summary, computed once in the backend.
        # The detail card used to compare `threshold_samples < 5` itself - the
        # fourth of five copies of a rule that has one home (derive).
        summary = {**summary, "threshold": derive.threshold_verdict(summary)}
    merged["dfa"] = summary
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
        vol.Optional("since"): str,
    }
)
@callback
def websocket_thresholds(hass, connection, msg) -> None:
    """Return the aerobic threshold read off each activity.

    The panel filters the window in the client - 57 readings arrive in one
    go anyway. `since` exists so that at 500 readings this is a parameter,
    not a rebuild.
    """
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    connection.send_result(
        msg["id"],
        importer.threshold_series(coordinator.archive.data, since=msg.get("since")),
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/blocks",
        vol.Optional("athlete_id"): str,
    }
)
@callback
def websocket_blocks(hass, connection, msg) -> None:
    """Ein Wert je Block, ueber die Zeit (docs/ausbau.md Paket M)."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    data = coordinator.archive.data
    result = blocks_lib.series(data)
    stats = importer.archive_stats(data)
    result["progress"] = {
        "done": stats["dfa_done"], "pending": stats["dfa_pending"],
        "total": stats["dfa_done"] + stats["dfa_pending"],
        "batch": DFA_BATCH_SIZE,
        "importing": bool(getattr(coordinator, "import_running", False)),
    }
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/fatigue",
        vol.Optional("athlete_id"): str,
    }
)
@callback
def websocket_fatigue(hass, connection, msg) -> None:
    """Die Ermuedungskurve der aeroben Schwelle (docs/ausbau.md Paket L)."""
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    data = coordinator.archive.data
    # Der ausgeruhte HF-Anker kommt aus dem Trainer - EINE Quelle, nicht eine
    # zweite Rechnung hier (L1b haengt an genau der Zahl, die das Panel nennt).
    anchors = coach_module.anchors(data)
    result = fatigue.curve(data, aerobic_hr=anchors.get("aerobic_hr"),
                           aerobic_power=anchors.get("aerobic_power"))
    # Nach einem Algorithmus-Bump ist das Archiv leer, bis die Stroeme neu
    # geholt sind - in Baendern von DFA_BATCH_SIZE je Sync. Der Fortschritt
    # reist mit, damit die Kachel "rechnet noch, x von y" sagen kann statt
    # leer zu bleiben: ein leerer Platz sieht aus wie ein Defekt (§7, der
    # stille Ausstieg).
    stats = importer.archive_stats(data)
    result["progress"] = {
        "done": stats["dfa_done"],
        "pending": stats["dfa_pending"],
        "total": stats["dfa_done"] + stats["dfa_pending"],
        "batch": DFA_BATCH_SIZE,
        "importing": bool(getattr(coordinator, "import_running", False)),
    }
    connection.send_result(msg["id"], result)


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
    # The decoupling mark is drawn in views that load neither the coach nor the
    # load payload (activity list, DFA table). Status is fetched at boot, so it
    # is the one carrier that is always there. Still ONE definition - const.py;
    # several carriers of the same value are fine, a second value is not.
    stats["decoupling_good"] = DECOUPLING_GOOD
    # Dieselbe Traegerlogik fuer die Plausibilitaetsgrenzen: der DFA-Reiter, die
    # Aktivitaetsliste und die Detailkarte muessen sagen koennen, WARUM ein Wert
    # als Ausfall gilt - und die Zahl dazu darf nicht im Frontend stehen.
    # `basis` reist mit, weil beide Zahlen SETZUNGEN sind und keine Befunde:
    # gemessen wurde an EINEM Bestand (§7), und fuer andere Koerper - sehr
    # trainiert, jung, betablockiert - kann die Grenze zu hoch liegen.
    stats["threshold_limits"] = {
        "min_hr": THRESHOLD_MIN_HR,
        "min_power": THRESHOLD_MIN_POWER,
        "min_windows": THRESHOLD_MIN_WINDOWS,
        "basis": (
            "Setzung, nicht Befund. Die Grenzen trennen AUSFAELLE von Messungen "
            "und sind an einem einzigen Bestand geprueft: dort liegt der "
            "niedrigste echte Schwellenwert bei 90 bpm (Gehen) und der hoechste "
            "Ruhepuls bei 66 - dazwischen liegt die Grenze. Das Fenster ist "
            "schmal, und fuer einen anderen Koerper kann es sich verschieben."
        ),
    }
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
        vol.Required("type"): "intervals_icu/day_context",
        vol.Optional("athlete_id"): str,
    }
)
@callback
def websocket_day_context(hass, connection, msg) -> None:
    """Return the labelled days, the vocabulary and the source-block texts.

    NOT named intervals_icu/context - that name has carried the coach's
    session context since 0.31.0. One payload feeds chips, markers and the
    source block, so vocabulary and rules cannot drift from day_context.py.
    """
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    data = coordinator.archive.data
    connection.send_result(msg["id"], {
        "days": data.get("day_context") or {},
        "tags": day_context_lib.TAGS,
        "valid_weights": list(day_context_lib.VALID_WEIGHTS),
        "min_weight_sum": day_context_lib.MIN_WEIGHT_SUM,
        "sources": day_context_lib.SOURCES,
    })


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/set_day_context",
        vol.Required("date"): str,
        vol.Required("tag"): vol.Any(str, None),
        vol.Optional("weight"): vol.Any(float, int, None),
        vol.Optional("note"): str,
        vol.Optional("athlete_id"): str,
    }
)
@websocket_api.async_response
async def websocket_set_day_context(hass, connection, msg) -> None:
    """Store or remove one day's context label.

    A local write only - nothing here is sent to intervals.icu. tag null
    REMOVES the entry (a retraction, distinct from setting "normal", which
    is a statement); the removed day computes as if never labelled.
    """
    coordinator = _pick(hass, msg.get("athlete_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "no Intervals.icu athlete loaded")
        return
    data = coordinator.archive.data
    day = msg["date"]
    if msg["tag"] is None:
        removed = day_context_lib.remove_entry(data, day)
        if removed:
            await coordinator.archive.async_save_now()
        connection.send_result(msg["id"], {"date": day, "entry": None,
                                           "removed": removed})
        return
    try:
        entry = day_context_lib.set_entry(
            data, day, msg["tag"], msg.get("weight"),
            msg.get("note", ""), set_at=dt_util.now().date().isoformat())
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    await coordinator.archive.async_save_now()
    connection.send_result(msg["id"], {"date": day, "entry": entry})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/ramp_tests",
        vol.Optional("athlete_id"): str,
    }
)
@callback
def websocket_ramp_tests(hass, connection, msg) -> None:
    """Markierte Stufentests und ihre gemessenen Zahlen.

    `latest` ist der juengste Test, der ueberhaupt etwas gemessen hat - ein
    markierter Test ohne Messung verdraengt keinen gueltigen aelteren, bleibt
    aber in `tests` sichtbar, samt Grund.
    """
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    data = coordinator.archive.data
    connection.send_result(msg["id"], {
        "tests": ramp_lib.entries(data),
        "latest": ramp_lib.latest(data),
        "sources": ramp_lib.SOURCES,
        "protocol": workout_lib.RAMP_TEST_STANDARD,
    })


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/set_ramp_test",
        vol.Required("activity_id"): str,
        vol.Required("mark"): bool,
        vol.Optional("note"): str,
        vol.Optional("athlete_id"): str,
    }
)
@websocket_api.async_response
async def websocket_set_ramp_test(hass, connection, msg) -> None:
    """Eine Fahrt als Stufentest markieren, oder die Markierung zuruecknehmen.

    Nur ein lokaler Schreibvorgang - an intervals.icu geht nichts. `mark`
    false NIMMT die Markierung ZURUECK, und danach rechnet die Fahrt genau wie
    eine, die nie markiert war.

    Markieren MISST: die Stroeme werden live und UNGEDUENNT geholt und durch
    ramp.evaluate geschickt. Ungeduennt, weil der Panel-Endpunkt bei 900
    Punkten deckelt - das sind 7 bis 18 Sekunden je Probe, und eine Gerade
    durch den Abfall staende dann auf rund hundert Punkten statt auf
    tausenden (J1, dieselbe Begruendung wie beim abgeloesten Protokoll).

    Die Markierung steht auch, wenn die Messung ausfaellt - dann aber MIT
    GRUND. Eine Markierung mit still leeren Zahlen waere der Ausstieg aus
    0.42.1.
    """
    coordinator = _pick(hass, msg.get("athlete_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "no Intervals.icu athlete loaded")
        return
    data = coordinator.archive.data
    activity_id = str(msg["activity_id"])

    if not msg["mark"]:
        removed = ramp_lib.remove_entry(data, activity_id)
        if removed:
            await coordinator.archive.async_save_now()
        connection.send_result(msg["id"], {"activity_id": activity_id, "entry": None,
                                           "removed": removed})
        return

    activity = (data.get("activities") or {}).get(activity_id)
    if not isinstance(activity, dict):
        connection.send_error(msg["id"], "not_found", f"unknown activity {activity_id}")
        return
    day = str(activity.get("start_date_local") or "")[:10]

    result = None
    reason = ""
    try:
        streams = await coordinator.client.async_get_streams(
            activity_id, ("time", "watts", "heartrate", "dfa_a1"))
    except IntervalsError as err:
        reason = f"Ströme nicht abrufbar: {err}"
    else:
        by_name = derive.streams_to_dict(streams)
        result = ramp.evaluate(by_name.get("dfa_a1"), by_name.get("watts"),
                               by_name.get("heartrate"))
        if result is None:
            # Kein Vorwurf, eine Auskunft: die Fahrt traegt keinen
            # auswertbaren Abfall. Das ist auch der Fall, wenn die Uhr kein
            # alpha aufgezeichnet hat.
            reason = ("Kein auswertbarer Abfall von DFA a1 in dieser Fahrt — "
                      "entweder fehlt der alpha-Strom, oder die Rampe hat "
                      "keinen zusammenhängenden Abfall ergeben.")

    try:
        entry = ramp_lib.set_entry(
            data, activity_id, day, result=result, reason=reason,
            note=msg.get("note", ""), set_at=dt_util.now().date().isoformat())
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    await coordinator.archive.async_save_now()
    connection.send_result(msg["id"], {
        "activity_id": activity_id,
        "entry": entry,
        "reason": reason,
        "latest": ramp_lib.latest(data),
    })


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
    data = coordinator.archive.data
    payload = analytics.readiness(data)
    # The lamp computes UNWEIGHTED by design (level 3: analytics is
    # context-free). When labelled days sit in its window the number can
    # diverge from the weighted trainer baseline - that gets SAID, not
    # silently accepted, and properly fixed by a per-condition baseline (B4).
    labelled = [d for d in sorted(data.get("day_context") or {})
                if d >= (dt_util.now().date() - timedelta(days=66)).isoformat()]
    if payload and labelled:
        payload["context_note"] = (
            f"ungewichtet gerechnet — {len(labelled)} etikettierte "
            f"{'Tag' if len(labelled) == 1 else 'Tage'} im Fenster; die "
            "gewichtete Basislinie steht beim Trainerurteil, sauber trennt "
            "das erst eine Basislinie je Bedingung (B4)")
    connection.send_result(msg["id"], payload)


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
    connection.send_result(msg["id"], coach_module.coach(coordinator.archive.data))


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
    st = coach_module.state(data)
    anchors = coach_module.anchors(data)
    lay = coach_module.layoff(data)

    # The FTP travels ON THE ACTIVITIES as icu_ftp - that is where Intervals
    # puts it, and it is present on every ride. The earlier version looked in
    # sport_settings, which this archive does not carry, so the FTP came back
    # as None and every workout fell back to percentages. Percentages are the
    # honest fallback when nothing is known; they are the wrong answer when the
    # number was sitting in the data all along.
    ftp = _latest_ftp(data)
    if ftp is None:
        for settings in (data.get("sport_settings") or {}).values():
            if isinstance(settings, dict) and settings.get("ftp"):
                ftp = float(settings["ftp"])
                break
    if ftp is None:
        ftp = anchors.get("ftp")

    max_hr = _max_hr(data)

    budget = (ready.get("budget") or {}).get("recommended")
    # FOUND WHILE BUILDING K: this handler never passed `recovery_offered`, so
    # `stage()` defaulted it to False and the session list for TODAY could not
    # reach the stimulus grade at all - while the week view (which does pass
    # it) could. One rule, two different inputs, and the grade that Paket I
    # added was invisible on the tab it was added for. See PROJEKTSTAND 7.
    recovery = bool(coach_module.recovery_offered(data).get("offered"))
    picks = workout_lib.suggest(
        st.get("state", "unknown"),
        ftp=ftp,
        aerobic_hr=anchors.get("aerobic_hr"),
        max_hr=max_hr,
        infection=bool(st.get("infection_suspected")),
        budget=budget,
        hard_days_last_7=coach_module._hard_days_recent(data, 7),
        layoff_days=lay.get("days"),
        goal=(data.get("goal") or {}).get("goal"),
        recovery_offered=recovery,
        # Die Wattvorgabe der Grundlagen- und Langfahrt-Familien kommt aus der
        # eigenen Messung, nicht aus einem Profilfeld. EINE Quelle: dieselbe
        # Kurve, die die Kachel zeigt.
        curve=fatigue.curve(data, aerobic_hr=anchors.get("aerobic_hr"),
                            aerobic_power=anchors.get("aerobic_power")),
        blocks=blocks_lib.series(data),
    )
    connection.send_result(msg["id"], {
        "ftp": ftp,
        "aerobic_hr": anchors.get("aerobic_hr"),
        "budget": budget,
        "state": st.get("state"),
        # Watts come from the FTP, heart rate from the DFA anchor. When the
        # two contradict each other the rider must see it - the base-ride
        # watts would sit ON their measured threshold (see workouts.anchor_conflict).
        "conflict": workout_lib.anchor_conflict(ftp, anchors.get("aerobic_power")),
        "workouts": picks,
        # Der Stufentest braucht KEINEN eigenen Zweig mehr: er ist ein
        # gewoehnlicher Katalogeintrag mit fester Form und steht damit in
        # `workouts` wie alles andere, mit Urteil und Stufe. Der abgeloeste
        # zweite Termin hatte ohne gemessenen ersten keine Form - daher der
        # Sonderweg, der hier entfaellt.
        "ramp_test": ramp_lib.latest(data),
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


def _latest_ftp(data: dict[str, Any]) -> float | None:
    """The most recent FTP Intervals recorded on an activity."""
    best_day, best = "", None
    for activity in (data.get("activities") or {}).values():
        day = str(activity.get("start_date_local") or "")[:10]
        if not day or day < best_day:
            continue
        for field in ("icu_ftp", "icu_rolling_ftp"):
            value = activity.get(field)
            if value:
                best_day, best = day, float(value)
                break
    return best


def _max_hr(data: dict[str, Any]) -> float | None:
    """The athlete's measured maximum heart rate, once - both handlers need it."""
    for settings in (data.get("sport_settings") or {}).values():
        if isinstance(settings, dict):
            found = settings.get("max_heartrate") or settings.get("max_hr")
            if found:
                return float(found)
    return None


def _state_for_plan(data: dict[str, Any]) -> dict[str, Any]:
    """What the archive knows that the plan should take into account."""
    longest = 0.0
    for activity in (data.get("activities") or {}).values():
        hours = (activity.get("moving_time") or 0) / 3600
        longest = max(longest, hours)
    # The weekly load comes from the ACTIVITIES. wellness.load is not filled
    # on every account - reading it there reported "weekly_load: 0" on an
    # archive holding 239 sessions. Same error class as the FTP (0.28.1) and
    # the seven-day load (0.29.0): right number, wrong place.
    wellness = data.get("wellness") or {}
    days = sorted(wellness)
    load_cutoff = days[-28] if len(days) >= 28 else (days[0] if days else "")
    loads = [
        float(activity.get("icu_training_load") or 0)
        for activity in (data.get("activities") or {}).values()
        if str(activity.get("start_date_local") or "")[:10] >= load_cutoff
    ]

    # The hours the athlete actually rides, taken from the last eight weeks -
    # so the form does not have to ask for a number the archive already holds.
    cutoff = (date.today() - timedelta(days=56)).isoformat()
    seconds = 0
    days_ridden = set()
    for activity in (data.get("activities") or {}).values():
        day = str(activity.get("start_date_local") or "")[:10]
        if day >= cutoff:
            seconds += activity.get("moving_time") or 0
            days_ridden.add(day)
    return {
        "longest_ride_hours": round(longest, 1),
        "weekly_load": round(sum(loads) / 4) if loads else None,  # 4 weeks
        "typical_hours": round(seconds / 3600 / 8, 1) if seconds else None,
        "typical_days": round(len(days_ridden) / 8, 1) if days_ridden else None,
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
    built = plan_lib.plan(profile, state)

    # The grade for the CURRENT week only. Everything it needs already exists:
    # the state rule in coach, the budget in analytics, the grade in workouts.
    # This handler wires them together, it does not restate any of them - and
    # weeks two to eight get no grade at all, because a budget solved from the
    # last six days says nothing about a session five weeks out (I3/I4).
    weeks = built.get("weeks") or []
    if built.get("ready") and weeks:
        st = coach_module.state(data)
        anchors = coach_module.anchors(data)
        lay = coach_module.layoff(data)
        rec = coach_module.recovery_offered(data)
        budget = ((analytics.readiness(data) or {}).get("budget") or {}).get("recommended")
        weeks[0]["sessions"] = workout_lib.rate_sessions(
            weeks[0].get("sessions") or [],
            st.get("state", "unknown"),
            budget=budget,
            recovery_offered=bool(rec.get("offered")),
            hard_days_last_7=coach_module._hard_days_recent(data, 7),
            layoff_days=lay.get("days"),
            infection=bool(st.get("infection_suspected")),
            ftp=_latest_ftp(data) or anchors.get("ftp"),
            aerobic_hr=anchors.get("aerobic_hr"),
            max_hr=_max_hr(data),
            curve=fatigue.curve(data, aerobic_hr=anchors.get("aerobic_hr"),
                                aerobic_power=anchors.get("aerobic_power")),
            blocks=blocks_lib.series(data),
        )
        weeks[0]["rated"] = True
        weeks[0]["done"] = analytics.week_done(data, weeks[0]["start"])
        built["assessment"] = {
            "state": st.get("state"),
            "state_label": st.get("label"),
            "budget": budget,
            "recovery": rec,
            "hard_days_last_7": coach_module._hard_days_recent(data, 7),
        }
    built["no_verdict_note"] = workout_lib.NO_VERDICT_NOTE
    built["stages"] = workout_lib.STAGES
    built["choice"] = plan_lib.CHOICE_EVIDENCE

    connection.send_result(msg["id"], {
        "profile": profile,
        "state": state,
        "goals": {key: {k: v for k, v in entry.items() if k != "mix"}
                  for key, entry in plan_lib.GOALS.items()},
        "plan": built,
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
    # The calendar anchor for the 3:1 cycle. A plan counted "from today"
    # keeps the recovery week forever four weeks away - so the start Monday
    # is persisted with the profile. It survives edits to the same goal and
    # resets only when the goal itself changes.
    if not plan_lib.has_anchor(profile):
        prior = coordinator.archive.data.get("goal") or {}
        if prior.get("goal") == profile.get("goal") and plan_lib.has_anchor(prior):
            profile["plan_start"] = prior["plan_start"]
        else:
            profile["plan_start"] = plan_lib.anchor_stamp()
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


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/reconcile",
        # Absent: report only, nothing is touched. Present: carry out exactly
        # the ids that were shown and confirmed - see below.
        vol.Optional("confirm"): [str],
        vol.Optional("athlete_id"): str,
    }
)
@websocket_api.async_response
async def websocket_reconcile(hass, connection, msg) -> None:
    """Compare the archive against Intervals, and on confirmation trim it.

    Reads only. Nothing goes to intervals.icu, and there is no way to remove
    one chosen activity: the removal follows from the comparison and has one
    outcome, parity. The locks live in reconcile.plan()/apply(); what is added
    here is the state of the system around them.
    """
    coordinator = _pick(hass, msg.get("athlete_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "no Intervals.icu athlete loaded")
        return

    # An import in flight is writing the very dict we would compare against,
    # and would write its own stale copy back afterwards.
    if getattr(coordinator, "import_running", False):
        connection.send_error(msg["id"], "busy", "Der Import läuft gerade - bitte danach abgleichen.")
        return

    data = coordinator.archive.data
    if importer.should_full_import(data):
        connection.send_error(
            msg["id"], "not_ready",
            "Die Historie wurde noch nie vollständig geholt - das Archiv ist kein Maßstab.")
        return

    oldest = coordinator.history_start()
    newest = date.today()
    try:
        rows = await coordinator.client.async_get_activities(
            oldest, newest, fields=reconcile_lib.RECONCILE_FIELDS)
    except Exception as err:  # noqa: BLE001 - lock 1: report, touch nothing
        connection.send_error(msg["id"], "fetch_failed", str(err))
        return

    try:
        report = reconcile_lib.plan(data, rows, oldest, newest)
    except ValueError as err:
        connection.send_error(msg["id"], "bad_response", str(err))
        return

    # The calendar is not the archive. Planned sessions come from the events
    # endpoint on every coordinator refresh, so a session deleted in Intervals
    # falls out by itself - but nothing here triggered that refresh, and a
    # parity result changes no state, so the panel kept showing the stale list
    # until the next scheduled poll. async_refresh() and NOT
    # async_request_refresh(): the debouncer would skip exactly this case.
    # A refresh is a read. The boundary from D3 is untouched - there is still
    # no "delete one session" action and still nothing goes to Intervals.
    await coordinator.async_refresh()

    confirmed = msg.get("confirm")
    if confirmed is None:
        connection.send_result(msg["id"], dict(report, applied=False))
        return

    # The archive may have moved between the dialog and the click, and the
    # second fetch is a second answer. Only the intersection of what was shown
    # and what is still missing may go - anything else would carry out
    # something other than what was confirmed.
    allowed = set(report["removable"])
    wanted = {str(key) for key in confirmed}
    if wanted - allowed:
        connection.send_result(msg["id"], dict(
            report, applied=False, stale=True,
            message="Der Befund hat sich seit der Anzeige geändert - es wurde nichts entfernt."))
        return

    removed = reconcile_lib.apply(data, wanted)
    if reconcile_lib.changed(removed):
        await coordinator.archive.async_save_now()
        coordinator.async_update_listeners()
    connection.send_result(msg["id"], dict(
        report, applied=True, stale=False, removed=removed,
        stats=importer.archive_stats(data)))
