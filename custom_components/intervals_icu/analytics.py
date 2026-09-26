"""Training analytics derived from the local archive.

Every metric here is a published one, and each carries its origin in the
docstring. Home Assistant is not imported, so the maths can be replayed
against recorded payloads in tests.

Sources, short:

* Form / TSB zones - Joe Friel. Intervals.icu applies the same numbers to
  relative form (form as a percentage of fitness) by default; its author calls
  the zones a rule of thumb rather than science.
* Monotony and strain - Foster: weekly mean load divided by its standard
  deviation, strain = weekly load x monotony.
* Acute:chronic workload ratio - Gabbett/Blanch, corridor 0.8-1.3, elevated
  above 1.5. Heavily criticised since (mathematical coupling, correlational
  evidence, a randomised trial finding no benefit), so it is reported as an
  indicator, never as a verdict.
* Intensity distribution - Seiler's three-zone model; elite endurance athletes
  came out near 75/8/17 percent.
* HRV guidance - 7-day rolling mean of ln(rMSSD) against the smallest
  worthwhile change, mean +/- 0.5 standard deviations of the baseline period.
* Decoupling - Joe Friel: at or below about 5 percent on steady aerobic rides
  means the aerobic base is sound.
* DFA alpha-1 - Rogers and Gronwald 2021a/b (treadmill): 0.75 marks the aerobic threshold (VT1),
  0.5 the anaerobic threshold (VT2).
"""

from __future__ import annotations

import logging
import math
from datetime import date, datetime, timedelta
from statistics import mean, pstdev
from typing import Any

try:  # inside the package (Home Assistant)
    from . import baseline, derive, section_marks, workouts
    from .const import DECOUPLING_GOOD
except ImportError:  # standalone (test suite loads this file directly)
    import baseline
    import derive
    import section_marks
    import workouts
    from const import DECOUPLING_GOOD

_LOGGER = logging.getLogger(__name__)

# --- Form / TSB zones ---------------------------------------------------------
# Upper bound (exclusive) -> name. Same numbers for absolute form and form %.
FORM_ZONES: tuple[tuple[float | None, str], ...] = (
    (-30.0, "high_risk"),
    (-5.0, "optimal"),
    (10.0, "grey"),
    (20.0, "fresh"),
    (None, "transition"),
)

# --- thresholds carried from the literature -----------------------------------
ACWR_LOW = 0.8
ACWR_HIGH = 1.3
ACWR_RISK = 1.5
MONOTONY_WATCH = 2.0
# DECOUPLING_GOOD comes from const.py - one definition for the whole house.
POLARIZED_LOW = 75.0
POLARIZED_MIDDLE = 8.0


def form_zone(form: float | None) -> str | None:
    """Return the Friel zone a form value falls into."""
    if form is None:
        return None
    for upper, name in FORM_ZONES:
        if upper is None or form < upper:
            return name
    return None


def form_state(ctl: float | None, atl: float | None) -> dict[str, Any] | None:
    """Die Form-Einstufung - EIN Erzeuger fuer Belastungs-Reiter und Ampel (0.67.4, F2.9).

    ABSOLUT (Entscheidung 24.09.): `form = ctl - atl` gegen FORM_ZONES. Bis
    0.67.3 stufte der Belastungs-Reiter absolut und die Ampel relativ
    (form / ctl); bei CTL um 30 ist relativ dreimal so grob (6,8 Last = 21,5 %),
    und beide Reiter widersprachen sich ("Grauzone" gegen "Uebergang, amber").
    Der relative Wert reist als `percent` mit, entscheidet aber nicht.
    """
    if ctl is None or atl is None:
        return None
    form = float(ctl) - float(atl)
    zone = form_zone(form)
    if zone is None:
        return None
    return {
        "form": form,
        "percent": form_percent(ctl, atl),
        "zone": zone,
        "state": {"high_risk": "red", "optimal": "green", "grey": "green",
                  "fresh": "green", "transition": "amber"}[zone],
        "label": {"high_risk": "hohes Risiko", "optimal": "optimal", "grey": "Grauzone",
                  "fresh": "frisch", "transition": "Übergang, lange ohne Reiz"}[zone],
    }


def form_percent(ctl: float | None, atl: float | None) -> float | None:
    """Return form as a percentage of fitness, the Intervals.icu default."""
    if ctl is None or atl is None or not ctl:
        return None
    return (ctl - atl) / ctl * 100


def _week_key(day: str) -> str:
    """Return the ISO week a date belongs to, as 2026-W37."""
    parsed = date.fromisoformat(day)
    year, week, _ = parsed.isocalendar()
    return f"{year}-W{week:02d}"


def load_by_day(data: dict[str, Any]) -> dict[str, float]:
    """Die Tageslast als Woerterbuch Tag -> Last - derselbe Erzeuger wie daily_load.

    EINE Tageslast (0.67.2, Sollzustand S2): bis 0.67.1 rechneten vier Stellen
    sie verschieden - hier ctlLoad mit Luecken = 0, `coach._acwr_local`
    ctlLoad mit Rueckfall auf `load` ohne Luecken, `coach._day_load` aus den
    Aktivitaeten, Plan und Kalender-Woche aus der Aktivitaetssumme. Am
    Livebestand (Messung 24.09.) sind ctlLoad und Aktivitaetssumme an 60 von 60
    Tagen gleich; die Wahl ist Bauhygiene. Alle lesen jetzt hier.
    """
    return {row["date"]: float(row.get("load") or 0.0) for row in daily_load(data)}


def daily_load(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the daily training load, oldest first, gaps filled with zero.

    DIE EINE REGEL (0.67.2, S2): `wellness.ctlLoad`, und wo Intervals den Tag
    nicht gefuellt hat, die Summe der Aktivitaetslasten dieses Tages. Der
    Rueckfall traegt den Fall aus 0.29.0 ("0 Last in sieben Tagen" auf einem
    Konto ohne das Feld); am Livebestand sind beide Reihen an 60 von 60 Tagen
    gleich (Messung 24.09.), dort ist er ohne Wirkung.
    """
    wellness = data.get("wellness") or {}
    days = sorted(wellness)
    if not days:
        return []
    from_activities: dict[str, float] = {}
    for activity in (data.get("activities") or {}).values():
        day_key = str(activity.get("start_date_local") or "")[:10]
        if day_key:
            from_activities[day_key] = from_activities.get(day_key, 0.0) + float(activity.get("icu_training_load") or 0)

    start = date.fromisoformat(days[0])
    end = date.fromisoformat(days[-1])
    series: list[dict[str, Any]] = []
    current = start
    while current <= end:
        key = current.isoformat()
        row = wellness.get(key) or {}
        value = row.get("ctlLoad")
        if value is None:
            value = from_activities.get(key, 0.0)
        series.append({"date": key, "load": float(value) if value else 0.0})
        current += timedelta(days=1)
    return series


def weekly_summary(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return per-week load, monotony and strain.

    Monotony is Foster's: the week's mean daily load divided by its standard
    deviation. A week of identical days scores high even at modest volume,
    which is the point of the metric. Strain multiplies the week's load by it.
    """
    buckets: dict[str, list[float]] = {}
    for point in daily_load(data):
        buckets.setdefault(_week_key(point["date"]), []).append(point["load"])

    result: list[dict[str, Any]] = []
    for week in sorted(buckets):
        loads = buckets[week]
        total = sum(loads)
        spread = pstdev(loads) if len(loads) > 1 else 0.0
        trained = sum(1 for value in loads if value > 0)
        # Below three training days the ratio says nothing: a week with one
        # session scores a low monotony simply because the zeros dominate.
        monotony = (mean(loads) / spread) if spread > 0 and trained >= 3 else None
        result.append(
            {
                "week": week,
                "load": round(total, 1),
                "days": len(loads),
                "days_trained": sum(1 for value in loads if value > 0),
                "monotony": round(monotony, 2) if monotony else None,
                "strain": round(total * monotony, 0) if monotony else None,
            }
        )
    return result


def hrv_status(data: dict[str, Any], baseline_days: int = baseline.WINDOW) -> dict[str, Any] | None:
    """Return the HRV trend against its smallest worthwhile change.

    Follows the HRV-guided training literature: work on the 7-day rolling mean
    of ln(rMSSD) and compare it with the baseline mean plus/minus half a
    standard deviation (Plews u. a. 2013: SWC = 0,5 x Streuung der Naechte
    der Basisperiode).

    S1 (0.69.0): DAS BAND IST DAS DES TRAINERS - `baseline.band_before`, die
    `baseline_days` Naechte VOR dem juengsten Tag, gewichtet ueber die
    Tagesetiketten. Bis 0.68.0 rechnete diese Funktion Mittel und Streuung der
    letzten 60 ROLLWERTE einschliesslich heute, ungewichtet - die zweite von
    drei HRV-Basislinien im Paket (Karte 4b, F4b.3). Die 7-Tage-Rollung
    bleibt als Leseweise: verglichen wird das 7-Tage-Mittel mit dem Band.

    Caveat carried in the payload: the wellness HRV comes from an overnight
    wearable measurement, not the validated morning supine recording, so this
    is a trend against your own baseline - not a clinical figure.
    """
    wellness = data.get("wellness") or {}
    values: dict[str, float] = {}
    points: list[tuple[str, float]] = []
    for day in sorted(wellness):
        value = (wellness[day] or {}).get("hrv")
        if value:
            try:
                v = float(value)
            except (TypeError, ValueError):
                continue
            if v > 0:
                values[day] = v
                points.append((day, math.log(v)))

    if len(points) < 14:
        return None

    rolling: list[dict[str, Any]] = []
    for index in range(6, len(points)):
        window = [value for _, value in points[index - 6 : index + 1]]
        rolling.append({"date": points[index][0], "ln_rmssd_7d": round(mean(window), 4)})

    today = points[-1][0]
    band = baseline.band_before(data, values, today, log=True, window=baseline_days)
    if band is None:
        return None
    swc = 0.5 * band.spread
    latest = rolling[-1]["ln_rmssd_7d"]

    if latest > band.base + swc:
        state = "above"
    elif latest < band.base - swc:
        state = "below"
    else:
        state = "normal"

    return {
        "series": rolling,
        "latest": latest,
        "baseline": round(band.base, 4),
        "spread": round(band.spread, 4),
        "swc": round(swc, 4),
        "state": state,
        "baseline_days": min(baseline_days, len([d for d in values if d < today])),
        "weighted": band.weighted,
        "labeled": band.labeled,
        "weight_sum": band.weight_sum,
        "baseline_note": baseline.fallback_note(band),
        "note": "overnight wearable HRV, not a morning supine recording",
    }


def _seconds(value: Any) -> float:
    """Return the seconds out of a zone-time entry.

    Intervals delivers two shapes: heart rate zone times come as a plain list
    of seconds, power zone times as a list of objects carrying secs. Both are
    accepted; anything else counts as zero instead of taking the panel down.
    """
    if isinstance(value, dict):
        for key in ("secs", "seconds", "time", "value"):
            if isinstance(value.get(key), (int, float)):
                return float(value[key])
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _three_zone(zone_times: list[Any] | None) -> tuple[float, float, float] | None:
    """Collapse a zone-time array into Seiler's three intensity zones.

    Zone 1 is everything below the first threshold, zone 2 the band around it,
    zone 3 everything above the second threshold. Five-zone models map 1-2 /
    3 / 4-5, seven-zone models map 1-3 / 4 / 5-7 - both keep the middle band
    at the threshold zone.
    """
    if not zone_times:
        return None
    if not isinstance(zone_times, (list, tuple)):
        return None
    times = [_seconds(value) for value in zone_times]
    if sum(times) <= 0:
        return None

    if len(times) <= 3:
        low, middle, high = times[0], times[1] if len(times) > 1 else 0.0, times[2] if len(times) > 2 else 0.0
    elif len(times) <= 5:
        low, middle, high = sum(times[0:2]), times[2], sum(times[3:])
    else:
        low, middle, high = sum(times[0:3]), times[3], sum(times[4:])

    total = low + middle + high
    return (low / total * 100, middle / total * 100, high / total * 100)


def intensity_distribution(data: dict[str, Any], days: int = 90) -> dict[str, Any] | None:
    """Return the three-zone intensity split over the last n days.

    Power zone times are preferred where they exist, heart rate zone times
    otherwise - the same order Intervals uses for load.
    """
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    low = middle = high = 0.0
    sessions = 0

    for activity in (data.get("activities") or {}).values():
        start = str(activity.get("start_date_local") or "")[:10]
        if start < cutoff:
            continue
        shares = _three_zone(activity.get("icu_zone_times")) or _three_zone(
            activity.get("icu_hr_zone_times")
        )
        if not shares:
            continue
        seconds = float(activity.get("moving_time") or 0)
        if seconds <= 0:
            continue
        low += shares[0] / 100 * seconds
        middle += shares[1] / 100 * seconds
        high += shares[2] / 100 * seconds
        sessions += 1

    total = low + middle + high
    if not total:
        return None

    return {
        "days": days,
        "sessions": sessions,
        "low": round(low / total * 100, 1),
        "middle": round(middle / total * 100, 1),
        "high": round(high / total * 100, 1),
        "hours": round(total / 3600, 1),
    }


def dfa_distribution(data: dict[str, Any], days: int = 90) -> dict[str, Any] | None:
    """Return the measured intensity split from the DFA alpha-1 summaries.

    Unlike zone times this needs no thresholds at all: DFA alpha-1 above 0.75
    is below the aerobic threshold, under 0.5 above the anaerobic one.
    """
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    aerobic = transition = anaerobic = 0.0
    sessions = 0

    for key, activity in (data.get("activities") or {}).items():
        if str(activity.get("start_date_local") or "")[:10] < cutoff:
            continue
        summary = (data.get("dfa") or {}).get(key)
        if not summary:
            continue
        aerobic += summary.get("secs_aerobic") or 0
        transition += summary.get("secs_transition") or 0
        anaerobic += summary.get("secs_anaerobic") or 0
        sessions += 1

    total = aerobic + transition + anaerobic
    if not total:
        return None

    return {
        "days": days,
        "sessions": sessions,
        "aerobic": round(aerobic / total * 100, 1),
        "transition": round(transition / total * 100, 1),
        "anaerobic": round(anaerobic / total * 100, 1),
        "hours": round(total / 3600, 1),
    }


def decoupling_series(data: dict[str, Any], min_minutes: int = 45) -> list[dict[str, Any]]:
    """Return decoupling per steady endurance session, oldest first.

    "Steady" is now enforced instead of promised: until 0.39.0 this filtered on
    duration alone, so a rolling group ride and a trainer session sat in the
    same chart as a steady outdoor ride - and the durability tile, which does
    filter, showed decoupling from a different population than the chart right
    next to it. Both now ask derive.steady_endurance_reason().
    """
    out: list[dict[str, Any]] = []
    for activity in (data.get("activities") or {}).values():
        value = activity.get("decoupling")
        if value is None:
            continue
        if derive.steady_endurance_reason(activity, min_minutes) is not None:
            continue
        out.append(
            {
                "date": str(activity.get("start_date_local") or "")[:10],
                "type": activity.get("type"),
                "decoupling": round(float(value), 1),
                "load": activity.get("icu_training_load"),
                "hours": round(float(activity.get("moving_time") or 0) / 3600, 1),
            }
        )
    out.sort(key=lambda item: item["date"])
    return out


def decoupling_verdict(value: float | None) -> str:
    """Return how to read a decoupling value.

    Negative values mean the power-to-heart-rate ratio held up or improved in
    the second half - not a warning. Only a rise beyond about five percent on
    a steady ride points at a thin aerobic base.
    """
    if value is None:
        return "unknown"
    if value <= 0:
        return "none"
    if value <= DECOUPLING_GOOD:
        return "good"
    return "high"


def ramp_rate(data: dict[str, Any]) -> float | None:
    """Return the newest ramp rate Intervals reports (weekly CTL change)."""
    wellness = data.get("wellness") or {}
    for day in sorted(wellness, reverse=True):
        value = (wellness[day] or {}).get("rampRate")
        if value is not None:
            return round(float(value), 2)
    return None


def _safe(label: str, function: Any, *args: Any, default: Any = None) -> Any:
    """Run one analysis, and let the rest survive if it fails.

    The panel asks for everything in one call; a single odd payload must not
    blank every view. The failure is logged, the section comes back empty.
    """
    try:
        return function(*args)
    except Exception:  # noqa: BLE001 - defensive by intent
        _LOGGER.exception("Intervals.icu: analysis %s failed", label)
        return default


def summary(data: dict[str, Any]) -> dict[str, Any]:
    """Return the whole load picture in one payload for the panel.

    0.74.0 (Skizze §3.1 i): ohne `acwr`, `acwr_latest` und `thresholds.acwr_*`
    - ihr einziger Leser war die ACWR-Kurve des Belastungs-Reiters, die durch
    den Verlauf der 7-Tage-Last ersetzt ist (coach.load_view). 0.74.1 (B4):
    die alte ACWR-Reihe ist entfernt - das Verhaeltnis kommt nur aus `window_ratio`.
    """
    weeks = _safe("weekly", weekly_summary, data, default=[])
    days = sorted((data.get("wellness") or {}))
    latest_row = (data.get("wellness") or {}).get(days[-1]) if days else {}
    ctl = (latest_row or {}).get("ctl")
    atl = (latest_row or {}).get("atl")

    return {
        "weeks": weeks[-26:],
        "ramp_rate": ramp_rate(data),
        "form": (ctl - atl) if ctl is not None and atl is not None else None,
        "form_percent": form_percent(ctl, atl),
        # ein Erzeuger (F2.9): dieselbe Einstufung wie die Ampel
        "form_zone": (form_state(ctl, atl) or {}).get("zone"),
        "intensity": _safe("intensity", intensity_distribution, data),
        "dfa_distribution": _safe("dfa_distribution", dfa_distribution, data),
        "decoupling": (_safe("decoupling", decoupling_series, data, default=[]) or [])[-40:],
        "hrv": _safe("hrv", hrv_status, data),
        "thresholds": {
            "monotony_watch": MONOTONY_WATCH,
            "decoupling_good": DECOUPLING_GOOD,
            "polarized_low": POLARIZED_LOW,
            "polarized_middle": POLARIZED_MIDDLE,
        },
    }


# --- readiness ----------------------------------------------------------------
# A traffic light built from components that are each documented on their own.
# The composite is a heuristic: no published score combines exactly these
# signals, and commercial readiness scores are not independently validated.
# Every component therefore stays visible with its own verdict and source.

RHR_WATCH_SD = 1.0
RHR_ALARM_SD = 2.0
SLEEP_WATCH_HOURS = 1.0
SLEEP_ALARM_HOURS = 2.0
STATE_ORDER = {"green": 0, "amber": 1, "red": 2, "unknown": -1}


def _baseline(values: list[float]) -> tuple[float, float]:
    """Return mean and standard deviation of a baseline window."""
    return (mean(values), pstdev(values) if len(values) > 1 else 0.0)


def _recent(data: dict[str, Any], field: str, days: int) -> list[float]:
    """Return the last n non-null values of a wellness field, oldest first."""
    wellness = data.get("wellness") or {}
    out: list[float] = []
    for day in sorted(wellness)[-days:]:
        value = (wellness[day] or {}).get(field)
        if value is not None:
            try:
                out.append(float(value))
            except (TypeError, ValueError):
                continue
    return out


def readiness(data: dict[str, Any]) -> dict[str, Any]:
    """Return a per-signal traffic light and its overall colour (since 0.73.1 without a load budget)."""
    components: list[dict[str, Any]] = []

    # --- HRV against its own smallest worthwhile change -----------------------
    hrv = hrv_status(data)
    if hrv:
        distance = hrv["latest"] - hrv["baseline"]
        if hrv["swc"] and distance < -2 * hrv["swc"]:
            state, detail = "red", "deutlich unter der Basislinie"
        elif hrv["swc"] and distance < -hrv["swc"]:
            state, detail = "amber", "unter der Basislinie"
        else:
            state, detail = "green", "im Normalbereich oder darüber"
        components.append({
            "id": "hrv", "label": "Herzratenvariabilität", "state": state,
            "value": round(hrv["latest"], 3), "reference": round(hrv["baseline"], 3),
            "detail": detail,
            "weighted": hrv.get("weighted"), "labeled": hrv.get("labeled"),
            "source": "7-Tage-Mittel von ln(rMSSD) gegen die kleinste bedeutsame Änderung "
                      "(Mittelwert ± 0,5 SD) aus der HRV-gesteuerten Trainingssteuerung — "
                      "dieselbe Basislinie wie beim Trainer: die 60 Nächte davor, gewichtet "
                      "über deine Tagesetiketten (S1). "
                      "Dein Wert kommt aus der Nachtmessung der Uhr; in einer Gerätevergleichsstudie "
                      "wurde Garmin bei der nächtlichen Ruhepuls-Auswertung wegen methodischer "
                      "Inkonsistenzen sogar ausgeschlossen — als Trend gegen die eigene Basislinie brauchbar, "
                      "als Absolutwert nicht.",
        })
    else:
        components.append({"id": "hrv", "label": "Herzratenvariabilität", "state": "unknown",
                           "detail": "zu wenig Daten", "source": ""})

    # --- resting heart rate against a 30-day baseline --------------------------
    rhr_values = _recent(data, "restingHR", 30)
    if len(rhr_values) >= 10:
        base, spread = _baseline(rhr_values[:-1])
        latest = rhr_values[-1]
        delta = latest - base
        if spread and delta >= RHR_ALARM_SD * spread:
            state, detail = "red", "deutlich erhöht"
        elif spread and delta >= RHR_WATCH_SD * spread:
            state, detail = "amber", "erhöht"
        else:
            state, detail = "green", "unauffällig"
        components.append({
            "id": "rhr", "label": "Ruhepuls", "state": state,
            "value": round(latest, 1), "reference": round(base, 1),
            "detail": f"{detail} ({delta:+.1f} bpm gegenüber 30-Tage-Mittel)",
            "source": "Ruhepuls gilt als niedrigschwelliger Zusatzindikator für physiologische "
                      "Beanspruchung; er ersetzt die HRV nicht, sondern ergänzt sie.",
        })
    else:
        components.append({"id": "rhr", "label": "Ruhepuls", "state": "unknown",
                           "detail": "zu wenig Daten", "source": ""})

    # --- sleep against your own habit -------------------------------------------
    sleep_values = [value / 3600 for value in _recent(data, "sleepSecs", 30)]
    if len(sleep_values) >= 7:
        base = mean(sleep_values[:-1])
        latest = sleep_values[-1]
        delta = latest - base
        if delta <= -SLEEP_ALARM_HOURS:
            state, detail = "red", "deutlich kürzer als gewohnt"
        elif delta <= -SLEEP_WATCH_HOURS:
            state, detail = "amber", "kürzer als gewohnt"
        else:
            state, detail = "green", "im gewohnten Rahmen"
        components.append({
            "id": "sleep", "label": "Schlaf", "state": state,
            "value": round(latest, 2), "reference": round(base, 2),
            "detail": f"{detail} ({delta:+.1f} h)",
            "source": "Schlaf wirkt auf Erholung, empfundene Anstrengung und Leistung; "
                      "verglichen wird gegen deinen eigenen 30-Tage-Schnitt, nicht gegen eine Norm.",
        })
    else:
        components.append({"id": "sleep", "label": "Schlaf", "state": "unknown",
                           "detail": "zu wenig Daten", "source": ""})

    # --- form ---------------------------------------------------------------------
    days = sorted((data.get("wellness") or {}))
    latest_row = (data.get("wellness") or {}).get(days[-1]) if days else {}
    ctl = (latest_row or {}).get("ctl")
    atl = (latest_row or {}).get("atl")
    fs = form_state(ctl, atl)
    if fs is None:
        components.append({"id": "form", "label": "Form", "state": "unknown",
                           "detail": "keine Daten", "source": ""})
    else:
        components.append({
            "id": "form", "label": "Form", "state": fs["state"],
            "value": round(fs["form"], 1),
            "reference": None, "detail": fs["label"],
            "percent": round(fs["percent"], 1) if fs.get("percent") is not None else None,
            "source": "Zonen nach Joe Friel, absolut (CTL − ATL) — dieselbe Einstufung wie im "
                      "Belastungs-Reiter. Faustregel, keine Wissenschaft.",
        })

    # --- acute against chronic --------------------------------------------------------
    # 0.74.0 (Skizze §3.1 h): EIN 4-Wochen-Schnitt. Das Verhaeltnis kommt aus
    # load_budget (heute = letzter Wellness-Tag): Fensterlast der 7 Tage bis
    # heute Abend / (7 x Schnitt der 28 Tage VOR heute) - derselbe Schnitt wie
    # Heute-Kopf und Trainer. Bis 0.73.4 las dieser Punkt die ACWR-Reihe (Schnitt
    # INKLUSIVE heute). Schwellen, Texte und Einstufung bleiben.
    # 0.74.1 (B4): die Rechnung steht in window_ratio - dieselbe Funktion wie coach.signals.
    wellness_days = sorted(data.get("wellness") or {})
    ratio = window_ratio(data, wellness_days[-1]) if wellness_days else None
    if ratio is not None:
        if ratio > ACWR_RISK:
            state, detail = "red", "deutlich über dem Korridor"
        elif ratio > ACWR_HIGH:
            state, detail = "amber", "über dem Korridor"
        elif ratio < ACWR_LOW:
            state, detail = "green", "unter dem Korridor — Luft nach oben"
        else:
            state, detail = "green", "im Korridor"
        components.append({
            "id": "acwr", "label": "Akut zu chronisch", "state": state,
            "value": ratio, "reference": ACWR_HIGH, "detail": detail,
            "source": "Korridor 0,8–1,3 und Risikomarke 1,5 nach Gabbett und Blanch. "
                      "Die Belege sind korrelativ und mathematisch gekoppelt; eine formelle "
                      "Richtigstellung wurde beantragt, eine randomisierte Studie fand keinen Nutzen.",
        })

    # --- monotony of the running week ------------------------------------------------
    weeks = weekly_summary(data)
    monotony = weeks[-1]["monotony"] if weeks else None
    if monotony is None:
        # Kept as a row on purpose: a signal that silently disappears midweek
        # makes the light look different on Tuesday than on Friday.
        components.append({
            "id": "monotony", "label": "Monotonie", "state": "unknown",
            "detail": "noch zu wenige Einheiten in dieser Woche",
            "source": "Foster: Wochenmittel geteilt durch Streuung. Unter drei Trainingstagen "
                      "sagt der Wert nichts, weil die Ruhetage die Streuung bestimmen.",
        })
    else:
        state = "amber" if monotony >= MONOTONY_WATCH else "green"
        components.append({
            "id": "monotony", "label": "Monotonie", "state": state,
            "value": monotony, "reference": MONOTONY_WATCH,
            "detail": "eintönige Woche" if state == "amber" else "genug Abwechslung",
            "source": "Foster: Wochenmittel geteilt durch Streuung. Hohe Werte stehen für "
                      "gleichförmige Wochen ohne echten Ruhetag.",
        })

    # --- subjective wellness ------------------------------------------------------------
    subjective = {field: _recent(data, field, 3) for field in ("fatigue", "soreness", "stress", "mood")}
    if any(subjective.values()):
        worst = max((values[-1] for values in subjective.values() if values), default=None)
        state = "amber" if worst and worst >= 3 else "green"
        components.append({
            "id": "subjective", "label": "Eigene Einschätzung", "state": state,
            "value": worst, "reference": 3, "detail": "aus deinen Einträgen in Intervals",
            "source": "Selbsteingeschätzte Werte bilden akute und chronische Belastung "
                      "empfindlicher und beständiger ab als objektive Messwerte "
                      "(systematischer Review, Saw et al.).",
        })
    else:
        components.append({
            "id": "subjective", "label": "Eigene Einschätzung", "state": "unknown",
            "detail": "nicht erfasst",
            "source": "Der systematische Review von Saw und Kollegen zeigt: selbsteingeschätzte "
                      "Werte schlagen objektive Messwerte in Empfindlichkeit und Beständigkeit. "
                      "In Intervals unter Einstellungen die tägliche Wellness-Abfrage einschalten — "
                      "das ist die wirksamste Einzelmaßnahme für diese Ampel.",
        })

    # --- overall ---------------------------------------------------------------------------
    states = [item["state"] for item in components if item["state"] != "unknown"]
    if "red" in states:
        overall = "red"
    elif states.count("amber") >= 2:
        overall = "red"
    elif "amber" in states:
        overall = "amber"
    elif states:
        overall = "green"
    else:
        overall = "unknown"

    # S1 (0.69.0): die Vorbemerkung kommt aus dem Band selbst - gewichtet mit
    # wie vielen Etiketten, oder auf ungewichtet zurueckgefallen und warum.
    # Bis 0.68.0 schrieb websocket_readiness "ungewichtet gerechnet" daneben.
    context_note = None
    if hrv and hrv.get("labeled"):
        if hrv.get("weighted"):
            n = int(hrv["labeled"])
            context_note = (f"gewichtet gerechnet — {n} etikettierte {'Tag' if n == 1 else 'Tage'} "
                            f"im Fenster der 60 Nächte davor, dieselbe Basislinie wie beim Trainer")
        else:
            context_note = hrv.get("baseline_note")

    return {
        "overall": overall,
        "components": components,
        "context_note": context_note,
        "note": "Die einzelnen Signale sind belegt, ihre Kombination ist es nicht: "
                "keine veröffentlichte Studie verrechnet genau diese Werte, und die "
                "Bereitschaftswerte kommerzieller Anbieter sind nicht unabhängig validiert. "
                "Als Entscheidungshilfe gedacht, nicht als Vorschrift.",
    }


def load_budget(data: dict[str, Any], state: str = "green", today: str | None = None,
                planned: dict[str, float] | None = None) -> dict[str, Any] | None:
    """Return how much load today may carry, derived from the ACWR definition.

    The ratio is the 7-day mean load over the 28-day mean. Solving it for
    today's load gives an upper bound: load = 7 x chronic x target minus the
    six days before. The target is tightened when the traffic light is not
    green - which is a choice, not a finding.

    0.74.0 (Skizze §3.1 a): `planned` = {Datum: Last}. Ist er gesetzt (auch
    leer), laeuft die Reihe lueckenlos bis `today` weiter, und geplante Tage
    zaehlen, als waeren sie gefahren - eine Festlegung fuer die Vorschau. Ohne
    `planned` bleibt alles bitgenau wie 0.73.4. Die 28 Tage Verlauf zaehlen
    nur echte Tage.
    """
    series = daily_load(data)
    if len(series) < 28:
        return None
    if planned is not None:
        series = _with_planned(series, planned, str(today or date.today().isoformat())[:10])

    # BUDGET = GESAMTLAST DES TAGES, NICHT RESTLAST (0.67.3, F2.10, Entscheidung
    # 24.09.). Die Reihe endet am letzten wellness-Tag - am Livebestand ist das
    # HEUTE, mit Last 0 bis zum Import und danach mit der eigenen Fahrt. Bis
    # 0.67.2 lagen heute und nur fuenf Tage davor in `last_six`, und das Budget
    # schrumpfte im Lauf des Tages um die Fahrt, die es erlauben sollte. Jetzt
    # zaehlen die sechs Tage VOR heute; die heutige Last reist als Verbrauch mit.
    day_today = str(today or date.today().isoformat())[:10]
    before, today_row = _window_rows(series, day_today)
    # 0.74.2 (B3): DIE 28 TAGE GELTEN FUER DEN TAG. Bis 0.74.1 pruefte nur die
    # Laenge der ganzen Reihe (oben); ein Tag mit weniger als 28 Tagen davor
    # rechnete mit einem kuerzeren Schnitt. Die Definition 7:28 braucht 28 Tage
    # VOR dem Tag - keine neue Setzung. Die Pruefung oben bleibt: geplante Tage
    # zaehlen nicht als Verlauf.
    if len(before) < 28:
        return None
    loads = [point["load"] for point in before]
    used_today = float(today_row[0]["load"]) if today_row else 0.0
    chronic = mean(loads[-28:])
    last_six = sum(loads[-6:])
    if chronic <= 0:
        return None

    targets = {"green": ACWR_HIGH, "amber": 1.0, "red": ACWR_LOW, "unknown": 1.0}
    target = targets.get(state, 1.0)

    def allowed(factor: float) -> int:
        return max(0, round(7 * chronic * factor - last_six))

    # 0.73.0 (Skizze §5.1): DAS FENSTER, aus derselben Rechnung - die sechs
    # Tage vor heute und heute. Keine neue Formel: `window_allowed` ist der
    # Zielwert 7 x chronisch x Ziel VOR dem Abzug der sechs Tage, `window_free`
    # das, was nach allen sieben Tagen (heute eingeschlossen) noch frei ist.
    # Die Baender sind die Faktoren, die hier schon stehen (0,8/1,0/1,3/1,5).
    six = before[-6:]
    window_load = last_six + used_today
    # 0.73.1 (2.3): WANN LAST AUS DEM FENSTER FAELLT - der aelteste Fenstertag
    # MIT Last (ein Tag mit 0 macht beim Herausfallen nichts frei), und der Tag,
    # an dem er nicht mehr zaehlt. Keine Aussage "wird Platz": der 28-Tage-
    # Schnitt bewegt sich mit.
    loaded = next((p for p in six + today_row if p["load"] > 0), None)
    # 0.73.1 (2.4): der Tag VOR dem Fenster - gegenueber dem Fenster von gestern
    # ist er herausgefallen (Hinweis im Morgen-Modus). Aus derselben Reihe.
    prior = before[-7] if len(before) >= 7 else None

    def zone(factor: float) -> int:
        return round(7 * chronic * factor)

    return {
        "chronic": round(chronic, 1),
        "last_six_days": round(last_six, 1),
        "target_ratio": target,
        "recommended": allowed(target),
        "used_today": round(used_today, 1),
        "steady": allowed(1.0),
        "corridor_top": allowed(ACWR_HIGH),
        "risk_top": allowed(ACWR_RISK),
        "state": state,
        "window_start": six[0]["date"] if six else day_today,
        "window_end": day_today,
        "window_load": round(window_load, 1),
        "window_allowed": zone(target),
        "window_free": max(0, round(7 * chronic * target - window_load)),
        "window_bands": {"low": zone(ACWR_LOW), "steady": zone(1.0),
                         "top": zone(ACWR_HIGH), "risk": zone(ACWR_RISK)},
        "drops_next": {"date": loaded["date"], "load": loaded["load"],
                       "leaves_on": (date.fromisoformat(loaded["date"]) + timedelta(days=7)).isoformat()}
        if loaded else None,
        "window_before": {"date": prior["date"], "load": prior["load"]} if prior else None,
    }


def window_ratio(data: dict[str, Any], day: str) -> float | None:
    """Akut zu chronisch an `day` - EINE Stelle (0.74.1, B4).

    = Fensterlast der 7 Tage bis `day` Abend / (7 x Schnitt der 28 Tage VOR
    `day`), beides aus `load_budget(..., today=day)`, also derselbe Schnitt wie
    Heute-Kopf und Trainer. Leser: `readiness` (Punkt "Akut zu chronisch") und
    `coach.signals` (Signale-Reiter). Bis 0.74.0 las signals die ACWR-Reihe
    (Schnitt INKLUSIVE des Tages) - ein zweiter Weg, jetzt entfernt. Die
    Rundung (Last und Schnitt auf eine Stelle, Verhaeltnis auf zwei) ist die
    von load_budget/readiness bis 0.74.0, bitgleich. Ohne Budget (unter 28
    Tagen vor `day`, 0.74.2) oder mit Schnitt 0: None.
    """
    window = load_budget(data, "green", today=day)
    if not window or not window.get("chronic"):
        return None
    return round(window["window_load"] / (7 * window["chronic"]), 2)


def _window_rows(series: list[dict[str, Any]], day_today: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Die Tage VOR heute und die Zeile von heute - EINE Stelle fuer Budget und Fenster.

    `load_budget` nimmt davon die letzten sechs (und 28 fuer den Schnitt),
    `window_sessions` dieselben sechs plus heute. Die Reihe ist lueckenlos
    (`daily_load`), eine fehlende Wellness-Zeile ist ein Tag mit Last 0.
    """
    before = [point for point in series if point["date"] < day_today]
    today_row = [point for point in series if point["date"] == day_today]
    return before, today_row


def _with_planned(series: list[dict[str, Any]], planned: dict[str, float], until: str) -> list[dict[str, Any]]:
    """Die Tagesreihe, lueckenlos verlaengert bis `until` bzw. bis zum letzten
    geplanten Tag, mit der geplanten Last auf ihrem Tag (0.74.0, §3.1 a).

    Kopie - `series` bleibt unberuehrt. Geplante Tage vor dem Beginn der
    Reihe gibt es nicht; sie fallen weg.
    """
    rows = [dict(point) for point in series]
    if not rows:
        return rows
    last = max([until] + [str(d)[:10] for d in planned])
    current = date.fromisoformat(rows[-1]["date"]) + timedelta(days=1)
    stop = date.fromisoformat(last)
    while current <= stop:
        rows.append({"date": current.isoformat(), "load": 0.0})
        current += timedelta(days=1)
    index = {point["date"]: point for point in rows}
    for day, load in planned.items():
        point = index.get(str(day)[:10])
        if point is not None:
            point["load"] = point["load"] + float(load or 0.0)
    return rows


def planned_loads(events: Any, after: str | None, until: str | None = None) -> dict[str, float]:
    """Geplante Last je Tag aus den Kalender-Events - EINE Stelle (0.74.0, §3.1 g).

    Geplant heisst: `category == "WORKOUT"`, Datum NACH `after` (heute zaehlt
    nicht - es ist Teil von heute), bis `until` einschliesslich,
    `icu_training_load` > 0, kein `paired_activity_id` (erledigt, steht schon
    als Fahrt in der Tageslast). 0.74.1 (B6): kein `hide_from_athlete` -
    derselbe Filter wie `_day_planned`.
    """
    out: dict[str, float] = {}
    for event in events or []:
        if not isinstance(event, dict) or event.get("category") != "WORKOUT":
            continue
        if event.get("hide_from_athlete"):
            continue
        if event.get("paired_activity_id") not in (None, ""):
            continue
        day = str(event.get("start_date_local") or "")[:10]
        if not day or (after and day <= after) or (until and day > until):
            continue
        try:
            load = float(event.get("icu_training_load") or 0)
        except (TypeError, ValueError):
            continue
        if load > 0:
            out[day] = round(out.get(day, 0.0) + load, 1)
    return out


def _window_point(day: str, budget: dict[str, Any] | None, series: list[dict[str, Any]]) -> dict[str, Any]:
    """Ein Tag des Verlaufs. Mit Budget kommen Last und Ziel aus DIESEM Aufruf
    (keine eigene Rechnung). Ohne Budget (unter 28 Tagen vor dem Tag) kein Ziel;
    die Last sind dieselben sieben Tage (`_window_rows`), damit die Linie steht."""
    if budget:
        load, allowed = budget["window_load"], budget["window_allowed"]
    else:
        before, today_row = _window_rows(series, day)
        load, allowed = round(sum(point["load"] for point in before[-6:] + today_row), 1), None
    return {"date": day, "window_load": load, "window_allowed": allowed,
            "over": allowed is not None and load > allowed}


def window_history(data: dict[str, Any], light_by_day: dict[str, str], days: int = 60,
                   today: str | None = None) -> list[dict[str, Any]]:
    """Die letzten `days` Tage: je Tag die Last der 7 Tage bis Tagesende und das
    Ziel dieses Tages - aus `load_budget(data, light_by_day[Tag], today=Tag)`
    (0.74.0, §3.1 d). Fehlt das Licht eines Tages, gilt "unknown" (1,0).
    """
    series = daily_load(data)
    if not series:
        return []
    end = str(today or series[-1]["date"])[:10]
    dates = [point["date"] for point in series if point["date"] <= end][-days:]
    return [_window_point(day, load_budget(data, light_by_day.get(day, "unknown"), today=day), series)
            for day in dates]


def window_projection(data: dict[str, Any], light: str, planned: dict[str, float] | None,
                      days: int = 14, today: str | None = None) -> list[dict[str, Any]]:
    """Die naechsten `days` Tage mit dem Plan (0.74.0, §3.1 e): je Tag
    `load_budget(..., planned)`. Das Licht ist das von heute fuer alle Tage -
    fuer morgen gibt es keinen Zustand. Beides ist eine Festlegung.
    """
    series = daily_load(data)
    if not series:
        return []
    start = date.fromisoformat(str(today or series[-1]["date"])[:10])
    plan = dict(planned or {})
    out = []
    for step in range(1, days + 1):
        day = (start + timedelta(days=step)).isoformat()
        out.append(_window_point(day, load_budget(data, light, today=day, planned=plan),
                                 _with_planned(series, plan, day)))
    return out


def _planned_key(events: Any, paired_event_id: Any) -> str | None:
    """Der Katalogschluessel des gepaarten Events - oder None.

    a) `external_id` mit unserem Praefix -> Schluessel aus der ID;
       eine fremde external_id ist nicht unser Event.
    b) Altbestand ohne external_id: die Beschreibung beginnt mit der
       Hinweiszeile aus `workouts.to_event` UND der Name ist ein Katalogtitel.
    Kein Vergleich mit dem Namen der AKTIVITAET - der traegt nicht (Skizze §2).
    """
    wanted = str(paired_event_id)
    event = next((ev for ev in events or [] if isinstance(ev, dict) and str(ev.get("id")) == wanted), None)
    if event is None:
        return None
    external = event.get("external_id")
    if external:
        text = str(external)
        if not text.startswith(workouts.EXTERNAL_ID_PREFIX):
            return None
        key = text[len(workouts.EXTERNAL_ID_PREFIX):].split(":", 1)[0]
        return key if key in workouts.BY_KEY else None
    if not str(event.get("description") or "").startswith(workouts.DEFAULT_NOTE):
        return None
    name = event.get("name")
    return next((key for key, entry in workouts.BY_KEY.items() if entry.get("title") == name), None)


def activity_family(data: dict[str, Any], activity_id: Any, events: Any = None) -> dict[str, Any] | None:
    """Die Familie einer gefahrenen Einheit - EINE Stelle (0.73.0, Skizze §4).

    Gepaart wird nicht von uns. Gelesen wird, was schon feststeht:
    1. die MARKEN des Athleten (section_marks) - die Familien der markierten
       Abschnitte; mehrere Gruppen: die haerteste gibt die Gruppe
       (workouts.GROUP_ORDER, Setzung E3), `families` nennt alle;
    2. der PLAN - die Paarung von intervals.icu (`paired_event_id`) auf ein
       Event dieser App (`_planned_key`); nie bei einer Pendelfahrt, die
       intervals.icu faelschlich mitpaart;
    3. eine andere Sportart -> "other" mit dem Sportwort;
    4. sonst keine Gruppe ("ohne Zuordnung").
    Kein Namensvergleich mit der Aktivitaet, keine Zonen, kein WORK-Etikett,
    nicht der Namens-Rateweg aus blocks. Liest nur, schreibt nichts.
    `events` sind die Kalender-Events des Koordinators (nicht im Archiv);
    ohne Parameter wird `data["events"]` gelesen.
    """
    activity = (data.get("activities") or {}).get(str(activity_id))
    if not isinstance(activity, dict):
        return None
    kind, sport = sport_group(activity.get("type"))
    commute = bool(activity.get("commute"))
    out = {"group": None, "source": None, "families": [], "sport": sport, "commute": commute}

    entry = section_marks.entry_for(data, activity_id)
    names = [name for name in sorted(((entry or {}).get("marks") or {}))
             if name in workouts.FAMILY_GROUP and section_marks.marked(entry, name)]
    if names:
        groups = {workouts.FAMILY_GROUP[name] for name in names}
        out.update(group=next(g for g in workouts.GROUP_ORDER if g in groups),
                   source="marks", families=names)
        return out

    paired = activity.get("paired_event_id")
    if not commute and paired not in (None, ""):
        key = _planned_key(data.get("events") if events is None else events, paired)
        if key in workouts.KEY_GROUP:
            family = next(f for f, _l, keys in workouts.FAMILIES if key in keys)
            out.update(group=workouts.KEY_GROUP[key], source="plan", families=[family], key=key)
            return out

    if kind != "ride":
        out.update(group="other", source="sport")
    return out


def window_sessions(data: dict[str, Any], today: str | None = None, events: Any = None) -> dict[str, Any]:
    """Die Fahrten im Fenster der Wochenlast - dieselben Tage wie `load_budget`.

    Je Aktivitaet {date, name, sport, load, group, source, families, commute},
    aelteste zuerst, am Tag nach Startzeit. Ist die Tageslast (ctlLoad) groesser
    als die Summe der Aktivitaeten, steht der Rest als Stueck "ohne Einheit"
    (rest=True) daneben; dann ist die Summe = `window_load`. Ist sie KLEINER,
    wird nichts versteckt: der Tag steht in `mismatch`.
    Gilt auch unter 28 Tagen Verlauf (kein Budget, aber die Liste).
    Seit 0.74.0 rechnet `sessions_between` (eine Stelle); hier stehen nur die
    Tage des Fensters.
    """
    series = daily_load(data)
    day_today = str(today or date.today().isoformat())[:10]
    before, today_row = _window_rows(series, day_today)
    days = before[-6:] + today_row
    span = (days[0]["date"], days[-1]["date"]) if days else (day_today, day_today)
    return {
        "start": days[0]["date"] if days else day_today,
        "end": day_today,
        **sessions_between(data, span[0], span[1], events, series),
    }


def sessions_between(data: dict[str, Any], start: str, end: str, events: Any = None,
                     series: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Die Fahrten von `start` bis `end` (einschliesslich) mit Gruppe, Rest und
    Fehlstellen - EINE Stelle fuer Heute-Liste und Wochen (0.74.0, §3.1 b).

    Herausgeloest aus `window_sessions` (bis 0.73.4 dort), Rechnung unveraendert:
    je Tag der lueckenlosen Tagesreihe die Aktivitaeten nach Startzeit, ihre
    Gruppe aus `activity_family`; ist die Tageslast groesser als die Fahrten,
    steht der Rest als Stueck ohne Einheit (Gruppe none), ist sie kleiner, steht
    der Tag in `mismatch`. `total` ist die Summe der Tageslast.
    """
    series = daily_load(data) if series is None else series
    days = [point for point in series if start <= point["date"] <= end]
    by_day: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for key, activity in (data.get("activities") or {}).items():
        day = str(activity.get("start_date_local") or "")[:10]
        by_day.setdefault(day, []).append((str(key), activity))

    sessions: list[dict[str, Any]] = []
    mismatch: list[str] = []
    for point in days:
        day = point["date"]
        ridden = 0.0
        for key, activity in sorted(by_day.get(day, []), key=lambda kv: (str(kv[1].get("start_date_local") or ""), kv[0])):
            load = float(activity.get("icu_training_load") or 0)
            ridden += load
            fam = activity_family(data, key, events) or {}
            sessions.append({"date": day, "id": key, "name": activity.get("name"), "sport": fam.get("sport"),
                             "load": round(load, 1), "group": fam.get("group"), "source": fam.get("source"),
                             "families": fam.get("families") or [], "commute": bool(fam.get("commute")),
                             "rest": False})
        rest = point["load"] - ridden
        if rest > 0.05:
            sessions.append({"date": day, "id": None, "name": None, "sport": None, "load": round(rest, 1),
                             "group": None, "source": "rest", "families": [], "commute": False, "rest": True})
        elif rest < -0.05:
            mismatch.append(day)

    groups = {"grundlage": 0.0, "schwelle": 0.0, "vo2max": 0.0, "other": 0.0, "none": 0.0}
    for row in sessions:
        slot = row["group"] if row["group"] in groups else "none"
        groups[slot] += row["load"]
    return {
        "sessions": sessions,
        "groups": {k: round(v, 1) for k, v in groups.items()},
        "total": round(sum(point["load"] for point in days), 1),
        "mismatch": mismatch,
    }


def weeks_by_group(data: dict[str, Any], events: Any = None, today: str | None = None,
                   weeks: int = 12) -> list[dict[str, Any]]:
    """Die letzten `weeks` Kalenderwochen (Mo-So) je Gruppe (0.74.0, §3.1 c).

    Je Woche die Summen je Gruppe aus `sessions_between` (bis heute), dazu
    `monotony` aus `weekly_summary` (ein Erzeuger) und fuer die laufende Woche
    `planned`: die geplante Last der Tage nach heute bis Sonntag
    (`planned_loads`). `total` ist die gefahrene Summe (Tageslast).
    """
    series = daily_load(data)
    if not series:
        return []
    day_today = str(today or series[-1]["date"])[:10]
    now = date.fromisoformat(day_today)
    monday = now - timedelta(days=now.weekday())
    monotony = {row["week"]: row.get("monotony") for row in weekly_summary(data)}
    ahead = planned_loads(events, day_today, (monday + timedelta(days=6)).isoformat())
    out: list[dict[str, Any]] = []
    for back in range(weeks - 1, -1, -1):
        start = monday - timedelta(weeks=back)
        sunday = start + timedelta(days=6)
        part = sessions_between(data, start.isoformat(), min(sunday, now).isoformat(), events, series)
        key = _week_key(start.isoformat())
        out.append({
            "week": key, "start": start.isoformat(), "end": sunday.isoformat(),
            "current": back == 0,
            "groups": part["groups"], "total": part["total"], "mismatch": part["mismatch"],
            "planned": round(sum(ahead.values()), 1) if back == 0 else 0.0,
            "monotony": monotony.get(key),
        })
    return out


# --- calendar ------------------------------------------------------------------
# The week grid is the main view, so the backend hands over one ready record per
# day: wellness, what was done, what is planned. Position encodes time (the
# grid), length encodes amounts (the bars), hue encodes the sport - the split
# that graphical perception research supports.

SPORT_GROUPS = {
    "Ride": ("ride", "Rad"),
    "VirtualRide": ("ride", "Rad (Rolle)"),
    "GravelRide": ("ride", "Gravel"),
    "MountainBikeRide": ("ride", "MTB"),
    "Run": ("run", "Lauf"),
    "TrailRun": ("run", "Trail"),
    "VirtualRun": ("run", "Lauf (Band)"),
    "Walk": ("walk", "Gehen"),
    "Hike": ("walk", "Wandern"),
    "Swim": ("swim", "Schwimmen"),
    "OpenWaterSwim": ("swim", "Freiwasser"),
    "WeightTraining": ("gym", "Kraft"),
}


def sport_group(activity_type: Any) -> tuple[str, str]:
    """Return (group, label) for an activity type."""
    return SPORT_GROUPS.get(str(activity_type or ""), ("other", str(activity_type or "Sonstiges")))


def _day_activities(data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Return the stored activities grouped by day, newest last."""
    by_day: dict[str, list[dict[str, Any]]] = {}
    dfa_all = data.get("dfa") or {}

    for key, activity in (data.get("activities") or {}).items():
        day = str(activity.get("start_date_local") or "")[:10]
        if not day:
            continue
        group, label = sport_group(activity.get("type"))
        zones = _three_zone(activity.get("icu_zone_times")) or _three_zone(
            activity.get("icu_hr_zone_times")
        )
        summary = dfa_all.get(key) or None
        _thr = derive.threshold_verdict(summary)
        shares = None
        if summary:
            total = (summary.get("secs_aerobic") or 0) + (summary.get("secs_transition") or 0) + (
                summary.get("secs_anaerobic") or 0
            )
            if total:
                shares = [
                    round((summary.get("secs_aerobic") or 0) / total * 100),
                    round((summary.get("secs_transition") or 0) / total * 100),
                    round((summary.get("secs_anaerobic") or 0) / total * 100),
                ]

        by_day.setdefault(day, []).append(
            {
                "id": key,
                "name": activity.get("name"),
                "type": activity.get("type"),
                "group": group,
                "sport": label,
                "moving_time": activity.get("moving_time"),
                "distance": activity.get("distance"),
                "load": activity.get("icu_training_load"),
                "intensity": activity.get("icu_intensity"),
                "average_heartrate": activity.get("average_heartrate"),
                "average_watts": activity.get("icu_average_watts"),
                "decoupling": activity.get("decoupling"),
                "zones": [round(value, 1) for value in zones] if zones else None,
                "dfa": shares,
                # Same rule as everywhere else, called rather than re-stated.
                # This list carried the raw value with no check at all until
                # 0.45.0 - the fifth of five places, and the only one that had
                # no rule whatsoever.
                "threshold_hr": _thr["hr"],
                "threshold_windows": _thr["hr_windows"],
                "threshold_usable": _thr["hr_usable"],
                "threshold_failure": _thr["failure"],
            }
        )

    for items in by_day.values():
        items.sort(key=lambda item: str(item.get("id")))
    return by_day


def week_done(data: dict[str, Any], start: str, today: str | None = None) -> dict[str, Any]:
    """What has actually been ridden in the week starting on `start`.

    From the ARCHIVE, not from the calendar grid the panel holds: the browser
    keeps `_days` for the whole session and empties it only after an applied
    reconcile (docs/ausbau.md D6), so a week view hanging off that cache still
    shows this morning's state after the afternoon ride. And not from the
    planned events either - those never touch the archive.

    WE DO NOT PAIR (0.73.0, Skizze §4). Pairing a ride with a planned session
    is done by intervals.icu (`paired_event_id`, by load or moving time) or by
    the athlete (manually there, or by marking sections here). This app only
    READS both - in ONE place, `activity_family` - and never guesses from the
    ride's name, its zones or a WORK label: the archive names ("SweetSpot
    2x...") are not the catalogue titles, and a guessed pairing would be a
    claim the system cannot back up. This week view stays "ridden against
    planned" (`paired: False`); the Heute header shows the family where one
    is read.
    """
    first = date.fromisoformat(start)
    last = first + timedelta(days=6)
    mark = date.fromisoformat(today) if today else date.today()
    by_day = _day_activities(data)

    sessions: list[dict[str, Any]] = []
    for offset in range(7):
        day = (first + timedelta(days=offset)).isoformat()
        for item in by_day.get(day, []):
            sessions.append({
                "date": day,
                "name": item.get("name"),
                "sport": item.get("sport"),
                "group": item.get("group"),
                "hours": round((item.get("moving_time") or 0) / 3600, 1),
                "load": item.get("load"),
                "intensity": item.get("intensity"),
            })

    days_left = max(0, (last - mark).days) if first <= mark <= last else None
    return {
        "start": first.isoformat(),
        "end": last.isoformat(),
        "days_left": days_left,
        "sessions": len(sessions),
        "hours": round(sum(item["hours"] for item in sessions), 1),
        "load": round(sum(float(item["load"] or 0) for item in sessions)),
        "activities": sessions,
        "paired": False,
        "note": (
            "Gefahren gegen vorgesehen — welche Fahrt welche geplante Einheit war, "
            "entscheidest du. Die Familie einer Fahrt kommt aus deinen Marken oder aus "
            "der Paarung in intervals.icu; geraten wird nichts."
        ),
    }


def _day_planned(events: Any) -> dict[str, list[dict[str, Any]]]:
    """Return planned workouts grouped by day."""
    planned: dict[str, list[dict[str, Any]]] = {}
    for event in events or []:
        if not isinstance(event, dict) or event.get("hide_from_athlete"):
            continue
        day = str(event.get("start_date_local") or "")[:10]
        if not day:
            continue
        group, label = sport_group(event.get("type"))
        planned.setdefault(day, []).append(
            {
                "id": str(event.get("id") or ""),
                "name": event.get("name"),
                "type": event.get("type"),
                "group": group,
                "sport": label,
                "load": event.get("icu_training_load"),
                "moving_time": event.get("moving_time"),
                "description": event.get("description"),
                "done": bool(event.get("paired_activity_id")),
                "category": event.get("category"),
            }
        )
    return planned


def calendar_days(
    data: dict[str, Any],
    events: Any = None,
    weeks: int = 12,
    ahead_days: int = 14,
) -> dict[str, Any]:
    """Return the week grid: one record per day plus a summary per week."""
    today = date.today()
    # Start on the Monday of the first week shown.
    first = today - timedelta(days=today.weekday() + 7 * (weeks - 1))
    last = today + timedelta(days=ahead_days)

    wellness = data.get("wellness") or {}
    done = _day_activities(data)
    planned = _day_planned(events)

    days: list[dict[str, Any]] = []
    current = first
    while current <= last:
        key = current.isoformat()
        row = wellness.get(key) or {}
        ctl = row.get("ctl")
        atl = row.get("atl")
        activities = done.get(key, [])
        days.append(
            {
                "date": key,
                "weekday": current.weekday(),
                "week": _week_key(key),
                "future": current > today,
                "today": current == today,
                "ctl": ctl,
                "atl": atl,
                "form": (ctl - atl) if ctl is not None and atl is not None else None,
                "load": row.get("ctlLoad"),
                "sleep_hours": round(row["sleepSecs"] / 3600, 1) if row.get("sleepSecs") else None,
                "sleep_score": row.get("sleepScore"),
                "hrv": row.get("hrv"),
                "resting_hr": row.get("restingHR"),
                "weight": row.get("weight"),
                "steps": row.get("steps"),
                "activities": activities,
                "planned": planned.get(key, []),
            }
        )
        current += timedelta(days=1)

    # --- per week -----------------------------------------------------------
    summary: dict[str, dict[str, Any]] = {}
    for day in days:
        bucket = summary.setdefault(
            day["week"],
            {"week": day["week"], "load": 0.0, "seconds": 0.0, "distance": 0.0,
             "sessions": 0, "planned_load": 0.0, "ctl": None, "atl": None, "form": None,
             "start": day["date"]},
        )
        # Die Wochenlast ist die Summe der TAGESLASTEN (ein Erzeuger, S2) -
        # nicht mehr die Aktivitaetssumme neben Tageszellen aus ctlLoad (F4a.9).
        bucket["load"] += float(day.get("load") or 0)
        for activity in day["activities"]:
            bucket["seconds"] += float(activity.get("moving_time") or 0)
            bucket["distance"] += float(activity.get("distance") or 0)
            bucket["sessions"] += 1
        for item in day["planned"]:
            if not item["done"]:
                bucket["planned_load"] += float(item.get("load") or 0)
        if day["ctl"] is not None and not day["future"]:
            bucket["ctl"] = day["ctl"]
            bucket["atl"] = day["atl"]
            bucket["form"] = day["form"]

    for bucket in summary.values():
        bucket["load"] = round(bucket["load"])
        bucket["hours"] = round(bucket["seconds"] / 3600, 1)
        bucket["km"] = round(bucket["distance"] / 1000, 1)
        bucket["planned_load"] = round(bucket["planned_load"])

    ordered = [summary[key] for key in sorted(summary)]
    loads = [item["load"] for item in ordered if item["load"]]
    return {
        "days": days,
        "weeks": ordered,
        "today": today.isoformat(),
        "max_week_load": max(loads) if loads else 0,
        "avg_week_load": round(sum(loads) / len(loads)) if loads else 0,
        "max_day_load": max(
            [float(day["load"] or 0) for day in days] + [1.0]
        ),
    }
