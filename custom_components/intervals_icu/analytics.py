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
    from . import derive
    from .const import DECOUPLING_GOOD
except ImportError:  # standalone (test suite loads this file directly)
    import derive
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


def daily_load(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the daily training load, oldest first, gaps filled with zero."""
    wellness = data.get("wellness") or {}
    days = sorted(wellness)
    if not days:
        return []

    start = date.fromisoformat(days[0])
    end = date.fromisoformat(days[-1])
    series: list[dict[str, Any]] = []
    current = start
    while current <= end:
        key = current.isoformat()
        row = wellness.get(key) or {}
        value = row.get("ctlLoad")
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


def acwr_series(data: dict[str, Any], acute: int = 7, chronic: int = 28) -> list[dict[str, Any]]:
    """Return the acute:chronic workload ratio per day.

    Rolling averages, as in the original definition. Days before a full chronic
    window has accumulated carry no ratio - a ratio against three days of
    history says nothing.
    """
    series = daily_load(data)
    loads = [point["load"] for point in series]
    out: list[dict[str, Any]] = []

    for index, point in enumerate(series):
        if index + 1 < chronic:
            out.append({"date": point["date"], "acute": None, "chronic": None, "ratio": None})
            continue
        acute_mean = mean(loads[index + 1 - acute : index + 1])
        chronic_mean = mean(loads[index + 1 - chronic : index + 1])
        ratio = (acute_mean / chronic_mean) if chronic_mean else None
        out.append(
            {
                "date": point["date"],
                "acute": round(acute_mean, 1),
                "chronic": round(chronic_mean, 1),
                "ratio": round(ratio, 2) if ratio else None,
            }
        )
    return out


def hrv_status(data: dict[str, Any], baseline_days: int = 60) -> dict[str, Any] | None:
    """Return the HRV trend against its smallest worthwhile change.

    Follows the HRV-guided training literature: work on the 7-day rolling mean
    of ln(rMSSD) and compare it with the baseline mean plus/minus half a
    standard deviation.

    Caveat carried in the payload: the wellness HRV comes from an overnight
    wearable measurement, not the validated morning supine recording, so this
    is a trend against your own baseline - not a clinical figure.
    """
    wellness = data.get("wellness") or {}
    points: list[tuple[str, float]] = []
    for day in sorted(wellness):
        value = (wellness[day] or {}).get("hrv")
        if value:
            try:
                points.append((day, math.log(float(value))))
            except ValueError:
                continue

    if len(points) < 14:
        return None

    rolling: list[dict[str, Any]] = []
    for index in range(6, len(points)):
        window = [value for _, value in points[index - 6 : index + 1]]
        rolling.append({"date": points[index][0], "ln_rmssd_7d": round(mean(window), 4)})

    baseline_window = [item["ln_rmssd_7d"] for item in rolling[-baseline_days:]]
    base_mean = mean(baseline_window)
    base_sd = pstdev(baseline_window) if len(baseline_window) > 1 else 0.0
    swc = 0.5 * base_sd
    latest = rolling[-1]["ln_rmssd_7d"]

    if latest > base_mean + swc:
        state = "above"
    elif latest < base_mean - swc:
        state = "below"
    else:
        state = "normal"

    return {
        "series": rolling,
        "latest": latest,
        "baseline": round(base_mean, 4),
        "swc": round(swc, 4),
        "state": state,
        "baseline_days": len(baseline_window),
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
    """Return the whole load picture in one payload for the panel."""
    weeks = _safe("weekly", weekly_summary, data, default=[])
    acwr = _safe("acwr", acwr_series, data, default=[])
    latest_acwr = next(
        (item for item in reversed(acwr) if item["ratio"] is not None), None
    )
    days = sorted((data.get("wellness") or {}))
    latest_row = (data.get("wellness") or {}).get(days[-1]) if days else {}
    ctl = (latest_row or {}).get("ctl")
    atl = (latest_row or {}).get("atl")

    return {
        "weeks": weeks[-26:],
        "acwr": acwr[-180:],
        "acwr_latest": latest_acwr,
        "ramp_rate": ramp_rate(data),
        "form": (ctl - atl) if ctl is not None and atl is not None else None,
        "form_percent": form_percent(ctl, atl),
        "form_zone": form_zone((ctl - atl) if ctl is not None and atl is not None else None),
        "intensity": _safe("intensity", intensity_distribution, data),
        "dfa_distribution": _safe("dfa_distribution", dfa_distribution, data),
        "decoupling": (_safe("decoupling", decoupling_series, data, default=[]) or [])[-40:],
        "hrv": _safe("hrv", hrv_status, data),
        "thresholds": {
            "acwr_low": ACWR_LOW,
            "acwr_high": ACWR_HIGH,
            "acwr_risk": ACWR_RISK,
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
    """Return a per-signal traffic light plus a load budget for today."""
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
            "source": "7-Tage-Mittel von ln(rMSSD) gegen die kleinste bedeutsame Änderung "
                      "(Mittelwert ± 0,5 SD) aus der HRV-gesteuerten Trainingssteuerung. "
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
    form = (ctl - atl) if ctl is not None and atl is not None else None
    relative = form_percent(ctl, atl)
    zone = form_zone(relative if relative is not None else form)
    if zone is None:
        components.append({"id": "form", "label": "Form", "state": "unknown",
                           "detail": "keine Daten", "source": ""})
    else:
        state = {"high_risk": "red", "optimal": "green", "grey": "green",
                 "fresh": "green", "transition": "amber"}[zone]
        label = {"high_risk": "hohes Risiko", "optimal": "optimal", "grey": "Grauzone",
                 "fresh": "frisch", "transition": "Übergang, lange ohne Reiz"}[zone]
        components.append({
            "id": "form", "label": "Form", "state": state,
            "value": round(relative, 1) if relative is not None else None,
            "reference": None, "detail": label,
            "source": "Zonen nach Joe Friel, hier relativ zur Fitness gerechnet wie in Intervals. "
                      "Faustregel, keine Wissenschaft.",
        })

    # --- acute against chronic --------------------------------------------------------
    series = acwr_series(data)
    latest_acwr = next((item for item in reversed(series) if item["ratio"] is not None), None)
    if latest_acwr:
        ratio = latest_acwr["ratio"]
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

    return {
        "overall": overall,
        "components": components,
        "budget": load_budget(data, overall),
        "note": "Die einzelnen Signale sind belegt, ihre Kombination ist es nicht: "
                "keine veröffentlichte Studie verrechnet genau diese Werte, und die "
                "Bereitschaftswerte kommerzieller Anbieter sind nicht unabhängig validiert. "
                "Als Entscheidungshilfe gedacht, nicht als Vorschrift.",
    }


def load_budget(data: dict[str, Any], state: str = "green") -> dict[str, Any] | None:
    """Return how much load today may carry, derived from the ACWR definition.

    The ratio is the 7-day mean load over the 28-day mean. Solving it for
    today's load gives an upper bound: load = 7 x chronic x target minus the
    six days before. The target is tightened when the traffic light is not
    green - which is a choice, not a finding.
    """
    series = daily_load(data)
    if len(series) < 28:
        return None

    loads = [point["load"] for point in series]
    chronic = mean(loads[-28:])
    last_six = sum(loads[-6:])
    if chronic <= 0:
        return None

    targets = {"green": ACWR_HIGH, "amber": 1.0, "red": ACWR_LOW, "unknown": 1.0}
    target = targets.get(state, 1.0)

    def allowed(factor: float) -> int:
        return max(0, round(7 * chronic * factor - last_six))

    return {
        "chronic": round(chronic, 1),
        "last_six_days": round(last_six, 1),
        "target_ratio": target,
        "recommended": allowed(target),
        "steady": allowed(1.0),
        "corridor_top": allowed(ACWR_HIGH),
        "risk_top": allowed(ACWR_RISK),
        "state": state,
    }


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

    NOTHING IS PAIRED. The plan says "SweetSpot 2x20"; the archive holds rides
    with a duration and a load and no label saying which planned session they
    were meant to be. Any automatic pairing would be a claim the system cannot
    back up - the same class as "it would take some 128 sessions" in H, a
    number that sounds more precise than it is. So: ridden against planned,
    and the pairing stays the athlete's job.
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
            "entscheidest du. Das Archiv führt Dauer und Last, kein Etikett; eine "
            "automatische Zuordnung wäre eine Behauptung, die hier niemand belegen kann."
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
        for activity in day["activities"]:
            bucket["load"] += float(activity.get("load") or 0)
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
