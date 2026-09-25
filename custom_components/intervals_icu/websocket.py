"""WebSocket API for the Intervals.icu panel.

The panel does not read entities - it asks these commands for whole series,
which keeps hundreds of days of history out of the state machine.
"""

from __future__ import annotations

import copy

from datetime import date, timedelta
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from . import analytics, blocks as blocks_lib, coach as coach_module, day_context as day_context_lib, derive, fatigue, fatigue_v2, importer, plan as plan_lib, ramp, ramp_tests as ramp_lib, reconcile as reconcile_lib, section_marks as marks_lib, steering as steering_lib, workouts as workout_lib
from .api import IntervalsError
from . import const
from .const import (
    BLOCK_CORRIDORS,
    BLOCK_MIN_FOR_SOURCE,
    STEERING_BAND_MIN_N,
    STEERING_BAND_WINDOW,
    STEERING_MIN_UNITS,
    STEERING_NEED,
    STEERING_STEP_W,
    STEERING_WINDOW,
    BLOCK_MIN_SECONDS,
    BLOCK_WARMUP_DISCARD_S,
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


def _same_index(left: Any, right: Any) -> bool:
    """Zwei Stromstellen als GLEICH lesen, ohne float-Vergleich auf Gleichheit."""
    try:
        return int(left) == int(right)
    except (TypeError, ValueError):
        return False


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
        websocket_section_marks,
        websocket_set_section_mark,
        websocket_confirm_section_marks,
        websocket_measure_section_marks,
        websocket_set_curve_source,
        websocket_set_fatigue_source,
        websocket_retry_dfa,
        websocket_fatigue_dry_run,
        websocket_set_block_source,
        websocket_set_steering_source,
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
    # WELCHE Familien ihre WATTVORGABE aus den Bloecken beziehen - aus der
    # Quellenkette, nicht aus einer Liste im Panel. Tempo misst ueber Bloecke,
    # seine Vorgabe kommt aber nie aus ihnen; eine Vergleichszeile „Vorgabe"
    # waere dort eine Blockzahl, die sich als Vorgabe ausgibt.
    result["feeds_watts"] = sorted(fam for fam, chain in workout_lib.SOURCE_CHAIN.items()
                                   if "blocks" in chain)
    # DIE STEUERUNG UND IHRE PARALLELANZEIGE. `steering` ist die neue Reihe
    # (Startwert, Schritte, Baender), `compare` stellt ALT neben NEU - beide
    # Zahlen aus gerechneten Reihen, keine im Frontend geschaetzt. Sie reisen
    # AUCH bei ausgeschaltetem Schalter mit, denn sonst koennte die Karte den
    # Vergleich nicht zeigen, ohne dass er schon wirkt.
    result["steering_on"] = steering_lib.steering_on(data)
    # DER STARTWERT JE ATHLET aus dem Archiv (0.66.3, Michael-Befund) - nicht
    # aus dem Code. Fehlt er, sagt `state` je Familie, dass er noch entsteht.
    anchors = steering_lib.anchors(data)
    result["steering"] = steering_lib.state(result, anchors)
    result["compare"] = steering_lib.compare(result, anchors)
    result["steering_anchors"] = anchors
    # Familien ohne Kachel (0.67.0): das Panel liest die Liste, statt sie zu kennen.
    result["hidden_families"] = list(blocks_lib.HIDDEN_FAMILIES)
    result["hidden_note"] = blocks_lib.HIDDEN_NOTE
    # Die Saetze zum Schalter kommen AUS DEM MODUL - eine Fassung im Frontend
    # waere die zweite Wahrheit aus 0.52.0, und die Versionsangabe darin stuende
    # dann an zwei Stellen.
    result["steering_words"] = {
        "on_note": steering_lib.SWITCH_ON_NOTE, "off_note": steering_lib.SWITCH_OFF_NOTE,
        "off_label": steering_lib.SWITCH_OFF_LABEL, "on_label": steering_lib.SWITCH_ON_LABEL,
        "go_label": steering_lib.SWITCH_GO_LABEL, "back_label": steering_lib.SWITCH_BACK_LABEL,
        # Die Saetze der KACHEL. Sie tragen Platzhalter ({watts}, {low} ...),
        # die das Frontend mit den Zahlen derselben Payload fuellt - so steht
        # der Satz an einer Stelle und die Zahl kommt trotzdem aus der Rechnung.
        "tile_ride": steering_lib.TILE_RIDE, "tile_inside": steering_lib.TILE_INSIDE,
        "tile_no_band": steering_lib.TILE_NO_BAND,
        "tile_band_means": steering_lib.TILE_BAND_MEANS,
        "tile_first_block": steering_lib.TILE_FIRST_BLOCK,
        "tile_off": steering_lib.TILE_OFF, "tile_no_target": steering_lib.TILE_NO_TARGET,
        "no_target_note": steering_lib.NO_TARGET_NOTE,
        "band_share": steering_lib.TILE_BAND_SHARE,
        "band_no_quote": steering_lib.TILE_BAND_NO_QUOTE,
        "more_origin": steering_lib.MORE_ORIGIN, "more_words": steering_lib.MORE_WORDS,
        "more_formula_label": steering_lib.MORE_FORMULA_LABEL,
        "more_formula_cap": steering_lib.MORE_FORMULA_CAP,
        "more_measured": steering_lib.MORE_MEASURED,
        "chip_alpha": steering_lib.CHIP_ALPHA, "chip_hr": steering_lib.CHIP_HR,
        "chip_first_block": steering_lib.CHIP_FIRST_BLOCK,
        "step_w": STEERING_STEP_W, "need": STEERING_NEED, "window": STEERING_WINDOW,
        "min_units": STEERING_MIN_UNITS, "band_min_n": STEERING_BAND_MIN_N,
        "band_window": STEERING_BAND_WINDOW,
    }
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
    # DIE ERMUEDUNGSRECHNUNG v2 reist als eigener Block mit, nicht als Ersatz.
    # So sieht die Kachel in EINEM Abruf beide Stellungen. Steht der Schalter
    # aus, ist `v2["on"]` false und die Kachel zeigt unveraendert das heutige
    # Verhalten - der Block kostet dann nur seine Zeilen.
    result["v2"] = fatigue_v2.curve(data, _today_iso())
    _stats = importer.archive_stats(data)
    result["v2"]["switch_note"] = fatigue_v2.switch_note(
        data, rides=_stats["dfa_done"] + _stats["dfa_pending"], batch=DFA_BATCH_SIZE)
    # DER BESTAND SAGT, OB ER VOLLSTAENDIG IST. Ein Stromabruf, der ausfaellt,
    # nimmt der Fahrt still ihre DFA-Zeile - und damit auch dem Anker, dem
    # DFA-Reiter und den Belastungsansichten, die von der Wattachse nichts
    # wissen. Solange hier etwas steht, darf keine Zahl der Karte so tun, als
    # waere der Bestand vollstaendig.
    result["incomplete"] = {"n": len(importer.failed_dfa(data)),
                            "rides": importer.failed_dfa(data)[:20]}
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
        vol.Required("type"): "intervals_icu/set_curve_source",
        vol.Required("from_marks"): bool,
        vol.Optional("athlete_id"): str,
    }
)
@websocket_api.async_response
async def websocket_set_curve_source(hass, connection, msg) -> None:
    """Den Kurvenschalter umlegen - und zurueck.

    DER RUECKWEG IST DER ZWECK. Umgelegt wird die QUELLE der Auswahl, nicht der
    Bestand: Marken, Anker und Messungen liegen im Archiv und werden hier nicht
    angefasst. Zurueckgestellt rechnet wieder die Namenserkennung, und zwar mit
    demselben Ergebnis wie vorher - ein Schalter ohne Rueckweg ist keiner.

    Gespeichert wird nur im AENDERUNGSFALL (J7, zweite Auflage).
    """
    coordinator = _pick(hass, msg.get("athlete_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "no Intervals.icu athlete loaded")
        return
    data = coordinator.archive.data
    box = data.get("settings")
    if not isinstance(box, dict):
        box = {}
        data["settings"] = box
    want = bool(msg["from_marks"])
    if bool(box.get(fatigue.CURVE_SWITCH)) != want:
        box[fatigue.CURVE_SWITCH] = want
        await coordinator.archive.async_save_now()
    connection.send_result(msg["id"], {"from_marks": fatigue.curve_from_marks(data)})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/set_fatigue_source",
        vol.Required("enabled"): bool,
        vol.Optional("athlete_id"): str,
    }
)
@websocket_api.async_response
async def websocket_set_fatigue_source(hass, connection, msg) -> None:
    """Den RECHENSCHALTER umlegen - und zurueck.

    ZWEI FRAGEN, ZWEI SCHALTER. Der Kurvenschalter waehlt die FAHRTEN ("meine
    Markierungen"), dieser waehlt die RECHNUNG: Watt ueber dasselbe
    120-s-Fenster wie alpha, Verlauf an der eigenen gehaltenen Last. Sie
    haengen nicht aneinander und duerfen es auch nicht - sonst liesse sich die
    eine Frage nicht mehr ohne die andere beantworten.

    ER KOSTET ETWAS, und das steht VOR dem Umlegen da: an bedeutet 58 Fahrten
    neu holen (in Schueben zu DFA_BATCH_SIZE) und 28 markierte Einheiten neu
    messen. Aus bedeutet: der Bestand wird nicht angefasst. Gespeichert - und
    geleert - wird deshalb nur im AENDERUNGSFALL (J7, zweite Auflage): ein
    Klick auf die Stellung, die schon steht, loest keine Neumessung aus.

    Das Leeren steht HIER und nicht im Versionszaehler. Der Zaehler gilt fuer
    alle und fuer immer; dieser Schalter gilt fuer diesen Athleten und nur,
    solange er umgelegt ist.
    """
    coordinator = _pick(hass, msg.get("athlete_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "no Intervals.icu athlete loaded")
        return
    data = coordinator.archive.data
    box = data.get("settings")
    if not isinstance(box, dict):
        box = {}
        data["settings"] = box
    want = bool(msg["enabled"])
    changed = bool(box.get(fatigue_v2.V2_SWITCH)) != want
    stats_before = importer.archive_stats(data)
    if changed:
        box[fatigue_v2.V2_SWITCH] = want
        data["dfa"] = {}
        await coordinator.archive.async_save_now()
    connection.send_result(msg["id"], {
        "enabled": fatigue_v2.v2_on(data),
        "changed": changed,
        "note": fatigue_v2.switch_note(
            data, rides=stats_before["dfa_done"] + stats_before["dfa_pending"],
            batch=DFA_BATCH_SIZE),
        "remeasure": {
            "rides": stats_before["dfa_done"] + stats_before["dfa_pending"],
            "batch": DFA_BATCH_SIZE,
        },
    })


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/fatigue_dry_run",
        vol.Optional("limit"): int,
        vol.Optional("athlete_id"): str,
    }
)
@websocket_api.async_response
async def websocket_fatigue_dry_run(hass, connection, msg) -> None:
    """DER TROCKENLAUF: beide Wattachsen an denselben Stroemen, LESEND.

    Er holt die Stroeme der Fahrten, die die Kurve heute traegt, rechnet
    jede Stunde in beiden Stellungen und gibt die Kachelzahlen beider Seiten
    zurueck. GESPEICHERT WIRD NICHTS: kein `async_save_now`, kein Schreiben in
    `data`. Die Rechnung laeuft auf Kopien (`fatigue_v2._shadow`).

    Damit sind die Zahlen der anderen Stellung sichtbar, BEVOR umgelegt wird -
    heute die einzige Luecke, die das Umlegen zu einem Sprung ins Dunkle
    macht. Er ueberlebt den Wegfall der Schalter, weil er zwei
    FENSTERBREITEN vergleicht und nicht zwei Schalterstellungen.
    """
    coordinator = _pick(hass, msg.get("athlete_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "no Intervals.icu athlete loaded")
        return
    data = coordinator.archive.data
    auswahl = [row.get("activity_id") for row in (fatigue.rides(data).get("used") or [])]
    limit = int(msg.get("limit") or 0)
    if limit > 0:
        auswahl = auswahl[-limit:]
    streams: dict[str, Any] = {}
    fehlt: list[dict[str, Any]] = []
    for key in auswahl:
        try:
            by_name = derive.streams_to_dict(
                await coordinator.client.async_get_streams(key, importer.DFA_STREAMS))
        except Exception as err:  # noqa: BLE001 - eine Fahrt ist kein Abbruch
            fehlt.append({"activity_id": key, "reason": str(err)[:200]})
            continue
        keep = None
        if fatigue.curve_from_marks(data):
            entry = marks_lib.entry_for(data, key)
            try:
                laps = derive.normalize_laps(
                    await coordinator.client.async_get_intervals(key)).get("laps") or []
            except Exception as err:  # noqa: BLE001
                fehlt.append({"activity_id": key, "reason": str(err)[:200]})
                continue
            keep, missing = marks_lib.mask_ranges(
                laps, marks_lib.marked(entry, "endurance"))
            if missing or not keep:
                fehlt.append({"activity_id": key, "reason": "Marken ohne Grenzen"})
                continue
        streams[key] = {"dfa_a1": by_name.get("dfa_a1"), "watts": by_name.get("watts"),
                        "heartrate": by_name.get("heartrate"), "keep": keep}
    result = fatigue_v2.dry_run(data, streams)
    result["asked"] = len(auswahl)
    result["missing"] = fehlt
    result["from_marks"] = fatigue.curve_from_marks(data)
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/retry_dfa",
        vol.Optional("athlete_id"): str,
    }
)
@websocket_api.async_response
async def websocket_retry_dfa(hass, connection, msg) -> None:
    """Die ausgefallenen Stromabrufe wieder freigeben.

    Kein Holen von hier aus: freigegeben wird nur die Marke "schon versucht",
    danach nimmt der naechste Abgleich die Fahrten wie jede andere mit. So
    bleibt der Holweg an EINER Stelle (dem Importweg) und wird nicht ein
    zweites Mal gebaut.

    Gespeichert wird nur im AENDERUNGSFALL (J7, zweite Auflage): ein Klick
    ohne Ausfaelle loest keinen Speichervorgang aus.
    """
    coordinator = _pick(hass, msg.get("athlete_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "no Intervals.icu athlete loaded")
        return
    data = coordinator.archive.data
    freed = importer.retry_failed_dfa(data)
    if freed:
        await coordinator.archive.async_save_now()
    connection.send_result(msg["id"], {"freed": freed})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/set_block_source",
        vol.Required("from_marks"): bool,
        vol.Optional("athlete_id"): str,
    }
)
@websocket_api.async_response
async def websocket_set_block_source(hass, connection, msg) -> None:
    """Den Blockschalter umlegen - und zurueck.

    Dieselbe Bauart wie der Kurvenschalter: umgelegt wird die QUELLE der
    Auswahl, nicht der Bestand. Marken und Messungen werden nicht angefasst,
    gespeichert wird nur im Aenderungsfall (J7, zweite Auflage).

    KEINE SPERRE. Bis 0.56.0 hing er an der Kurve (widerlegt: das Pulsfenster
    kommt nicht aus ihr), bis 0.57.0 an „noch nicht gebaut". Die einzige
    Kopplung beider Schalter sind Karten, die je eine Zahl aus beiden Ketten
    zeigen - und die Mischung entsteht schon mit dem Kurvenschalter allein.
    Eine Sperre haette sie nicht verhindert; die Karten nennen stattdessen je
    Zahl ihre Auswahl.
    """
    coordinator = _pick(hass, msg.get("athlete_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "no Intervals.icu athlete loaded")
        return
    data = coordinator.archive.data
    box = data.get("settings")
    if not isinstance(box, dict):
        box = {}
        data["settings"] = box
    want = bool(msg["from_marks"])
    if bool(box.get(blocks_lib.BLOCK_SWITCH)) != want:
        box[blocks_lib.BLOCK_SWITCH] = want
        await coordinator.archive.async_save_now()
    connection.send_result(msg["id"], {"from_marks": blocks_lib.blocks_from_marks(data)})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/set_steering_source",
        vol.Required("on"): bool,
        vol.Optional("athlete_id"): str,
    }
)
@websocket_api.async_response
async def websocket_set_steering_source(hass, connection, msg) -> None:
    """Die Steuerung v2 einschalten - und zurueck.

    Dritter Schalter derselben Bauart (Kurve, Bloecke, Steuerung): er steht im
    Archiv neben den anderen, gespeichert wird nur im AENDERUNGSFALL (J7,
    zweite Auflage), und ausgeschaltet bleibt das heutige Verhalten bitgenau.
    Umgelegt aendert er die QUELLE der Vorgabe, nicht den Bestand: Marken,
    Messungen und Bloecke werden nicht angefasst.
    """
    coordinator = _pick(hass, msg.get("athlete_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "no Intervals.icu athlete loaded")
        return
    data = coordinator.archive.data
    box = data.get("settings")
    if not isinstance(box, dict):
        box = {}
        data["settings"] = box
    want = bool(msg["on"])
    changed = False
    if bool(box.get(steering_lib.STEERING_SWITCH)) != want:
        box[steering_lib.STEERING_SWITCH] = want
        changed = True
    # BEIM EINSCHALTEN ENTSTEHT DER STARTWERT (0.66.3): aus den letzten
    # eigenen Einheiten je Familie, am heutigen Tag. Ein vorhandener bleibt.
    if want and steering_lib.ensure_anchors(
            data, blocks_lib.series(data, with_other=False), dt_util.now().date().isoformat()):
        changed = True
    if changed:
        await coordinator.archive.async_save_now()
    connection.send_result(msg["id"], {"on": steering_lib.steering_on(data),
                                       "anchors": steering_lib.anchors(data)})


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
        # `protocol` ist hier FORT (0.51.1). Die Beschreibung haengt an der
        # Einheit und kommt ueber die workouts-Payload als `standard` - das ist
        # die Stelle, die das Panel liest. Sie in ZWEI Payloads zu legen hiesse
        # zwei Wahrheiten fuer einen Text; dass eine davon niemand liest, ist
        # genau der Fall aus §7, neunzehnter Fall.
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
    ramp.measure geschickt. Ungeduennt, weil der Panel-Endpunkt bei 900
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
        # Rechenweg e1: die Segmentgrenzen kommen aus dem Protokoll, also
        # prueft measure() zuerst, ob die Fahrt es traegt. Der Grund ist je
        # Fall ein eigener Satz - ein Sammelsatz "kein auswertbarer Abfall"
        # waere bei einer Fahrt ohne Einrollen schlicht falsch.
        outcome = ramp.measure(by_name.get("dfa_a1"), by_name.get("watts"),
                               by_name.get("heartrate"))
        result = outcome.get("result")
        if result is None:
            # Kein Vorwurf, eine Auskunft.
            reason = str(outcome.get("reason") or "")

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
    # S1 (0.69.0): die Ampel rechnet mit derselben gewichteten Basislinie wie
    # der Trainer; die Vorbemerkung (`context_note`) kommt aus analytics.
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
    """Fetch one activity's laps live - und dabei die Drift der Zuordnung pruefen.

    Laps are not archived: they belong to a single opened activity and would
    multiply the archive for no gain. The API returns them on the activity
    itself when asked with intervals=true.

    DIESES LESE-KOMMANDO SCHREIBT, und das steht hier, statt sich zu
    verstecken. Der Grund ist, dass es die EINZIGE Stelle ist, an der die
    Runden einer Fahrt und das Archiv gleichzeitig vorliegen: `section_marks`
    fuehrt die Drift bewusst nicht mit (sie waere nur gegen live geholte Laps
    zu haben), und ein zweiter Abruf allein fuer die Pruefung waere derselbe
    Abruf noch einmal.

    Was geschrieben wird, ist eine LOESCHUNG mit Grund: driftet die Fahrt und
    traegt sie noch eine Messung, faellt die Messung - sie sass auf einem
    Ausschnitt, den es so nicht mehr gibt. Die MARKEN und der ANKER bleiben
    stehen; zurueck kommt der Athlet ueber "bestaetigen" oder neues Haken. Die
    Alternative waere, eine Zahl aus verschobenen Abschnitten weiterrechnen zu
    lassen - der stille Ausstieg (§7, vierte Fehlerklasse).

    GESPEICHERT WIRD NUR IM AENDERUNGSFALL. Ein Oeffnen ohne Drift, und ein
    Oeffnen einer gedrifteten Fahrt, deren Messung schon gefallen ist, loesen
    keinen Speichervorgang aus (J7, zweite Auflage).

    GELOESCHT WIRD NUR BEI FESTGESTELLTER DRIFT (seit 0.66.1, Karte F1.11 /
    R1 Haltung i). `drift` kennt drei Gruende, und nur zwei davon sind ein
    Befund: `lap_count` und `section_moved`. Der dritte, `laps_missing`, heisst
    "die Runden sind nicht da" - also NICHT PRUEFBAR, nicht verschoben. Bis
    0.66.0 fiel die Messung auch dann, mit dem Grund `moved`, den niemand
    festgestellt hatte; jeder Klick auf eine markierte Fahrt bei einer leeren
    Antwort von Intervals war eine Loeschung. Jetzt bleibt die Messung stehen,
    der Befund reist wie bisher mit (`marks_stale`), und benutzt wird sie
    trotzdem nicht: `usable_hours` gibt bei jedem Driftbefund None. Nicht
    rechnen ist nicht dasselbe wie loeschen.
    """
    coordinator = _pick(hass, msg.get("athlete_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "no Intervals.icu athlete loaded")
        return
    activity_id = str(msg["activity_id"])
    try:
        payload = await coordinator.client.async_get_intervals(activity_id)
    except Exception as err:  # noqa: BLE001 - surfaced to the panel as a message
        connection.send_error(msg["id"], "fetch_failed", str(err))
        return
    result = derive.normalize_laps(payload)

    data = coordinator.archive.data
    entry = marks_lib.entry_for(data, activity_id)
    stale = marks_lib.drift(entry, result.get("laps") or []) if entry else None
    if stale in marks_lib.DRIFT_FOUND and marks_lib.drop_hours(
            data, activity_id, marks_lib.STALE_REASON.get(stale, "")):
        await coordinator.archive.async_save_now()
    # Der Befund reist MIT den Runden, nicht in einer zweiten Payload: er ist
    # genau gegen sie erhoben, und zwei Wege zu einer Aussage waren 0.46.0.
    result["marks_stale"] = stale
    connection.send_result(msg["id"], result)


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
    lay = coach_module.layoff(data)
    # EINE Stelle fuer die Eingaenge, aus denen eine Einheit ihre Zahlen
    # bekommt - dieselbe fuer die Anzeige und fuer den Schreibweg nach
    # Intervals (siehe `_session_inputs`).
    inputs = _session_inputs(data, getattr(getattr(coordinator, "config_entry", None), "options", None))
    anchors = inputs["anchors"]
    ftp = inputs["ftp"]
    max_hr = inputs["max_hr"]

    # EINE LASTGRENZE (0.67.3, S5): die Karten lesen dieselbe Obergrenze wie der
    # Heute-Reiter - min(Budget, Zustandsdeckel), aus coach.load_ceiling.
    # NACH DEM TRAINING DIE GRENZE VON MORGEN (0.69.2, F2): eine Stelle, coach.session_ceiling.
    budget = coach_module.session_ceiling(data, st.get("state", "unknown"), ready)["ceiling"]
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
        curve=inputs["curve"],
        blocks=inputs["blocks"],
        steering=inputs["steering"],
        # Der Stufentest als naechste Stufe der Quellenkette (N2). Er wird
        # IMMER mitgegeben; ob er greift, entscheidet SOURCE_CHAIN je Familie -
        # und ohne markierten Test ist er None und aendert nichts.
        ramp=inputs["ramp"],
        ga=inputs["ga"],
    )
    # B2c: je Einheit ihr Nachweis - aus DENSELBEN Eingaengen, aus denen sie
    # gerechnet wurde, nicht aus einer zweiten Rechnung.
    for pick in picks:
        if isinstance(pick, dict):
            pick["explain"] = workout_lib.explain(pick, ftp, inputs["curve"], inputs["blocks"], inputs["ramp"])
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
        "ramp_test": inputs["ramp"],
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
    template = workout_lib.BY_KEY.get(str(msg["workout"]))
    if template is None:
        connection.send_error(msg["id"], "not_found", f"unknown workout {msg['workout']}")
        return
    # NIE DER ROHE KATALOGEINTRAG. Er traegt nur FTP-Prozent, und eine
    # Prozentangabe landet nur richtig, wenn die FTP in Intervals mit der
    # uebereinstimmt, aus der hier gerechnet wird - sonst ist jede Vorgabe der
    # Einheit still falsch. Geschrieben wird, was die Karte zeigt: dieselbe
    # Rechnung aus denselben Eingaengen.
    inputs = _session_inputs(coordinator.archive.data, getattr(getattr(coordinator, "config_entry", None), "options", None))
    entry = workout_lib.scaled(
        template, inputs["ftp"], inputs["anchors"].get("aerobic_hr"),
        max_hr=inputs["max_hr"], curve=inputs["curve"], blocks=inputs["blocks"],
        ramp=inputs["ramp"], steering=inputs["steering"], ga=inputs["ga"],
    )
    payload = workout_lib.to_event(
        entry, str(msg["date"]), str(msg.get("sport") or "Ride"),
        note="Vorgeschlagen von Home Assistant",
    )
    # DER WAECHTER AM SCHREIBWEG: nach Intervals gehen absolute Watt oder gar
    # nichts. Ohne FTP gibt es keine Wattzahlen - dann wird nicht geschrieben,
    # statt Prozente auf eine fremde FTP zu schicken.
    if "%" in str(payload.get("description") or ""):
        connection.send_error(
            msg["id"], "no_watts",
            "Nicht eingetragen: für diese Einheit liegen keine Wattzahlen vor "
            "(keine FTP und keine Messung). Prozentangaben würden in Intervals "
            "auf eine andere FTP gerechnet.")
        return
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



def _today_iso() -> str:
    """Der heutige Tag als ISO-Datum - robust gegen eine gestubbte Uhr im Pruefstand."""
    now = dt_util.now()
    return (now.date() if hasattr(now, "date") and callable(getattr(now, "date")) else now).isoformat()[:10]


def _ga_options(options: Any) -> tuple[float, float | None]:
    """Grenz- und Ziel-alpha aus den Einstellungen des Athleten (Regel 10)."""
    box = dict(options or {})
    try:
        limit = float(box.get(const.OPT_GA_ALPHA_LIMIT) or const.DEFAULT_GA_ALPHA_LIMIT)
    except (TypeError, ValueError):
        limit = const.DEFAULT_GA_ALPHA_LIMIT
    raw = box.get(const.OPT_GA_ALPHA_TARGET)
    try:
        target = float(raw) if raw not in (None, "", 0) else None
    except (TypeError, ValueError):
        target = None
    return limit, target


def _session_inputs(data: dict[str, Any], options: Any = None) -> dict[str, Any]:
    """Woraus eine Einheit ihre Watt und ihren Puls bekommt - EINE Stelle.

    Anzeige und Schreibweg nach Intervals lesen hier. Bis 0.56.0 las nur die
    Anzeige die Messung; `plan_workout` nahm den ROHEN Katalogeintrag, und
    `to_event` fiel auf dessen FTP-Prozent zurueck - die Karte zeigte 250 W,
    im Kalender landeten 106-110 % einer FTP von 200 (PROJEKTSTAND §7). Zwei
    Wege zu einer Zahl; hier ist es wieder einer.
    """
    anchors = coach_module.anchors(data)
    # The FTP travels ON THE ACTIVITIES as icu_ftp - that is where Intervals
    # puts it, and it is present on every ride. The earlier version looked in
    # sport_settings, which this archive does not carry, so the FTP came back
    # as None and every workout fell back to percentages.
    ftp = _latest_ftp(data)
    if ftp is None:
        for settings in (data.get("sport_settings") or {}).values():
            if isinstance(settings, dict) and settings.get("ftp"):
                ftp = float(settings["ftp"])
                break
    if ftp is None:
        ftp = anchors.get("ftp")
    series = blocks_lib.series(data)
    return {
        "anchors": anchors,
        "ftp": ftp,
        "max_hr": _max_hr(data),
        # Die Wattvorgabe der Grundlagen- und Langfahrt-Familien kommt aus der
        # eigenen Messung, nicht aus einem Profilfeld. EINE Quelle: dieselbe
        # Kurve, die die Kachel zeigt.
        "curve": fatigue.curve(data, aerobic_hr=anchors.get("aerobic_hr"),
                               aerobic_power=anchors.get("aerobic_power")),
        "blocks": series,
        "ramp": ramp_lib.latest(data),
        # DIE GA-EINHEIT LIEST DIE UMKEHRUNG (0.68.0): Ziel und Grenze je Stunde,
        # alpha-Werte aus den Einstellungen des Athleten.
        "ga": fatigue_v2.ga_targets(data, _today_iso(), *_ga_options(options)),
        # DIE STEUERUNG NUR BEI UMGELEGTEM SCHALTER. Steht er aus, ist der
        # Wert None - und `scaled()` betritt den neuen Zweig gar nicht erst,
        # statt ihn zu betreten und dort dasselbe zu tun wie vorher. Ein
        # Schalter, der die alte Rechnung nachbaut, ist kein Rueckweg.
        "steering": (steering_lib.state(series, steering_lib.anchors(data))
                     if steering_lib.steering_on(data) else None),
    }

def _latest_ftp(data: dict[str, Any]) -> float | None:
    """The most recent FTP Intervals recorded on an activity.

    VERGLICHEN WIRD DER ZEITPUNKT, nicht der Tag (0.67.2, F3.11): bis 0.67.1
    stand hier `day < best_day`, und bei zwei Aktivitaeten desselben Tages
    gewann die Archivreihenfolge. Jetzt gilt die spaetere; eine ohne FTP-Feld
    faellt durch, statt den Stand zu halten.
    """
    best_at, best = "", None
    for activity in (data.get("activities") or {}).values():
        at = str(activity.get("start_date_local") or "")
        if not at or at <= best_at:
            continue
        for field in ("icu_ftp", "icu_rolling_ftp"):
            value = activity.get(field)
            if value:
                best_at, best = at, float(value)
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
        lay = coach_module.layoff(data)
        rec = coach_module.recovery_offered(data)
        budget = coach_module.session_ceiling(
            data, st.get("state", "unknown"), analytics.readiness(data) or {})["ceiling"]
        # DIESELBEN EINGAENGE WIE DIE TRAINER-KARTE (0.67.2, F3.2): bis 0.67.1
        # baute dieser Handler seine Eingaenge von Hand - ohne `steering`. Bei
        # Steuerung an zeigte der Trainer-Reiter den Startwert, der Wochenplan
        # derselben Familie den Median der letzten Einheit. Eine Stelle.
        inputs = _session_inputs(data, getattr(getattr(coordinator, "config_entry", None), "options", None))
        anchors = inputs["anchors"]
        weeks[0]["sessions"] = workout_lib.rate_sessions(
            weeks[0].get("sessions") or [],
            st.get("state", "unknown"),
            budget=budget,
            recovery_offered=bool(rec.get("offered")),
            hard_days_last_7=coach_module._hard_days_recent(data, 7),
            layoff_days=lay.get("days"),
            infection=bool(st.get("infection_suspected")),
            ftp=inputs["ftp"],
            aerobic_hr=anchors.get("aerobic_hr"),
            max_hr=inputs["max_hr"],
            curve=inputs["curve"],
            blocks=inputs["blocks"],
            ramp=inputs["ramp"],
            steering=inputs["steering"],
            ga=inputs["ga"],
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
        vol.Required("type"): "intervals_icu/section_marks",
        vol.Optional("athlete_id"): str,
    }
)
@callback
def websocket_section_marks(hass, connection, msg) -> None:
    """Die Zuordnung Abschnitt -> Familie, wie sie im Archiv steht.

    ROH, UND ZWAR MIT ABSICHT: der Driftbefund steht hier NICHT dabei. Er ist
    nur gegen die Laps zu haben, und die sind nicht archiviert - sie kommen je
    Fahrt live ueber `intervals_icu/laps`. Ihn hier zu berechnen hiesse, fuer
    jede Fahrt der Liste einen Abruf zu machen; ihn aus den archivierten
    Bloecken zu SCHAETZEN hiesse, einen Stellvertreter zu zeigen, ohne zu
    sagen, dass es einer ist (§7, erster Fall).

    Geprueft wird die Drift deshalb dort, wo die Laps ohnehin vorliegen: im
    Aktivitaetsdetail und auf dem Messweg. Was die Aktivitaetenliste damit
    anfaengt, entscheidet P5.
    """
    if (coordinator := _require(hass, connection, msg)) is None:
        return
    data = coordinator.archive.data
    connection.send_result(msg["id"], {
        "marks": marks_lib.entries(data),
        # Die Familien reisen mit, damit das Panel keine zweite Liste fuehrt -
        # eine handgepflegte Kopie waere die Listen-Klasse aus §7.
        "families": list(marks_lib.FAMILIES),
        # Und die Saetze zu den Driftgruenden, aus derselben Quelle wie der
        # Grund selbst (fuenfte Bauregel).
        # WAS NEU ZU MESSEN IST, und warum. Der Sammelknopf ueber der Liste
        # zeigt die Zahl, bevor er etwas tut - "alle neu messen" waere eine
        # andere Zusage als die, die er einloest.
        "pending_remeasure": marks_lib.pending_remeasure(
            data, derive.watt_window(data)),
        "remeasure_batch": marks_lib.REMEASURE_BATCH,
        "remeasure_pause_ms": marks_lib.REMEASURE_PAUSE_MS,
        "stale_reason": marks_lib.STALE_REASON,
        "not_measured": marks_lib.NOT_MEASURED,
        # Was die Markierungen heute bewirken - ZWEI Saetze, weil die beiden
        # Lagen verschieden sind. Aus dem Modul, nicht aus dem Frontend.
        # Der Kurvensatz haengt an der SCHALTERSTELLUNG. In 0.56.0 stand er
        # bedingungslos da und sagte bei umgelegtem Schalter, die Kurve lese
        # die Marken nicht - das Gegenteil dessen, was sie tat (§7).
        # Der Blocksatz haengt am BLOCKSCHALTER (seit 0.66.3, F1.14): "an
        # deinen Marken vorbei" sagt, ob die Blockreihe die Marken liest, und
        # das entscheidet `blocks_from_marks` in blocks.series - nicht die
        # Steuerung. Von 0.60.0 bis 0.66.2 hing er an `steering_v2`: bei
        # Blockschalter an und Steuerung aus stand er neben einer Reihe, die
        # laengst auf den Marken rechnete. Davor stand er bedingungslos da.
        # Dieselbe Klasse wie der Kurvensatz in 0.56.0 (§7).
        "not_active": {**({} if blocks_lib.blocks_from_marks(data)
                          else {"blocks": marks_lib.NOT_ACTIVE_BLOCKS}),
                       **({} if fatigue.curve_from_marks(data)
                          else {"curve": marks_lib.NOT_ACTIVE_CURVE})},
        "no_value": marks_lib.NO_VALUE,
        # Was der Regelkreis spaeter sieht, BEVOR er es tut: je Familie die
        # Bloecke im und ausserhalb ihres Korridors.
        "corridor_state": marks_lib.corridor_state(
            data.get("section_marks") or {}, BLOCK_CORRIDORS),
        "outside_note": marks_lib.OUTSIDE_NOTE,
        # Der ZWEITE Satz, fuer den, der schon einmal gemessen hat. Beide aus
        # derselben Quelle wie der Zustand selbst (fuenfte Bauregel) - eine
        # Fassung im Frontend waere die zweite Wahrheit aus 0.52.0.
        "remeasure": marks_lib.REMEASURE,
        # WARUM eine Messung fort ist, je Grund ein Satz. Der Eintrag traegt
        # den Grund als Feld (`lost`); ohne ihn ist der Grund unbekannt, und
        # die Kachel sagt das, statt „Auswahl geaendert" zu erfinden.
        "lost_text": marks_lib.LOST_TEXT,
        # Die Zahlen fuer die Erklaerung je Familie reisen MIT: eine Schwelle,
        # die das Panel als Literal fuehrt, ist eine zweite Wahrheit (fuenfte
        # Bauregel), und der Dublettenwaechter meldet sie zu Recht.
        "corridors": BLOCK_CORRIDORS,
        "discard_s": BLOCK_WARMUP_DISCARD_S,
        "min_seconds": BLOCK_MIN_SECONDS,
        "min_for_source": BLOCK_MIN_FOR_SOURCE,
        "v": marks_lib.MEASURE_VERSION,
    })


async def _laps_for(coordinator: Any, activity_id: str) -> list[dict[str, Any]]:
    """Die Abschnitte einer Fahrt, LIVE. Wirft IntervalsError weiter."""
    payload = await coordinator.client.async_get_intervals(activity_id)
    return derive.normalize_laps(payload).get("laps") or []


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/set_section_mark",
        vol.Required("activity_id"): str,
        vol.Required("family"): str,
        vol.Required("start_index"): int,
        vol.Required("mark"): bool,
        vol.Optional("athlete_id"): str,
    }
)
@websocket_api.async_response
async def websocket_set_section_mark(hass, connection, msg) -> None:
    """Eine Marke setzen oder zuruecknehmen. Nur lokal, an Intervals geht nichts.

    DER SCHLUESSEL IST `start_index`, und er wird gegen die LIVE geholten Laps
    geprueft - nicht gegen die archivierten Bloecke. Die beiden Listen sind
    nicht deckungsgleich (P3a), und die Bloecke sind es, die Luecken haben.

    DER FEHLERPFAD, AUSDRUECKLICH: scheitert der Lap-Abruf beim Setzen, wird
    NICHTS geschrieben. Das ist der Unterschied zu `set_ramp_test`, wo die
    Markierung auch ohne Messung steht: dort faellt die MESSUNG aus, und die
    Aussage "diese Fahrt war ein Stufentest" ist trotzdem vollstaendig. Hier
    fiele das aus, was die Aussage ueberhaupt erst BESTIMMT - ohne Laps gibt es
    weder einen geprueften Schluessel noch einen Anker. Eine Marke ohne Anker
    ist eine, deren Drift nie auffallen kann; sie gaelte fuer immer als
    sitzend. Das waere der stille Ausstieg, eine Ebene tiefer.

    DIE RUECKNAHME BRAUCHT KEINE LAPS und laeuft deshalb auch dann, wenn die
    Schnittstelle gerade nicht antwortet. Sonst waere eine falsch gesetzte
    Marke genau dann nicht loszuwerden, wenn ohnehin etwas klemmt.
    """
    coordinator = _pick(hass, msg.get("athlete_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "no Intervals.icu athlete loaded")
        return
    data = coordinator.archive.data
    activity_id = str(msg["activity_id"])

    # GESPEICHERT WIRD NUR IM AENDERUNGSFALL (J7): seit 0.66.2 gibt `_write`
    # bei einer schon gesetzten Marke den alten Eintrag zurueck (F1.8b), und
    # ein No-op darf keinen Speichervorgang ausloesen.
    before = copy.deepcopy(marks_lib.entry_for(data, activity_id))

    if not msg["mark"]:
        try:
            entry = marks_lib.unset_mark(
                data, activity_id, str(msg["family"]), int(msg["start_index"]))
        except ValueError as err:
            connection.send_error(msg["id"], "invalid_format", str(err))
            return
        if entry != before:
            await coordinator.archive.async_save_now()
        connection.send_result(msg["id"], {"activity_id": activity_id, "entry": entry})
        return

    activity = (data.get("activities") or {}).get(activity_id)
    if not isinstance(activity, dict):
        connection.send_error(msg["id"], "not_found", f"unknown activity {activity_id}")
        return
    day = str(activity.get("start_date_local") or "")[:10]
    try:
        laps = await _laps_for(coordinator, activity_id)
    except IntervalsError as err:
        connection.send_error(
            msg["id"], "fetch_failed",
            f"Die Abschnitte dieser Fahrt sind nicht abrufbar ({err}) — ohne sie "
            f"wird nichts markiert, weil die Markierung sonst ohne Anker stünde.")
        return
    except Exception as err:  # noqa: BLE001 - dem Panel als Satz zeigen
        connection.send_error(msg["id"], "fetch_failed", str(err))
        return
    if not laps:
        connection.send_error(
            msg["id"], "no_laps",
            "Intervals liefert für diese Fahrt keine Abschnitte — sie ist dort "
            "zu unterteilen, damit es hier etwas zu markieren gibt.")
        return

    try:
        entry = marks_lib.set_mark(
            data, activity_id, day, str(msg["family"]), int(msg["start_index"]),
            laps, set_at=dt_util.now().date().isoformat())
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    if entry != before:
        await coordinator.archive.async_save_now()
    connection.send_result(msg["id"], {
        "activity_id": activity_id,
        "entry": entry,
        "laps": len(laps),
    })


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/measure_section_marks",
        vol.Required("activity_id"): str,
        vol.Optional("athlete_id"): str,
    }
)
@websocket_api.async_response
async def websocket_measure_section_marks(hass, connection, msg) -> None:
    """"Uebernehmen und messen": der Stundenverlauf des MARKIERTEN Bereichs.

    ER MISST NUR, WAS MARKIERT IST. Er hakt nichts an, schlaegt nichts vor,
    ergaenzt nichts - die Auswahl trifft der Athlet, hier wird gerechnet.

    ZWEI ABRUFE, und der zweite ist nicht optional. `set_ramp_test` kommt mit
    den Stroemen aus, weil es die ganze Fahrt auswertet. Maskieren heisst
    Stromstellen ausschliessen, und die Grenzen dafuer sind `start_index` UND
    `end_index` der Laps - die stehen NICHT im Strom, und der Anker haelt sie
    auch nicht (er fuehrt die DAUER, und Dauer ist Bewegungszeit auf einer
    Stromachse: genau der Versatz aus §7). Also derselbe zweite Abruf wie in
    `importer.async_import_dfa`, samt eigenem Fehlerpfad: Stroeme da, Laps
    nicht.

    DIE STROEME LIVE UND UNGEDUENNT, aus denselben Kanaelen wie der Import
    (`importer.DFA_STREAMS`). Das ist kein Detail: die maskierte Stundenliste
    steht spaeter neben der Ganzfahrt-Liste aus dem Archiv, und zwei
    verschieden erhobene Groessen unter einer Ueberschrift waren 0.49.2.

    DIE DRIFT WIRD GEGEN DIE FRISCH GEHOLTEN LAPS GEPRUEFT, bevor gerechnet
    wird. Ohne das misst dieser Weg auf Abschnitten, die in Intervals
    inzwischen verschoben wurden - dieselben `start_index` gibt es vielleicht
    noch, der Ausschnitt ist ein anderer, und das ERGEBNIS SAEHE SAUBER AUS.
    Hier liegen die Laps ohnehin vor; es gibt keinen Grund, nicht zu pruefen.

    ZWEI ARTEN VON FEHLSCHLAG, und sie werden verschieden behandelt:

      * TRANSPORT und DRIFT (Abruf gescheitert, keine Abschnitte, verschoben,
        ein markierter Abschnitt ist fort) -> `send_error`, es wird NICHTS
        geschrieben. Ein Netzfehler, der als Satz ins Archiv wandert, steht
        dort beim naechsten Oeffnen noch, obwohl nie erneut versucht wurde -
        das ist die Klasse aus 0.53.1, ein gespeicherter Anzeigetext, der
        veraltet.
      * SACHBEFUND ueber die Fahrt (die markierten Sekunden tragen kein
        auswertbares alpha) -> `set_measurement` mit Grund. Der ist bei jedem
        Versuch wieder derselbe, gehoert also ins Archiv - dieselbe Bauart wie
        der Grund aus ramp.measure beim Stufentest.
    """
    coordinator = _pick(hass, msg.get("athlete_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "no Intervals.icu athlete loaded")
        return
    data = coordinator.archive.data
    activity_id = str(msg["activity_id"])

    entry = marks_lib.entry_for(data, activity_id)
    if entry is None or not marks_lib.marked(entry):
        connection.send_error(
            msg["id"], "not_found",
            "Für diese Fahrt ist kein Abschnitt markiert — gemessen wird nur, "
            "was du angehakt hast.")
        return

    try:
        streams = await coordinator.client.async_get_streams(
            activity_id, importer.DFA_STREAMS)
    except Exception as err:  # noqa: BLE001 - dem Panel als Satz zeigen
        connection.send_error(
            msg["id"], "fetch_failed",
            f"Die Ströme dieser Fahrt sind nicht abrufbar ({err}) — ohne sie "
            f"ist nichts zu messen. Die Markierung bleibt stehen.")
        return

    try:
        laps = await _laps_for(coordinator, activity_id)
    except Exception as err:  # noqa: BLE001 - EIGENER Fehlerpfad: Stroeme da, Laps nicht
        connection.send_error(
            msg["id"], "laps_failed",
            f"Die Ströme sind da, die Abschnitte nicht ({err}) — ohne ihre "
            f"Grenzen ist nicht zu bestimmen, welche Sekunden gemessen werden "
            f"sollen. Es wurde nichts geändert.")
        return
    if not laps:
        connection.send_error(
            msg["id"], "no_laps",
            "Intervals liefert für diese Fahrt keine Abschnitte mehr — ohne "
            "ihre Grenzen ist der markierte Bereich nicht zu schneiden.")
        return

    stale = marks_lib.drift(entry, laps)
    if stale:
        # GEMESSEN WIRD NICHT AUF VERSCHOBENEN ABSCHNITTEN. Und die Messung,
        # die noch dastand, faellt hier genauso wie beim Oeffnen.
        if marks_lib.drop_hours(data, activity_id,
                                marks_lib.STALE_REASON.get(stale, "")):
            await coordinator.archive.async_save_now()
        connection.send_error(msg["id"], "marks_stale",
                              marks_lib.STALE_REASON.get(stale, ""))
        return

    # DIE MASKE IST FAMILIENREIN. Ohne den Parameter nahm sie alle Marken
    # einer Fahrt quer ueber die Familien - auf einer Fahrt mit VO2max- UND
    # Grundlagen-Marken legte die Gerade dann zwei getrennte Punktwolken
    # zusammen (Einrollen: wenig Watt, hohes alpha; Intervalle: viel Watt,
    # niedriges alpha) und las bei 0,75 einen Zustand ab, den niemand
    # gefahren ist. Das ist der Fit-durch-zwei-Wolken aus Paket M, dort schon
    # einmal behoben - zurueckgekommen ueber einen neuen Weg, weil die
    # Voraussetzung des alten Fixes (die Messung sieht nur EINE Sorte
    # Abschnitt) von der Maskierung aufgehoben wurde.
    #
    # Und die Familie entscheidet auch das INSTRUMENT: hier wird die Kurve
    # gerechnet, und die Kurve ist die Quelle der GRUNDLAGE. Fuer die
    # Blockfamilien gibt es den Messweg noch nicht; lieber keine Zahl als
    # eine, die niemand angefordert hat.
    by_name = derive.streams_to_dict(streams)
    # DIE BLOCKZEILEN WERDEN FRISCH GERECHNET, nicht im Archiv nachgeschlagen.
    # Die Archivbloecke haengen an der Rundenstruktur vom IMPORTzeitpunkt, die
    # Marken an der heutigen. An der Fahrt vom 13.09.2026 fielen beide
    # auseinander (Archiv sieben Runden, live fuenf) - OHNE Drift, denn die
    # Driftprobe vergleicht Marken gegen Runden, nicht Archiv gegen Runden.
    # Marken, live geholte Runden und Stroeme liegen im SELBEN Indexraum; die
    # Archivbloecke nicht (§7).
    block_rows = derive.dfa_blocks(by_name.get("dfa_a1"), by_name.get("watts"),
                                   by_name.get("heartrate"), laps)

    results: dict[str, Any] = {}
    stamp = dt_util.now().date().isoformat()
    for family in marks_lib.FAMILIES:
        if not marks_lib.marked(entry, family):
            continue
        hours = blocks = None
        reason = ""
        if family == "endurance":
            ranges, missing = marks_lib.mask_ranges(laps, marks_lib.marked(entry, family))
            if missing or not ranges:
                reason = ("Zu mindestens einem markierten Abschnitt gibt es in dieser "
                          "Fahrt keine Grenzen mehr — die Zuordnung ist zu bestätigen "
                          "oder neu zu setzen.")
            else:
                # DIE WATTACHSE HAENGT AM RECHENSCHALTER, hier wie im
                # Importweg. Bis 0.63.0 stand hier kein Fenster: stand der
                # Kurvenschalter auf "meine Markierungen" - so steht er -,
                # las die Kurve ungefensterte Werte, und der Rechenschalter
                # hatte gar keine Wirkung. Zwei Wahrheiten unter einem Dach.
                hours = derive.dfa_hours(by_name.get("dfa_a1"), by_name.get("watts"),
                                         by_name.get("heartrate"), keep=ranges,
                                         watt_window_s=derive.watt_window(data)) or None
                if hours is None:
                    reason = ("Diese Fahrt führt keinen auswertbaren DFA-a1-Strom — an "
                              "den markierten Abschnitten ist nichts abzulesen.")
        else:
            rows = marks_lib.marked_blocks(entry, block_rows, family)
            fehlt = [i for i in marks_lib.marked(entry, family)
                     if not any(_same_index(row.get("start_index"), i) for row in rows)]
            usable = [row for row in rows
                      if row.get("watts") is not None and row.get("alpha") is not None]
            blocks = usable or None
            if fehlt:
                # SACHBEFUND, kein Transportfehler: der Abschnitt ist kuerzer
                # als BLOCK_MIN_SECONDS oder traegt keine gueltigen Werte.
                reason = (f"Zu {len(fehlt)} markierten Abschnitten gibt es keinen "
                          f"Blockwert — zu kurz oder ohne verwertbare Daten.")
            elif not usable:
                reason = "In den markierten Abschnitten stehen keine Wattwerte."
        try:
            marks_lib.set_measurement(data, activity_id, family=family, hours=hours,
                                      blocks=blocks, reason=reason, measured_at=stamp,
                                      window_s=derive.watt_window(data))
        except ValueError as err:
            connection.send_error(msg["id"], "invalid_format", str(err))
            return
        results[family] = {"hours": hours, "blocks": blocks, "reason": reason}

    # Mit der dritten gemessenen Einheit einer Familie kann der Startwert
    # entstehen (0.66.3) - hier, weil hier ohnehin geschrieben wird, nicht in
    # einem Leseweg (F1.11-Klasse).
    if steering_lib.steering_on(data):
        steering_lib.ensure_anchors(data, blocks_lib.series(data, with_other=False),
                                    dt_util.now().date().isoformat())
    await coordinator.archive.async_save_now()
    connection.send_result(msg["id"], {
        "activity_id": activity_id,
        "entry": marks_lib.entry_for(data, activity_id),
        # JE FAMILIE ein Ergebnis mit eigenem Grund - keine Sammelmeldung.
        "families": results,
    })


@websocket_api.websocket_command(
    {
        vol.Required("type"): "intervals_icu/confirm_section_marks",
        vol.Required("activity_id"): str,
        vol.Optional("athlete_id"): str,
    }
)
@websocket_api.async_response
async def websocket_confirm_section_marks(hass, connection, msg) -> None:
    """Eine verschobene Fahrt ausdruecklich bestaetigen - ein Knopf, kein Automat.

    Die Marken bleiben, der Anker wird neu genommen, die Messung faellt: sie
    sass auf dem alten Ausschnitt. Passt eine Marke nicht mehr auf die neuen
    Abschnitte, wird NICHT bestaetigt, sondern neu gehakt - eine Bestaetigung,
    die auf nichts zeigt, ist schlimmer als keine.
    """
    coordinator = _pick(hass, msg.get("athlete_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "no Intervals.icu athlete loaded")
        return
    data = coordinator.archive.data
    activity_id = str(msg["activity_id"])
    try:
        laps = await _laps_for(coordinator, activity_id)
    except Exception as err:  # noqa: BLE001 - dem Panel als Satz zeigen
        connection.send_error(msg["id"], "fetch_failed", str(err))
        return
    try:
        entry = marks_lib.reanchor(data, activity_id, laps)
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    await coordinator.archive.async_save_now()
    connection.send_result(msg["id"], {"activity_id": activity_id, "entry": entry})

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
