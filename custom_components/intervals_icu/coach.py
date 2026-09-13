"""The coach: what to ride next, why, and what it will do.

This module holds no thresholds it made up. Every rule below either comes
from a published source or from the athlete's own measured history, and each
one carries which of the two it is. Where the evidence is thin, the text says
so - a recommendation that hides its own uncertainty is worse than none.

Sources, once, so the rules below can refer to them:

  JAVALOYES  Javaloyes et al. 2019/2020, HRV-guided training in cyclists:
             7-day LnRMSSD inside or above the smallest worthwhile change ->
             hard session; below -> easy or rest. The guided group improved
             peak power, power at VT2 and a 40-min time trial; the fixed-plan
             group did not. Vesterinen 2016 found the same pattern in runners
             with FEWER hard sessions (13.2 vs 17.7).
  DUEKING    Düking et al. 2021, meta-analysis of 8 studies / 198 subjects:
             medium effect on submaximal parameters, small and NOT significant
             on peak performance. So: a useful timing aid, not a guarantee.
  PLEWS      Plews/Buchheit and Altini: 7-day rolling mean against a 60-day
             band; both a fall AND a rise can signal trouble; resting heart
             rate gives the context. "Normal is better than higher."
  ROGERS     Rogers/Gronwald: DFA alpha-1 0.75 marks the aerobic threshold,
             0.5 the anaerobic one. Under fatigue the same external load
             produces LOWER alpha-1 - the metric shifts, which makes it a
             fatigue marker but a poor zone marker on a tired day.
  SEILER     Three-zone model; trained endurance athletes accumulate roughly
             75-80% of sessions below the first threshold.
  FRIEL      Decoupling of 5% or less on a steady aerobic ride means the
             aerobic base carries the duration.
  MUJIKA     Mujika/Padilla and Coyle: up to ~2 weeks off costs 4-7% VO2max,
             mostly through plasma volume - it returns within a few sessions.
             The heart rate at a given submaximal load is elevated meanwhile.
  GABBETT    Acute:chronic workload ratio; a low chronic load followed by a
             sharp acute spike is the pattern associated with trouble. The
             ratio itself is contested (correlational, mathematically coupled).
  RTP        Graded return after a viral infection: build up over days, and
             stop if symptoms return. Systemic infection plus hard training is
             the one combination with a serious downside (myocarditis).
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from statistics import mean, median, pstdev
from typing import Any, NamedTuple

try:  # inside the package (Home Assistant)
    from . import analytics, day_context, derive
    from .const import (
        DECOUPLING_GOOD,
        DURABILITY_EXCLUDED_TYPES,
        DURABILITY_MAX_INTENSITY,
        DURABILITY_VI_FULL,
        DURABILITY_VI_NONE,
        DURABILITY_MIN_WEIGHT_SUM,
        DURABILITY_MIN_WEIGHT_SUM_BLOCK,
        DURABILITY_MIN_SLOPE_T,
        DURABILITY_BLOCK_WEEKS,
        DURABILITY_BINS_KJ,
        DURABILITY_POWER_DAYS,
        DURABILITY_POWER_DAYS_FALLBACK,
        DURABILITY_MIN_POWER_SESSIONS,
        DURABILITY_FUELLING_G_PER_H,
        DURABILITY_MIN_MINUTES,
        MIN_PEERS_TO_RANK_METRIC,
        MIN_SESSIONS_FOR_TILE,
        MIN_SESSIONS_TO_CLAIM_GROUP,
        PEER_CALIPER_STAGES,
        PROGRESSION_FACTOR,
        PROGRESSION_ROUND_MINUTES,
        PROGRESSION_WINDOWS_DAYS,
        RECOVERY_MAX_HARD_DAYS_7,
        RECOVERY_QUIET_DAYS,
    )
except ImportError:  # standalone (test suite loads this file directly)
    import analytics
    import day_context
    import derive
    from const import (
        DECOUPLING_GOOD,
        DURABILITY_EXCLUDED_TYPES,
        DURABILITY_MAX_INTENSITY,
        DURABILITY_VI_FULL,
        DURABILITY_VI_NONE,
        DURABILITY_MIN_WEIGHT_SUM,
        DURABILITY_MIN_WEIGHT_SUM_BLOCK,
        DURABILITY_MIN_SLOPE_T,
        DURABILITY_BLOCK_WEEKS,
        DURABILITY_BINS_KJ,
        DURABILITY_POWER_DAYS,
        DURABILITY_POWER_DAYS_FALLBACK,
        DURABILITY_MIN_POWER_SESSIONS,
        DURABILITY_FUELLING_G_PER_H,
        DURABILITY_MIN_MINUTES,
        MIN_PEERS_TO_RANK_METRIC,
        MIN_SESSIONS_FOR_TILE,
        MIN_SESSIONS_TO_CLAIM_GROUP,
        PEER_CALIPER_STAGES,
        PROGRESSION_FACTOR,
        PROGRESSION_ROUND_MINUTES,
        PROGRESSION_WINDOWS_DAYS,
        RECOVERY_MAX_HARD_DAYS_7,
        RECOVERY_QUIET_DAYS,
    )

# --- thresholds, all of them sourced ------------------------------------------
HRV_DROP_SD = 2.0          # PLEWS: an acute drop of this size is not noise
RHR_RISE_SD = 2.0
RECOVERY_WINDOW = 10       # days a slump keeps colouring the picture
LAYOFF_DAYS = 4            # MUJIKA: below this, nothing measurable is lost
DFA_AEROBIC = 0.75         # ROGERS
DFA_ANAEROBIC = 0.5        # ROGERS
# DECOUPLING_GOOD lives in const.py - it is shown in the panel, so it may exist
# exactly once in the whole house (docs/ausbau.md F4).
SWC_SD = 0.5               # PLEWS/ALTINI: smallest worthwhile change


def _f(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _series(wellness: dict[str, Any], field: str, days: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for day in days:
        value = _f((wellness.get(day) or {}).get(field))
        if value is not None:
            out[day] = value
    return out


def _band(values: list[float]) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    return (mean(values), pstdev(values) if len(values) > 1 else 0.0)


class Band(NamedTuple):
    """A baseline with its provenance, so a fallback can say WHY."""

    base: float
    spread: float
    weighted: bool     # the sum-of-weights rule allowed weighting
    weight_sum: float  # effective days in the window
    labeled: int       # usable values carrying a weight below 1


def _norm_band(raw: list[float], *, log: bool,
               weights: list[float] | None = None) -> Band | None:
    """THE baseline of a wellness signal - the only place it is computed.

    One primitive instead of four hand-rolled copies: `state()`,
    `_z_series()`, `_night_z()` and `_signal_bands()` all call this, so the
    scale (HRV on the log scale, the published ln(rMSSD) comparison), the
    20-value floor, the flat-band rejection AND the day-context weighting
    cannot drift apart again. A guard in test_coach.py checks the callers.

    The weighting rule (docs/ausbau.md B3, level 1 - a STIPULATION):
    weighted mean and spread when at least one day carries a weight below 1
    and the weight sum reaches MIN_WEIGHT_SUM; otherwise the plain band over
    the same values. The unlabelled case delegates to `_band` directly, so
    an archive without labels is BIT-IDENTICAL to the unweighted world - the
    frozen references in test_coach block 30 hang on that. Levels 2 and 3
    never enter here: the judged day's own weight is irrelevant (histories
    exclude it or triggering ignores it), and analytics never calls this.

    Returns the Band on the (possibly log) scale, or None when the history
    is too thin to mean anything.
    """
    if weights is None:
        weights = [1.0] * len(raw)
    pairs = list(zip(raw, weights))
    if log:
        pairs = [(math.log(v), w) for v, w in pairs if v > 0]
    if len(pairs) < 20:
        return None
    values = [v for v, _w in pairs]
    weight_sum = sum(w for _v, w in pairs)
    labeled = sum(1 for _v, w in pairs if w < 1.0)
    if labeled and weight_sum >= day_context.MIN_WEIGHT_SUM:
        base = sum(v * w for v, w in pairs) / weight_sum
        spread = math.sqrt(sum(w * (v - base) ** 2 for v, w in pairs) / weight_sum)
        is_weighted = True
    else:
        base, spread = _band(values)
        is_weighted = False
    if spread <= 0:
        return None
    return Band(base, spread, is_weighted, round(weight_sum, 2), labeled)


def _fallback_note(band: Band | None) -> str | None:
    """Says WHAT is missing when the weighted baseline is not usable yet.

    Fires only when the fallback changes anything - a window without a
    single labelled day computes identically either way, and a hint that
    warns about nothing teaches the reader to ignore hints.
    """
    if band is None or band.weighted or band.labeled == 0:
        return None
    have = f"{band.weight_sum:.1f}".replace(".", ",").removesuffix(",0")
    days = "Tag ist" if band.labeled == 1 else "Tage sind"
    return (f"Basislinie auf ungewichtet zurückgefallen — nur {have} belastbare "
            f"Tage von {int(day_context.MIN_WEIGHT_SUM)} nötigen, "
            f"{band.labeled} {days} etikettiert")


def _z_at(value: float | None, band: Band | None, *,
          log: bool, sign: int = 1) -> float | None:
    """A value's distance from its band, on the band's own scale."""
    if value is None or band is None:
        return None
    if log:
        if value <= 0:
            return None
        value = math.log(value)
    return sign * (value - band.base) / band.spread


# --- state --------------------------------------------------------------------
def state(data: dict[str, Any]) -> dict[str, Any]:
    """Classify today, distinguishing an acute slump from creeping fatigue.

    A single rolling mean cannot tell those apart: after an infection the
    7-day window still carries the slump while the body is already back, and
    the panel would keep saying "red" for days. So the window is read, but the
    most recent days and the resting heart rate get a say.
    """
    wellness = data.get("wellness") or {}
    days = sorted(wellness)
    if len(days) < 21:
        return {"state": "unknown", "label": "zu wenig Historie",
                "detail": "unter drei Wochen Wellness-Daten", "since": None,
                "slump": None, "confidence": "keine", "explained": False,
                "context": None, "baseline_note": None}

    today = days[-1]
    hrv = _series(wellness, "hrv", days)
    rhr = _series(wellness, "restingHR", days) or _series(wellness, "resting_hr", days)

    hrv_days = sorted(hrv)
    base_days = [d for d in hrv_days if d < today][-60:]
    hrv_band = _norm_band([hrv[d] for d in base_days], log=True,
                          weights=[day_context.weight_for(data, d) for d in base_days])
    rhr_base_days = [d for d in sorted(rhr) if d < today][-60:]
    rhr_band = _norm_band([rhr[d] for d in rhr_base_days], log=False,
                          weights=[day_context.weight_for(data, d) for d in rhr_base_days])

    def z_hrv(day: str) -> float | None:
        return _z_at(hrv.get(day), hrv_band, log=True)

    def z_rhr(day: str) -> float | None:
        return _z_at(rhr.get(day), rhr_band, log=False)

    # Day context, attached to every verdict from the SAME bands the verdict
    # was computed against - a second computation path here is exactly the
    # error class this file keeps paying for.
    baseline_note = _fallback_note(hrv_band) or _fallback_note(rhr_band)
    today_entry = day_context.entry_for(data, today)
    today_context = None
    if today_entry:
        today_context = {
            "tag": today_entry.get("tag"),
            "label": day_context.TAGS.get(today_entry.get("tag"), {}).get(
                "label", today_entry.get("tag")),
            "weight": day_context.weight_for(data, today),
        }

    def st(key, label, since, detail, week_z, now_hrv, now_rhr, confidence,
           cause=None, infection=False):
        result = _st(key, label, since, detail, week_z, now_hrv, now_rhr,
                     confidence, cause, infection)
        since_entry = day_context.entry_for(data, since) if since else None
        explained = bool(since_entry and since_entry.get("tag") != "normal"
                         and key in ("slump", "recovering", "rebound"))
        if explained:
            tag_label = day_context.TAGS.get(since_entry.get("tag"), {}).get(
                "label", since_entry.get("tag"))
            result["detail"] = (result["detail"] +
                f" Der Tag tr\u00e4gt das Etikett \u201e{tag_label}\u201c \u2014 "
                "der Ausschlag ist damit benannt: gesehen, erkl\u00e4rt, nicht "
                "weggerechnet. Die Warnung bleibt, denn ausgeschlossen wird "
                "hier nie.")
        result["explained"] = explained
        result["context"] = today_context
        result["baseline_note"] = baseline_note
        return result

    # An acute departure needs more than one lonely number: either BOTH
    # signals leave the band on the same day (the infection pattern), or ONE
    # signal stays out on two consecutive days. A single signal on a single
    # day is what the tension text itself calls noise - the published control
    # compares the 7-day mean, not a lone morning (PLEWS).
    recent = [d for d in sorted(set(hrv) | set(rhr))
              if d >= _shift(today, -(RECOVERY_WINDOW - 1))]
    slump_day = None
    slump_cause = None
    infection = False
    for day in recent:
        zh, zr = z_hrv(day), z_rhr(day)
        hrv_hit = zh is not None and zh <= -HRV_DROP_SD
        rhr_hit = zr is not None and zr >= RHR_RISE_SD
        prev = _shift(day, -1)
        zh_p, zr_p = z_hrv(prev), z_rhr(prev)
        persists = ((hrv_hit and zh_p is not None and zh_p <= -HRV_DROP_SD)
                    or (rhr_hit and zr_p is not None and zr_p >= RHR_RISE_SD))
        both = hrv_hit and rhr_hit
        if both or persists:
            slump_day = day
            infection = infection or both
            slump_cause = ("beide" if both or slump_cause == "beide"
                           else "hrv" if hrv_hit else "ruhepuls")
    last3 = [z_hrv(d) for d in hrv_days[-3:] if z_hrv(d) is not None]
    last3_rhr = [z_rhr(d) for d in sorted(rhr)[-3:] if z_rhr(d) is not None]
    now_hrv = mean(last3) if last3 else None
    now_rhr = mean(last3_rhr) if last3_rhr else None

    # 7-day mean against the 60-day band, the published comparison (PLEWS).
    # The mean of ln(rMSSD), on the same log scale as the band itself.
    week = [math.log(hrv[d]) for d in hrv_days[-7:] if hrv[d] > 0]
    week_z = (((mean(week) - hrv_band.base) / hrv_band.spread)
              if (week and hrv_band is not None) else None)
    swc = 0.5  # half a standard deviation, the usual smallest worthwhile change

    if slump_day is not None:
        days_since = (date.fromisoformat(today) - date.fromisoformat(slump_day)).days
        recovered = (now_hrv is not None and now_hrv >= 0) and (now_rhr is None or now_rhr <= 0)
        cause_text = {
            "beide": "HRV und Ruhepuls sind gemeinsam deutlich außerhalb deines "
                     "Normalbereichs — das Muster eines Infekts.",
            "hrv": "Die HRV liegt den zweiten Tag in Folge deutlich außerhalb deines "
                   "Normalbereichs — ein Einzeltag wäre Rauschen, zwei in Folge sind ein Signal.",
            "ruhepuls": "Der Ruhepuls liegt den zweiten Tag in Folge deutlich über deinem "
                        "Normalbereich — ein Einzeltag wäre Rauschen, zwei in Folge sind ein Signal.",
        }.get(slump_cause, "Deine Werte sind deutlich außerhalb deines Normalbereichs.")
        infection_note = (" Beide Signale waren gleichzeitig extrem — das Muster eines "
                          "Infekts; der Weg zurück ist eine Leiter, keine Rampe.") if infection else ""
        if days_since == 0:
            return st("slump", "Einbruch", slump_day, cause_text,
                       week_z, now_hrv, now_rhr, "hoch", slump_cause, infection)
        if recovered:
            return st("rebound", "Erholung nach Einbruch", slump_day,
                       f"Der Einbruch war vor {days_since} Tagen. Die letzten Tage liegen "
                       "wieder über deiner Basislinie, der Ruhepuls darunter — der Körper "
                       "ist auf dem Rückweg. Das 7-Tage-Mittel hinkt noch nach, weil der "
                       "Einbruch darin steckt." + infection_note,
                       week_z, now_hrv, now_rhr, "mittel", slump_cause, infection)
        return st("recovering", "noch im Einbruch", slump_day,
                   f"Der Einbruch war vor {days_since} Tagen und die Werte sind noch nicht "
                   "zurück auf deiner Basislinie." + infection_note,
                   week_z, now_hrv, now_rhr, "hoch", slump_cause, infection)

    if week_z is None:
        return st("unknown", "keine Einschätzung", None,
                   "Zu wenige HRV-Werte für einen Vergleich.", None, now_hrv, now_rhr, "keine")
    if week_z < -swc:
        return st("strained", "beansprucht", None,
                   "Das 7-Tage-Mittel liegt unter deinem Normalband — nach der Regel von "
                   "Javaloyes ist das ein Tag für Umfang, nicht für Intensität.",
                   week_z, now_hrv, now_rhr, "mittel")
    if week_z > 1.5:
        return st("elevated", "auffällig hoch", None,
                   "Das 7-Tage-Mittel liegt deutlich über dem Normalband. Nach Plews ist "
                   "das nicht automatisch gut: dauerhaft erhöhte Werte können auch "
                   "Erschöpfung anzeigen. Im Zweifel: wie gewohnt trainieren und beobachten.",
                   week_z, now_hrv, now_rhr, "gering")
    return st("ready", "im Normalbereich", None,
               "Das 7-Tage-Mittel liegt in deinem Normalband — nach der Regel von Javaloyes "
               "ist heute ein harter Reiz möglich.",
               week_z, now_hrv, now_rhr, "mittel")


def _st(key, label, since, detail, week_z, now_hrv, now_rhr, confidence,
        cause=None, infection=False):
    return {"state": key, "label": label, "since": since, "detail": detail,
            "week_z": round(week_z, 2) if week_z is not None else None,
            "recent_hrv_z": round(now_hrv, 2) if now_hrv is not None else None,
            "recent_rhr_z": round(now_rhr, 2) if now_rhr is not None else None,
            "confidence": confidence, "cause": cause, "infection_suspected": infection}


def _shift(day: str, delta: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=delta)).isoformat()


# --- anchors: the athlete's own measured intensities ---------------------------
def anchors(data: dict[str, Any]) -> dict[str, Any]:
    """Heart rate and power anchors, measured rather than assumed.

    The aerobic threshold comes from the athlete's own DFA alpha-1 readings
    (ROGERS), not from a percentage of a maximum. Only readings with enough
    samples count, and the median of the last few is used so one bad recording
    cannot move the anchor.
    """
    dfa = data.get("dfa") or {}
    acts = data.get("activities") or {}
    rows = []
    for key, summary in dfa.items():
        if not isinstance(summary, dict):
            continue
        # ONE rule, called - not a fourth copy of it. The old line here read
        # `hr <= 0 and >= 5 samples`, which is neither the physiological floor
        # nor the window count the house agreed on (§7).
        verdict = derive.threshold_verdict(summary)
        if not verdict["hr_usable"]:
            continue
        act = acts.get(key) or {}
        rows.append({"date": str(act.get("start_date_local") or "")[:10],
                     "hr": verdict["hr"],
                     "power": verdict["power"] if verdict["power_usable"] else None})
    rows.sort(key=lambda r: r["date"])
    if len(rows) < 3:
        return {"aerobic_hr": None, "aerobic_power": None, "n": len(rows),
                "trend_power": None, "source": "zu wenige belastbare DFA-Messungen"}

    recent = rows[-5:]
    hr_now = median([r["hr"] for r in recent])
    pw = [r["power"] for r in recent if r["power"]]
    power_now = median(pw) if pw else None

    # ONE "now" in this whole block: the median of the last five. The halves
    # only provide the "before" - an earlier version computed a second "now"
    # from the newest half, and the panel showed two different current values
    # for the same anchor.
    half = len(rows) // 2
    old_pw = [r["power"] for r in rows[:half] if r["power"]]
    old_hr = [r["hr"] for r in rows[:half]]
    trend = None
    if old_pw and old_hr and power_now and hr_now:
        trend = {
            "power_before": round(mean(old_pw)), "power_now": round(power_now),
            "hr_before": round(mean(old_hr)), "hr_now": round(hr_now),
            "power_change_pct": round((power_now - mean(old_pw)) / mean(old_pw) * 100, 1),
            "hr_change": round(hr_now - mean(old_hr), 1),
        }
    return {"aerobic_hr": round(hr_now), "aerobic_power": round(power_now) if power_now else None,
            "n": len(rows), "trend_power": trend,
            "source": "Median der letzten fünf belastbaren DFA-Messungen (Rogers/Gronwald: "
                      "alpha-1 = 0,75 markiert die aerobe Schwelle) — als Trend am eigenen "
                      "Körper brauchbar, als alleinige Verankerung nicht"}


# --- layoff and durability -----------------------------------------------------
def layoff(data: dict[str, Any]) -> dict[str, Any]:
    """Days since the last real session, and what the literature expects."""
    acts = data.get("activities") or {}
    wellness = data.get("wellness") or {}
    days = sorted(wellness)
    today = days[-1] if days else None
    last = None
    for activity in acts.values():
        if (activity.get("moving_time") or 0) < 900:
            continue
        day = str(activity.get("start_date_local") or "")[:10]
        if day and (last is None or day > last):
            last = day
    if not today or not last:
        return {"days": None, "last": last, "phase": None, "note": None}

    gap = (date.fromisoformat(today) - date.fromisoformat(last)).days
    if gap < LAYOFF_DAYS:
        return {"days": gap, "last": last, "phase": None, "note": None}
    if gap <= 14:
        note = ("Bis etwa zwei Wochen Pause kostet vor allem das Plasmavolumen Leistung "
                "(Mujika/Coyle: 4–7 % VO2max, davon der grösste Teil hydraulisch). Der "
                "Puls liegt bei gewohnter Leistung höher, das gibt sich nach wenigen "
                "Einheiten wieder. Nicht mit Trainingsverlust verwechseln.")
    else:
        note = ("Über zwei Wochen Pause geht auch Substanz verloren (Schlagvolumen, "
                "Laktatschwelle, Glykogenspeicher). Der Wiederaufbau dauert länger als "
                "die Pause selbst.")
    return {"days": gap, "last": last, "phase": "wiedereinstieg", "note": note}


def _last_known_weight(data: dict[str, Any]) -> dict[str, Any] | None:
    """Return the newest wellness weight with the day it was measured.

    The day travels with the value on purpose: the kJ/kg conversion is a side
    note in the explanation, and a side note that silently keeps computing with
    a weight from two years ago is worse than none.
    """
    best_day, best_value = None, None
    for day, row in (data.get("wellness") or {}).items():
        if not isinstance(row, dict):
            continue
        value = _f(row.get("weight"))
        if value and (best_day is None or str(day) > best_day):
            best_day, best_value = str(day), value
    if best_day is None:
        return None
    return {"kg": round(best_value, 1), "day": best_day}


def _weighted_line(points: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Weighted least squares of decoupling over work, with the slope's error.

    The weights come from steadiness (docs/ausbau.md G3), so the fit leans on
    the rides that were actually pedalled evenly instead of pretending a wavy
    group ride says as much as a steady one. The standard error travels with
    the slope because a slope alone cannot be read: on this athlete's archive
    it is +2.9 % per 1000 kJ with an error of 2.2, which is no slope at all.
    """
    live = [p for p in points if p["w"] > 0]
    w_sum = sum(p["w"] for p in points)
    if len(live) < 3 or w_sum <= 0:
        return None
    mean_x = sum(p["w"] * p["kj"] for p in points) / w_sum
    mean_y = sum(p["w"] * p["dec"] for p in points) / w_sum
    spread = sum(p["w"] * (p["kj"] - mean_x) ** 2 for p in points)
    if spread <= 0:
        return None
    slope = sum(p["w"] * (p["kj"] - mean_x) * (p["dec"] - mean_y) for p in points) / spread
    intercept = mean_y - slope * mean_x
    resid = sum(p["w"] * (p["dec"] - intercept - slope * p["kj"]) ** 2 for p in points)
    error = math.sqrt((resid / (len(live) - 2)) / spread)
    # A residual-free fit is perfectly determined, not unusable - it happens in
    # fixtures, never in an archive, and returning None here would have made the
    # cleanest possible relationship read as "too thin".
    determined = abs(slope) / error if error > 0 else (math.inf if slope else 0.0)
    return {
        "a": intercept, "b": slope, "se": error, "t": determined,
        "w_sum": w_sum, "n": len(live),
    }


def _tipping_kj(fit: dict[str, Any], mark: float) -> float | None:
    """Where the fitted line crosses the mark. None when it never does."""
    if fit["b"] <= 0:
        return None
    crossing = (mark - fit["a"]) / fit["b"]
    return crossing if crossing > 0 else None


def _conversion_power(points: list[dict[str, Any]], newest: date) -> dict[str, Any] | None:
    """Median power of the RECENT qualifying rides, with the window it used.

    Not the median over the whole pool: that spans a season of progression (61
    to 151 W on the live archive) and would turn work into time with a figure
    from last winter. Too few rides in the near window and it widens - visibly,
    never silently (docs/ausbau.md G2).
    """
    for days in (DURABILITY_POWER_DAYS, DURABILITY_POWER_DAYS_FALLBACK):
        cutoff = newest - timedelta(days=days)
        watts = [p["watts"] for p in points if p["day"] >= cutoff and p["watts"]]
        if len(watts) >= DURABILITY_MIN_POWER_SESSIONS:
            return {"watts": round(median(watts)), "days": days, "n": len(watts)}
    return None


def _bin_medians(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Median decoupling per work band - a DESCRIPTION, never a forecast.

    It is what the archive says most plainly today: the medians rise monotonic
    across the bands while the fitted slope cannot be told from zero. Bands
    under MIN_SESSIONS_TO_CLAIM_GROUP carry their count but no median, the same
    rule the two groups obeyed in 0.39.0.
    """
    edges = [0.0, *DURABILITY_BINS_KJ, float("inf")]
    bands = []
    for low, high in zip(edges, edges[1:]):
        inside = [p for p in points if low <= p["kj"] < high]
        thin = len(inside) < MIN_SESSIONS_TO_CLAIM_GROUP
        bands.append({
            "from_kj": round(low),
            "to_kj": None if high == float("inf") else round(high),
            "n": len(inside),
            "w": round(sum(p["w"] for p in inside), 1),
            "median": None if (thin or not inside) else round(median([p["dec"] for p in inside]), 1),
            "thin": thin,
        })
    return bands


def _season_blocks(points: list[dict[str, Any]], mark: float) -> list[dict[str, Any]]:
    """The tipping point per season block - the athlete's actual question.

    All three honesty rules apply PER BLOCK, and "the stock" is the block, not
    the archive: a block may not extrapolate past its own longest ride, may not
    claim a slope it cannot distinguish from zero, and may not speak below its
    own minimum weight. The live archive shows why all three are needed at
    once - a four-ride block came out at |t| 3.3 and a tipping point of 640 kJ.
    An empty block stays empty and is NOT interpolated.
    """
    if not points:
        return []
    newest = max(p["day"] for p in points)
    span = DURABILITY_BLOCK_WEEKS * 7
    grouped: dict[int, list[dict[str, Any]]] = {}
    for point in points:
        grouped.setdefault((newest - point["day"]).days // span, []).append(point)
    blocks = []
    for index in sorted(grouped, reverse=True):
        inside = grouped[index]
        start = newest - timedelta(days=span * (index + 1) - 1)
        w_sum = sum(p["w"] for p in inside)
        block = {
            "start": max(start, min(p["day"] for p in inside)).isoformat(),
            "end": min(newest, newest - timedelta(days=span * index)).isoformat(),
            "n": len(inside), "w": round(w_sum, 1),
            "max_kj": round(max(p["kj"] for p in inside)),
            "tipping_kj": None, "reason": None,
            # What the block is WAITING for. A field of dashes that does not say
            # when it will show something is a field one stops reading.
            "need_w": None, "need_n": None, "slope_t": None,
        }
        fit = _weighted_line(inside)
        crossing = _tipping_kj(fit, mark) if fit else None
        if fit is not None:
            block["slope_t"] = round(fit["t"], 2)
        if w_sum < DURABILITY_MIN_WEIGHT_SUM_BLOCK:
            block["reason"] = "thin"
            block["need_w"] = round(DURABILITY_MIN_WEIGHT_SUM_BLOCK - w_sum, 1)
        elif fit is None or fit["t"] < DURABILITY_MIN_SLOPE_T:
            block["reason"] = "flat"
            if fit is not None and fit["t"] > 0:
                block["need_n"] = max(
                    len(inside) + 1,
                    math.ceil(len(inside) * (DURABILITY_MIN_SLOPE_T / fit["t"]) ** 2),
                )
        elif crossing is None or crossing > max(p["kj"] for p in inside):
            block["reason"] = "beyond"
        else:
            block["tipping_kj"] = round(crossing)
        blocks.append(block)
    return blocks


def _archive_today(data: dict[str, Any], fallback: date) -> date:
    """The archive's own clock, not the machine's.

    `layoff()` already reads "today" off the newest wellness day, and the
    progression window has to agree with it: two clocks in one module is the
    same error class as two truths about one threshold. Wellness arrives daily
    from the watch, so it keeps running when the athlete does not - which is
    exactly what makes the 30-day window able to run empty at all.
    """
    days = sorted(data.get("wellness") or {})
    if days:
        try:
            return date.fromisoformat(days[-1])
        except ValueError:
            pass
    return fallback


def _progression(points: list[dict[str, Any]], today: date) -> dict[str, Any] | None:
    """The head of the tile: what is demonstrated, what is recent, what is next.

    The first line is DEMONSTRATED ability, not an estimated ceiling: it is the
    longest steady ride in the pool, with that ride's OWN average power. The
    pool median from `_conversion_power()` must never appear here - a figure
    borrowed from another calculation inside a line that says "demonstrated"
    is the same mistake as the amateur yardstick in G6, one floor down.

    Longest means longest BY TIME, and the tile's own axis is work, so the two
    superlatives can point at different rides. They are labelled apart for that
    reason. On the live archive of 13.09.2026 they happen to be the same ride -
    which is precisely why the fixture must force them apart.

    Everything here is drawn from the SAME list, so "recent <= demonstrated"
    follows from the data structure rather than from a test standing guard.
    """
    if not points:
        return None
    longest = max(points, key=lambda p: (p["minutes"], p["kj"]))
    demonstrated = {
        "minutes": longest["minutes"], "watts": round(longest["watts"]) if longest["watts"] else None,
        "kj": round(longest["kj"]), "date": longest["date"], "id": longest["id"],
    }

    recent = None
    for days in PROGRESSION_WINDOWS_DAYS:
        inside = (points if days is None
                  else [p for p in points if 0 <= (today - p["day"]).days < days])
        if not inside:
            continue
        best = max(inside, key=lambda p: (p["minutes"], p["kj"]))
        recent = {
            "minutes": best["minutes"], "watts": round(best["watts"]) if best["watts"] else None,
            "kj": round(best["kj"]), "date": best["date"], "id": best["id"],
            "days": days, "n": len(inside), "widened": days != PROGRESSION_WINDOWS_DAYS[0],
        }
        break
    if recent is None:  # unreachable while points is non-empty - the last rung is the whole stock
        return None

    step = PROGRESSION_ROUND_MINUTES
    # Rounded HERE, so the printed minutes are the minutes one lands on when
    # multiplying the printed reference by the printed factor.
    next_minutes = int(round(recent["minutes"] * PROGRESSION_FACTOR / step) * step)
    return {
        "demonstrated": demonstrated,
        "recent": recent,
        "next_minutes": next_minutes,
        # NOT a special case: this is the rule whenever a single outlier long
        # ride sits more than the factor above the recent best - which is most
        # of the year for most people. On the live archive it is true today
        # with a well-filled window (260 against 230 minutes).
        "below_demonstrated": next_minutes < demonstrated["minutes"],
        "factor": PROGRESSION_FACTOR,
        "round_minutes": step,
        "window_days": PROGRESSION_WINDOWS_DAYS[0],
        "windows_days": [d for d in PROGRESSION_WINDOWS_DAYS if d is not None],
        "today": today.isoformat(),
    }


def durability(data: dict[str, Any], min_minutes: int = DURABILITY_MIN_MINUTES) -> dict[str, Any] | None:
    """How long the aerobic base holds as WORK accumulates - measured, not assumed.

    Indexed by accumulated work, not by duration: that axis is what the
    literature supports (Maunder 2021; Spragg splits the power profile at 2000
    kJ) and on this athlete's archive the duration split hid the effect
    entirely. What 0.39.0 still got wrong was the SHAPE - two groups either side
    of one setting answer "is it different above 800 kJ", while the question on
    the heading is "how long until it tips". That is a curve over work, so this
    returns the cloud, a weighted fit with its error, the binned medians and the
    per-block course - and refuses a lead figure under any of three rules
    (docs/ausbau.md G1-G4).
    """
    points: list[dict[str, Any]] = []
    dropped = {"short": 0, "intense": 0, "variable": 0, "indoor": 0, "no_power": 0,
               "no_activity": 0, "no_decoupling": 0, "no_work": 0}
    for activity in (data.get("activities") or {}).values():
        reason = derive.steady_endurance_reason(activity, min_minutes)
        if reason is not None:
            dropped[reason] += 1
            continue
        decoupling = _f(activity.get("decoupling"))
        if decoupling is None:
            dropped["no_decoupling"] += 1
            continue
        work = _f(activity.get("icu_joules"))
        if not work:
            dropped["no_work"] += 1
            continue
        day = str(activity.get("start_date_local") or "")[:10]
        points.append({
            "kj": work / 1000.0,
            "dec": decoupling,
            # Duration and the ride's OWN power travel with the point from here
            # on. Both already sat in the archive; until 0.40.0 the emitted
            # point dropped them, which is why H1 could not be drawn at all.
            # Carrying them means the head line and the cloud come out of one
            # list - the "same pool" assurance follows from the structure.
            "minutes": round((activity.get("moving_time") or 0) / 60),
            "vi": derive.variability_index(activity),
            "w": derive.steady_weight(activity),
            "watts": _f(activity.get("icu_average_watts")),
            "day": date.fromisoformat(day) if len(day) == 10 else None,
            "date": day,
            "id": activity.get("id"),
        })
    points = [p for p in points if p["day"] is not None]
    if len(points) < MIN_SESSIONS_FOR_TILE:
        return None
    points.sort(key=lambda p: p["kj"])

    weight_sum = sum(p["w"] for p in points)
    max_kj = max(p["kj"] for p in points)
    fit = _weighted_line(points)
    crossing = _tipping_kj(fit, DECOUPLING_GOOD) if fit else None
    newest = max(p["day"] for p in points)
    power = _conversion_power(points, newest)

    # The three honesty rules, in the order in which they disqualify. Each one
    # produces an ANSWER, not a gap: "no claim possible" and "the direction is
    # there but the scatter is too wide" are different findings, and reading the
    # second as the first would be reading "fine" into "unknown".
    blocked = None
    if weight_sum < DURABILITY_MIN_WEIGHT_SUM or fit is None:
        blocked = "thin"
    elif fit["t"] < DURABILITY_MIN_SLOPE_T:
        blocked = "flat"
    elif crossing is None or crossing > max_kj:
        blocked = "beyond"

    tipping = None if blocked else round(crossing / 10.0) * 10
    # Rounded FIRST, then converted. Whoever divides the printed kJ by the
    # printed watts has to land on the printed hours (the F3 rule).
    hours = (tipping * 1000.0 / (power["watts"] * 3600.0)) if (tipping and power) else None

    if blocked == "thin":
        headline = (
            f"Noch keine Aussage möglich: die ausgewerteten Einheiten tragen zusammen "
            f"{round(weight_sum, 1):.1f} von {round(DURABILITY_MIN_WEIGHT_SUM):.0f} nötigen Gewichten."
        )
    elif blocked == "flat":
        direction = (
            "Die Richtung stimmt — die Entkopplung steigt mit der Arbeit —, aber die "
            "Streuung ist zu groß für eine Aussage."
            if fit["b"] > 0 else
            "In deinen Daten steigt die Entkopplung mit der Arbeit nicht — aber die "
            "Streuung ist zu groß, um auch das zu behaupten."
        )
        headline = direction
    elif blocked == "beyond":
        headline = (
            f"Bis {round(max_kj):.0f} kJ — deine arbeitsreichste ausgewertete Fahrt — "
            f"bleibst du unter der {DECOUPLING_GOOD:.0f}-%-Marke. Weiter reichen deine Daten nicht."
        )
    else:
        when = (
            f" — rund {int(hours)} h {int(round((hours - int(hours)) * 60)):02d} bei deinen "
            f"{power['watts']:.0f} W der letzten {round(power['days'] / 30):.0f} Monate"
            if hours else ""
        )
        headline = f"Bis etwa {tipping:.0f} kJ bleibst du unter der {DECOUPLING_GOOD:.0f}-%-Marke{when}."

    # What would close the gap. This is the only place in the panel that can say
    # which ride advances the measurement: the error shrinks with the weight AND
    # with the spread of the work, so one long ride moves it further than five
    # short ones.
    needed = None
    if blocked == "flat" and fit["t"] > 0:
        needed = max(len(points) + 1, math.ceil(len(points) * (DURABILITY_MIN_SLOPE_T / fit["t"]) ** 2))

    return {
        "n": len(points),
        "w_sum": round(weight_sum, 1),
        "n_full": sum(1 for p in points if p["w"] >= 0.999),
        "n_partial": sum(1 for p in points if 0 < p["w"] < 0.999),
        "n_zero": sum(1 for p in points if p["w"] <= 0),
        "points": [
            {"kj": round(p["kj"]), "dec": round(p["dec"], 1), "w": round(p["w"], 2),
             "vi": round(p["vi"], 3) if p["vi"] is not None else None, "date": p["date"], "id": p["id"],
             "minutes": p["minutes"], "watts": round(p["watts"]) if p["watts"] else None}
            for p in points
        ],
        "max_kj": round(max_kj),
        "slope": round(fit["b"] * 1000, 2) if fit else None,
        "slope_se": round(fit["se"] * 1000, 2) if fit else None,
        "slope_t": round(fit["t"], 2) if fit else None,
        "blocked": blocked,
        "tipping_kj": tipping,
        "tipping_hours": round(hours, 2) if hours else None,
        "power": power,
        "power_pool": round(median([p["watts"] for p in points if p["watts"]])) if any(p["watts"] for p in points) else None,
        "needed_sessions": needed,
        "bins": _bin_medians(points),
        "blocks": _season_blocks(points, DECOUPLING_GOOD),
        "headline": headline,
        # The head (docs/ausbau.md H1/H2). It stands there from the first ride,
        # it never disappears because the statistics do not carry, and it never
        # comes out of a model - which is why it is computed before any of the
        # three honesty rules above can block anything.
        "progression": _progression(points, _archive_today(data, newest)),
        # Everything the panel prints. None of these may appear as a literal in
        # the frontend - there is a source guard against exactly that.
        "decoupling_good": DECOUPLING_GOOD,
        "min_minutes": min_minutes,
        "max_intensity": DURABILITY_MAX_INTENSITY,
        "vi_full": DURABILITY_VI_FULL,
        "vi_none": DURABILITY_VI_NONE,
        "min_weight_sum": DURABILITY_MIN_WEIGHT_SUM,
        "min_weight_sum_block": DURABILITY_MIN_WEIGHT_SUM_BLOCK,
        "min_slope_t": DURABILITY_MIN_SLOPE_T,
        "block_weeks": DURABILITY_BLOCK_WEEKS,
        "bins_kj": list(DURABILITY_BINS_KJ),
        "power_days": DURABILITY_POWER_DAYS,
        "power_days_fallback": DURABILITY_POWER_DAYS_FALLBACK,
        "fuelling_g_per_h": DURABILITY_FUELLING_G_PER_H,
        "min_per_group": MIN_SESSIONS_TO_CLAIM_GROUP,
        "min_sessions": MIN_SESSIONS_FOR_TILE,
        "excluded_types": list(DURABILITY_EXCLUDED_TYPES),
        "dropped": dropped,
        "weight": _last_known_weight(data),
        "source": (
            "Setzung: die 5-%-Marke ist eine Trainerfaustregel (Friel), keine "
            "Studiengrenze. Belegt ist das Phänomen dahinter — der kardiovaskuläre "
            "Drift — und dass es stark von Hitze, Flüssigkeit und Umgebung abhängt. "
            "Belegt ist auch die Achse: Durability wird über angesammelte Arbeit "
            "gemessen (Maunder 2021; Spragg trennt bei 2000 kJ). Die Gewichtsgrenzen, "
            "die Mindestbelegung und das Steigungskriterium sind Setzungen."
        ),
    }


def pattern_after_breaks(data: dict[str, Any]) -> dict[str, Any] | None:
    """What the athlete has actually DONE after previous breaks.

    Not advice - an observation about their own habit, which is the part a
    plan usually fails on.
    """
    acts = sorted(
        ((str(a.get("start_date_local") or "")[:10], a) for a in (data.get("activities") or {}).values()
         if (a.get("moving_time") or 0) >= 1800),
        key=lambda pair: pair[0],
    )
    firsts: list[float] = []
    for index in range(1, len(acts)):
        prev_day, _ = acts[index - 1]
        day, activity = acts[index]
        if not prev_day or not day:
            continue
        gap = (date.fromisoformat(day) - date.fromisoformat(prev_day)).days
        intensity = _f(activity.get("icu_intensity"))
        if gap >= LAYOFF_DAYS and intensity is not None:
            firsts.append(intensity)
    if len(firsts) < 3:
        return None
    return {"n": len(firsts), "median_intensity": round(median(firsts)),
            "hard_share": round(sum(1 for value in firsts if value >= 75) / len(firsts) * 100)}


# --- the assessment: one source for "how is this athlete today" ----------------
# There used to be a second recommender here: its own session menu, its own
# heart-rate windows, its own load estimate and a seven-day ladder. The panel
# never rendered most of it, and where it overlapped with workouts.suggest()
# the two could quietly disagree - the error class that already cost 0.11.0
# and 0.27.0 a release each. Session choice now lives in ONE place
# (workouts.suggest); this module only answers what state the athlete is in
# and why, and hands over the measured anchors.

def _hard_days_recent(data: dict[str, Any], days: int) -> int:
    wellness = data.get("wellness") or {}
    order = sorted(wellness)
    if not order:
        return 0
    cutoff = _shift(order[-1], -(days - 1))
    hard = set()
    for activity in (data.get("activities") or {}).values():
        day = str(activity.get("start_date_local") or "")[:10]
        if day >= cutoff and (_f(activity.get("icu_intensity")) or 0) >= 80:
            hard.add(day)
    return len(hard)


def recovery_offered(data: dict[str, Any]) -> dict[str, Any]:
    """Whether the last days actually offered recovery - ONE place, a SETTING.

    The stimulus grade (functional overreaching) needs the statement "the last
    days offered recovery". Without a rule nailed down in one place it would
    grow into a SECOND state rule through the back door - the error class that
    cost 0.11.0 and 0.27.0 a release each.

    Three conditions, all from figures that already exist:

      * the state is `ready` (coach.state - HRV and resting HR against the
        athlete's own band),
      * no hard day in the last seven (the same counter the session list
        uses),
      * the load of the last RECOVERY_QUIET_DAYS days below the chronic daily
        mean (the same daily series the load budget is solved from).

    The daily load comes from analytics.daily_load, not from a second walk
    over the activities: two ways to the same number is exactly what this
    package forbids.

    The honest part travels with it: the THRESHOLDS are chosen, not measured.
    The ingredients are sourced, their combination into this particular rule
    is a setting - the same admission the load budget makes about its target
    ratio per traffic light.
    """
    st = state(data)
    hard = _hard_days_recent(data, 7)

    series = analytics.daily_load(data)
    loads = [point.get("load") or 0.0 for point in series]
    chronic = mean(loads[-28:]) if len(loads) >= 28 else None
    recent = loads[-RECOVERY_QUIET_DAYS:] if len(loads) >= RECOVERY_QUIET_DAYS else []
    recent_mean = mean(recent) if recent else None

    quiet = (chronic is not None and recent_mean is not None and recent_mean < chronic)
    offered = bool(st.get("state") == "ready"
                   and hard <= RECOVERY_MAX_HARD_DAYS_7
                   and quiet)

    missing: list[str] = []
    if st.get("state") != "ready":
        missing.append(f"Zustand {st.get('label') or st.get('state')}, nicht unauffällig")
    if hard > RECOVERY_MAX_HARD_DAYS_7:
        missing.append(f"{hard} harter Tag in den letzten sieben" if hard == 1
                       else f"{hard} harte Tage in den letzten sieben")
    if chronic is None or recent_mean is None:
        missing.append("zu wenige Tage für einen chronischen Vergleich")
    elif not quiet:
        missing.append(f"die letzten {RECOVERY_QUIET_DAYS} Tage lagen mit "
                       f"{round(recent_mean)} über dem chronischen Schnitt von {round(chronic)}")

    return {
        "offered": offered,
        "state": st.get("state"),
        "hard_days_last_7": hard,
        "quiet_days": RECOVERY_QUIET_DAYS,
        "max_hard_days_7": RECOVERY_MAX_HARD_DAYS_7,
        "recent_daily_load": None if recent_mean is None else round(recent_mean, 1),
        "chronic_daily_load": None if chronic is None else round(chronic, 1),
        "missing": missing,
        "note": (
            f"Erholung gilt als geboten, wenn der Zustand unauffällig ist, in den letzten "
            f"sieben Tagen höchstens {RECOVERY_MAX_HARD_DAYS_7} harte Tage liegen und die "
            f"Last der letzten {RECOVERY_QUIET_DAYS} Tage unter deinem chronischen "
            f"Tagesschnitt bleibt. Die Bestandteile sind belegt, diese Schwellen sind "
            f"gewählt — eine Setzung, keine Messung."
        ),
    }


def _trained_today(data: dict[str, Any]) -> bool:
    """Whether a real session (>= 15 min) is already on today's date."""
    wellness = data.get("wellness") or {}
    order = sorted(wellness)
    if not order:
        return False
    today = order[-1]
    for activity in (data.get("activities") or {}).values():
        if str(activity.get("start_date_local") or "")[:10] != today:
            continue
        if (activity.get("moving_time") or 0) >= 900:
            return True
    return False


def assessment(data: dict[str, Any]) -> dict[str, Any]:
    """Everything that describes TODAY, with reasons and warnings - no session.

    The reasons say why the state is what it is, each with its source. The
    warnings are the safety-relevant part: they exist so the panel can show
    them, and a payload that carries a warning nowhere visible is a bug, not
    a style choice (see test_panel_fixes: warnings must reach the DOM).
    """
    st = state(data)
    lay = layoff(data)
    anc = anchors(data)
    dur = durability(data)
    habit = pattern_after_breaks(data)
    hard_recent = _hard_days_recent(data, 7)

    reasons: list[dict[str, str]] = []
    warnings: list[str] = []

    if st["state"] in ("slump", "recovering", "rebound", "strained", "ready", "elevated"):
        source = {"slump": "Plews/Altini", "recovering": "Plews/Altini",
                  "rebound": "Plews", "strained": "Javaloyes",
                  "ready": "Javaloyes", "elevated": "Plews"}[st["state"]]
        reasons.append({"weil": st["label"], "quelle": source, "text": st["detail"]})

    if st.get("infection_suspected") and st["state"] in ("slump", "recovering", "rebound"):
        warnings.append(
            "Beide Signale schlugen gemeinsam aus — das Muster eines Infekts. Der Weg "
            "zurück ist eine Leiter: mehrere lockere Einheiten, die nächste Stufe erst, "
            "wenn dabei keine Symptome zurückkehren. Faustregel aus der Return-to-Sport-"
            "Praxis (eine Konvention, keine Studienregel): Symptome nur oberhalb des "
            "Halses — locker fahren möglich; Fieber, Husten oder Gliederschmerzen — Pause.")

    if lay.get("phase") == "wiedereinstieg":
        reasons.append({"weil": f"{lay['days']} Tage ohne Einheit",
                        "quelle": "Mujika/Coyle; Rückkehr nach Infekt",
                        "text": lay["note"] or ""})
        warnings.append("Nach einem Infekt gilt: stufenweise aufbauen und bei "
                        "wiederkehrenden Symptomen abbrechen. Systemische Infektion plus "
                        "harte Belastung ist die eine Kombination mit ernstem Risiko.")
        if habit and habit["hard_share"] >= 50:
            warnings.append(
                f"Dein eigenes Muster: nach {habit['n']} Pausen lag die erste Einheit im "
                f"Median bei {habit['median_intensity']} % Intensität, "
                f"{habit['hard_share']} % davon waren hart. Genau dieser Sprung von wenig "
                "chronischer auf hohe akute Last ist das Muster, das Gabbett als riskant "
                "beschreibt.")

    if st["state"] in ("ready", "rebound", "elevated") and hard_recent >= 2:
        reasons.append({"weil": f"{hard_recent} harte Tage in den letzten sieben",
                        "quelle": "Seiler",
                        "text": "Im Dreizonenmodell tragen 75–80 % der Einheiten den "
                                "lockeren Bereich. Zwei harte Tage in einer Woche sind "
                                "die übliche Obergrenze — heute spricht das für Umfang."})

    return {
        "state": st,
        "layoff": lay,
        "anchors": anc,
        "durability": dur,
        "habit": habit,
        "hard_days_last_7": hard_recent,
        "trained_today": _trained_today(data),
        "reasons": reasons,
        "warnings": warnings,
    }


def coach(data: dict[str, Any]) -> dict[str, Any]:
    """Everything the trainer view needs, in one payload - and only one voice.

    The session list itself comes from intervals_icu/workouts; this payload
    deliberately carries no second recommendation next to it.
    """
    out = assessment(data)
    out["evidence"] = {
        "rule": "Javaloyes 2019/2020, Vesterinen 2016 — HRV-gesteuerte Steuerung: "
                "harte Einheit nur, wenn das 7-Tage-Mittel im oder über dem Normalband liegt.",
        "limit": "Düking 2021, Metaanalyse über 8 Studien und 198 Teilnehmer: mittlerer "
                 "Effekt auf submaximale Werte, kleiner und nicht signifikanter Effekt "
                 "auf die Spitzenleistung. Dafür weniger Non-Responder als unter festem "
                 "Plan (Manresa-Rocamora 2021) — eine Zeitwahl-Hilfe, keine Garantie.",
        "own_data": "Die Schwellen stammen aus deinen eigenen DFA-Messungen, nicht aus "
                    "Prozenten einer Maximalherzfrequenz.",
    }
    return out


# --- the signal matrix ---------------------------------------------------------
# Seven signals in seven different units cannot share an axis. Expressed as
# distance from the athlete's own baseline in standard deviations they can:
# zero means "your normal", -2 means two spreads below it. That is what makes
# the stacked view readable at all, and it is the same normalisation the
# smallest-worthwhile-change logic already uses (PLEWS).
SIGNALS: dict[str, dict[str, Any]] = {
    "hrv": {
        "label": "Herzratenvariabilität", "unit": "ms", "field": "hrv", "sign": 1, "log": True,
        "read": "Höher als deine Basislinie heißt meist erholt. Aber nicht grenzenlos: "
                "dauerhaft erhöhte Werte können auch Erschöpfung anzeigen.",
        "source": "Plews/Buchheit und Altini: 7-Tage-Mittel gegen ein 60-Tage-Band, "
                  "Schwelle ist die kleinste bedeutsame Änderung (0,5 SD). Deine Werte "
                  "stammen aus der Nachtmessung der Uhr, nicht aus der validierten "
                  "Morgenmessung im Liegen — als Trend brauchbar, als Absolutwert nicht.",
    },
    "rhr": {
        "label": "Ruhepuls", "unit": "bpm", "field": "restingHR", "sign": -1, "log": False,
        "read": "Niedriger ist besser, deshalb ist die Kurve gespiegelt: oben heißt immer "
                "günstig. Der Ruhepuls schwankt von Tag zu Tag weniger als die HRV und "
                "ordnet sie ein.",
        "source": "Der Ruhepuls gilt als niederschwelliger Zusatzindikator; er ersetzt die "
                  "HRV nicht, sondern ergänzt sie. Bei einem Infekt schlägt er oft "
                  "deutlicher aus als die HRV.",
    },
    "sleep": {
        "label": "Schlaf", "unit": "h", "field": "sleepSecs", "sign": 1, "log": False,
        "scale": 1 / 3600,
        "read": "Ein einzelner kurzer Schlaf sagt wenig; mehrere hintereinander sind ein "
                "Signal. Auffällig lange Nächte nach einem Einbruch sind Erholung.",
        "source": "Schlafdauer aus der Uhr geschätzt. Die Stadien-Erkennung von Wearables "
                  "ist ungenau, die Dauer selbst ist brauchbar.",
    },
    "form": {
        "label": "Form (TSB)", "unit": "", "field": "form", "sign": 1, "log": False,
        "read": "Fitness minus Ermüdung. Positiv heißt ausgeruht, stark negativ heißt "
                "belastet — beides ist weder gut noch schlecht, sondern eine Phase.",
        "source": "Joe Friel; Intervals rechnet die Zonen relativ zur Fitness. Faustregel, "
                  "keine Wissenschaft — sagt der Entwickler selbst.",
    },
}

LOAD_SIGNALS = {
    "acwr": {
        "label": "Akut zu chronisch", "unit": "",
        "read": "Verhältnis der letzten 7 zu den letzten 28 Tagen. Im Korridor 0,8–1,3 "
                "unauffällig, ab 1,5 erhöht.",
        "source": "Gabbett/Blanch. Umstritten: korrelative Belege, mathematisch gekoppelt, "
                  "eine formelle Richtigstellung wurde beantragt, eine randomisierte Studie "
                  "fand keinen Nutzen. Als Indikator lesen, nie als Urteil.",
    },
    "load": {
        "label": "Tageslast", "unit": "",
        "read": "Die Balken unten. Ihre Farbe zeigt, in welchen Bereichen die Einheit "
                "gefahren wurde — gemessen an DFA alpha-1, nicht an geplanten Zonen.",
        "source": "Rogers/Gronwald: alpha-1 über 0,75 aerob, 0,5–0,75 Übergang, "
                  "darunter anaerob.",
    },
}


def _z_series(values: dict[str, float], days: list[str], window: int = 60,
              log: bool = False, sign: int = 1,
              weights: dict[str, float] | None = None) -> dict[str, float]:
    """Distance from a trailing baseline, in standard deviations.

    The baseline trails the day it judges, so today is never part of its own
    normal - otherwise a slow drift would erase itself.
    """
    out: dict[str, float] = {}
    ordered = [d for d in days if d in values]
    for index, day in enumerate(ordered):
        history = ordered[max(0, index - window):index]
        band = _norm_band([values[d] for d in history], log=log,
                          weights=[(weights or {}).get(d, 1.0) for d in history])
        z = _z_at(values[day], band, log=log, sign=sign)
        if z is not None:
            out[day] = z
    return out


def state_series(data: dict[str, Any]) -> list[dict[str, str]]:
    """The state for every past day, so the chart can be banded by it.

    Same rules as `state`, applied day by day: a slump is an acute departure,
    and it keeps colouring the following days until the recent values are back.
    """
    wellness = data.get("wellness") or {}
    days = sorted(wellness)
    hrv = _series(wellness, "hrv", days)
    rhr = _series(wellness, "restingHR", days)
    ctx_w = {d: day_context.weight_for(data, d) for d in days}
    z_hrv = _z_series(hrv, days, log=True, sign=1, weights=ctx_w)
    z_rhr = _z_series(rhr, days, sign=1, weights=ctx_w)  # unsigned here: a RISE is the warning

    def _tag(day: str) -> str | None:
        entry = day_context.entry_for(data, day)
        return entry.get("tag") if entry else None

    def _row(day: str, state: str, explained: bool = False) -> dict[str, Any]:
        row: dict[str, Any] = {"date": day, "state": state}
        tag = _tag(day)
        if tag:
            row["context"] = tag
        if explained:
            # level 2 (docs/ausbau.md B3): the day still triggered - it is
            # SEEN and NAMED, never computed away. The flag is information
            # for the reader, not an input to any rule.
            row["explained"] = True
        return row

    out: list[dict[str, Any]] = []
    slump_day: str | None = None
    slump_explained = False
    for day in days:
        zh, zr = z_hrv.get(day), z_rhr.get(day)
        if zh is None and zr is None:
            out.append(_row(day, "unknown"))
            continue
        hrv_hit = zh is not None and zh <= -HRV_DROP_SD
        rhr_hit = zr is not None and zr >= RHR_RISE_SD
        prev = _shift(day, -1)
        persists = ((hrv_hit and z_hrv.get(prev) is not None and z_hrv[prev] <= -HRV_DROP_SD)
                    or (rhr_hit and z_rhr.get(prev) is not None and z_rhr[prev] >= RHR_RISE_SD))
        acute = (hrv_hit and rhr_hit) or persists
        if acute:
            slump_day = day
            slump_explained = _tag(day) not in (None, "normal")
            out.append(_row(day, "slump", explained=slump_explained))
            continue
        if slump_day is not None:
            since = (date.fromisoformat(day) - date.fromisoformat(slump_day)).days
            if since > RECOVERY_WINDOW:
                slump_day = None
                slump_explained = False
            else:
                # Same rule as state(): judge the recovery on the mean of the
                # last three days, not on one day. A single dip below the
                # baseline is noise, and the bands in the chart have to say
                # exactly what the trainer view says.
                window = [d for d in days if d <= day][-3:]
                hs = [z_hrv[d] for d in window if d in z_hrv]
                rs = [z_rhr[d] for d in window if d in z_rhr]
                back = ((not hs or mean(hs) >= 0) and (not rs or mean(rs) <= 0))
                out.append(_row(day, "rebound" if back else "recovering",
                                explained=slump_explained))
                continue
        if zh is not None and zh < -0.5:
            out.append(_row(day, "strained"))
        else:
            out.append(_row(day, "ready"))
    return out


def signals(data: dict[str, Any], days_back: int = 180) -> dict[str, Any]:
    """One row per day: every signal in its own units AND as a z-score, the
    day's state, and what was ridden - including which DFA bands it touched."""
    wellness = data.get("wellness") or {}
    order = sorted(wellness)[-days_back:]
    if not order:
        return {"days": [], "signals": {}, "load_signals": LOAD_SIGNALS, "bands": []}

    raw_by_signal: dict[str, dict[str, float]] = {}
    z_by_signal: dict[str, dict[str, float]] = {}
    all_days = sorted(wellness)
    for key, meta in SIGNALS.items():
        values: dict[str, float] = {}
        for day in all_days:
            value = _f((wellness.get(day) or {}).get(meta["field"]))
            if value is None:
                continue
            values[day] = value * meta.get("scale", 1)
        raw_by_signal[key] = values
        z_by_signal[key] = _z_series(values, all_days, log=meta.get("log", False),
                                     sign=meta.get("sign", 1))

    states = {row["date"]: row["state"] for row in state_series(data)}

    # activities per day, with the DFA band split so the bar can carry it
    per_day: dict[str, list[dict[str, Any]]] = {}
    dfa_all = data.get("dfa") or {}
    for key, activity in (data.get("activities") or {}).items():
        day = str(activity.get("start_date_local") or "")[:10]
        if not day:
            continue
        summary = dfa_all.get(key) or {}
        total = sum(_f(summary.get(field)) or 0 for field in
                    ("secs_aerobic", "secs_transition", "secs_anaerobic"))
        bands = None
        if total > 0:
            bands = [round((_f(summary.get(field)) or 0) / total * 100)
                     for field in ("secs_aerobic", "secs_transition", "secs_anaerobic")]
        group, label = ("other", "Sonstiges")
        try:
            from . import analytics as _an  # local import keeps this module HA-free
            group, label = _an.sport_group(activity.get("type"))
        except Exception:  # noqa: BLE001 - the fallback above is fine
            pass
        per_day.setdefault(day, []).append({
            "id": key, "name": activity.get("name"), "group": group, "sport": label,
            "load": _f(activity.get("icu_training_load")) or 0,
            "intensity": _f(activity.get("icu_intensity")),
            "minutes": round((activity.get("moving_time") or 0) / 60),
            "dfa_bands": bands,
            "hr": _f(activity.get("average_heartrate")),
            "watts": _f(activity.get("icu_weighted_avg_watts") or activity.get("icu_average_watts")),
            "decoupling": _f(activity.get("decoupling")),
        })

    acwr = {row["date"]: row.get("ratio") for row in _acwr_local(data)}
    rows = []
    for day in order:
        acts = per_day.get(day, [])
        rows.append({
            "date": day,
            "state": states.get(day, "unknown"),
            "raw": {key: round(raw_by_signal[key].get(day), 2)
                    for key in SIGNALS if raw_by_signal[key].get(day) is not None},
            "z": {key: round(z_by_signal[key].get(day), 2)
                  for key in SIGNALS if z_by_signal[key].get(day) is not None},
            "acwr": round(acwr[day], 2) if acwr.get(day) is not None else None,
            "load": round(sum(a["load"] for a in acts)),
            "activities": acts,
            "hard": any((a["intensity"] or 0) >= 80 for a in acts),
        })

    # contiguous state bands, so the background can be painted in few shapes
    bands_out = []
    for row in rows:
        if bands_out and bands_out[-1]["state"] == row["state"]:
            bands_out[-1]["to"] = row["date"]
        else:
            bands_out.append({"state": row["state"], "from": row["date"], "to": row["date"]})

    return {"days": rows,
            "signals": {key: {k: v for k, v in meta.items() if k not in ("field", "scale")}
                        for key, meta in SIGNALS.items()},
            "load_signals": LOAD_SIGNALS,
            "bands": bands_out,
            "swc": 0.5}


def _acwr_local(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Acute:chronic per day, computed here so this module stays standalone."""
    wellness = data.get("wellness") or {}
    days = sorted(wellness)
    loads = []
    for day in days:
        value = _f((wellness.get(day) or {}).get("ctlLoad"))
        if value is None:
            value = _f((wellness.get(day) or {}).get("load")) or 0.0
        loads.append({"date": day, "load": value or 0.0})
    out = []
    for index, row in enumerate(loads):
        if index < 27:
            out.append({"date": row["date"], "ratio": None})
            continue
        acute = mean([r["load"] for r in loads[index - 6:index + 1]])
        chronic = mean([r["load"] for r in loads[index - 27:index + 1]])
        out.append({"date": row["date"],
                    "ratio": (acute / chronic) if chronic > 0 else None})
    return out


# --- what the night after an activity showed ----------------------------------
# Sleep is the cleanest measurement condition there is: no external disruption,
# and the night directly after a session is where the response shows. After a
# hard effort, nocturnal heart rate rises and ln(rMSSD) falls; the return to
# resting values takes minutes up to a full day, driven mainly by intensity.
#
# The catch, and the reason this is never read as "more damping = harder": the
# relationship between load and HRV change is bell-shaped, not linear. A very
# easy session and a very hard one can both leave the night looking ordinary,
# for opposite reasons. So the reading is always RELATIVE TO THIS ATHLETE'S
# OWN usual answer to sessions of the same size - not to a published norm.
NIGHT_FIELDS = (
    ("hrv", "hrv", True, 1, "Herzratenvariabilität", "ms"),
    ("rhr", "restingHR", False, -1, "Ruhepuls", "bpm"),
    ("sleep", "sleepSecs", False, 1, "Schlafdauer", "h"),
)


def _night_z(data: dict[str, Any], day: str) -> dict[str, Any]:
    """Each wellness field of one night, as a z-score against the 60 days before."""
    wellness = data.get("wellness") or {}
    days = sorted(d for d in wellness if d < day)[-60:]
    out: dict[str, Any] = {}
    for key, field, use_log, direction, label, unit in NIGHT_FIELDS:
        raw = []
        wts = []
        for d in days:
            value = _f((wellness.get(d) or {}).get(field))
            if value is None or value <= 0:
                continue
            raw.append(value)
            wts.append(day_context.weight_for(data, d))
        current = _f((wellness.get(day) or {}).get(field))
        band = _norm_band(raw, log=use_log, weights=wts)
        z = _z_at(current if current and current > 0 else None, band,
                  log=use_log, sign=direction)
        if z is None:
            continue
        scale = 1 / 3600 if field == "sleepSecs" else 1
        entry = {
            "label": label, "unit": unit,
            "value": round(current * scale, 2),
            "baseline": round((math.exp(band.base) if use_log else band.base) * scale, 2),
            "z": round(z, 2),
            "baseline_weighted": band.weighted,
        }
        if (note := _fallback_note(band)) is not None:
            entry["baseline_note"] = note
        out[key] = entry
    return out


def night_after(data: dict[str, Any], activity_id: str) -> dict[str, Any]:
    """The night after one session, read against this athlete's usual answer.

    Returns the measured night, the reference built from comparable sessions in
    their own history, and a verdict that says which of the two it resembles.
    """
    activities = data.get("activities") or {}
    activity = activities.get(str(activity_id))
    if not activity:
        return {"available": False, "reason": "unknown_activity"}
    day = str(activity.get("start_date_local") or "")[:10]
    if not day:
        return {"available": False, "reason": "no_date"}
    night_day = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    night = _night_z(data, night_day)
    if not night:
        return {"available": False, "reason": "no_wellness", "night_date": night_day}

    load = _f(activity.get("icu_training_load")) or 0.0
    intensity = _f(activity.get("icu_intensity")) or 0.0

    # comparable sessions: similar load, and the same side of the hard/easy line
    peers: list[dict[str, Any]] = []
    for key, other in activities.items():
        if key == str(activity_id):
            continue
        other_day = str(other.get("start_date_local") or "")[:10]
        if not other_day or other_day >= day:
            continue
        other_load = _f(other.get("icu_training_load")) or 0.0
        other_int = _f(other.get("icu_intensity")) or 0.0
        if load > 0 and abs(other_load - load) > max(15.0, load * 0.3):
            continue
        if abs(other_int - intensity) > 12:
            continue
        peer_night = _night_z(
            data, (date.fromisoformat(other_day) + timedelta(days=1)).isoformat()
        )
        if peer_night:
            peers.append(peer_night)

    reference: dict[str, Any] = {}
    for key in night:
        values = [p[key]["z"] for p in peers if key in p]
        if len(values) >= 5:
            mean_z, spread = _band(values)
            reference[key] = {"mean": round(mean_z, 2), "sd": round(spread, 2), "n": len(values)}

    # the verdict: how this night compares with the usual answer, where known
    # Weighting, not a plain average. The studies that establish this reading
    # measure nocturnal HEART RATE and HRV - those are the autonomic answer.
    # Sleep duration is behaviour: useful context, but a short night after a
    # late finish must not outvote what the heart did.
    weights = {"hrv": 1.0, "rhr": 0.8, "sleep": 0.3}
    marks: list[tuple[float, float]] = []
    for key, entry in night.items():
        ref = reference.get(key)
        if not ref or ref["sd"] <= 0:
            continue
        marks.append(((entry["z"] - ref["mean"]) / ref["sd"], weights.get(key, 0.5)))
    if marks:
        total = sum(weight for _, weight in marks)
        mean_mark = sum(value * weight for value, weight in marks) / total
        if mean_mark <= -1.5:
            state, headline = "hard", "Die Nacht fiel deutlich gedämpfter aus als sonst nach solchen Einheiten."
        elif mean_mark <= -0.7:
            state, headline = "costly", "Die Nacht fiel etwas gedämpfter aus als sonst nach solchen Einheiten."
        elif mean_mark >= 1.0:
            state, headline = "easy", "Die Nacht fiel besser aus als sonst nach solchen Einheiten."
        else:
            state, headline = "usual", "Die Nacht sah aus wie sonst nach solchen Einheiten."
        detail = (f"Verglichen mit {min(r['n'] for r in reference.values())} früheren Einheiten "
                  f"ähnlicher Last und Intensität.")
    else:
        state, headline = "unknown", "Kein Vergleich möglich."
        detail = ("Es liegen noch zu wenige frühere Einheiten ähnlicher Last mit gemessener "
                  "Folgenacht vor — mindestens fünf werden gebraucht.")

    return {
        "available": True,
        "night_date": night_day,
        "activity_date": day,
        "load": round(load), "intensity": round(intensity),
        "night": night,
        "reference": reference,
        "state": state, "headline": headline, "detail": detail,
        "caveat": (
            "Die Nacht direkt nach einer Einheit ist die sauberste Messbedingung, die es "
            "gibt — kein Alltag stört. Gelesen wird sie hier gegen deine eigene übliche "
            "Antwort auf gleich große Einheiten, nicht gegen einen Normwert: der "
            "Zusammenhang zwischen Last und HRV-Änderung ist glockenförmig, nicht gerade. "
            "Eine sehr lockere und eine sehr harte Einheit können beide eine unauffällige "
            "Nacht hinterlassen — aus entgegengesetzten Gründen. Und es bleibt die "
            "Nachtmessung der Uhr, nicht die validierte Morgenmessung im Liegen."
        ),
    }


# --- is this number large FOR THIS RIDER? -------------------------------------
# A decoupling of 11.4% means nothing on its own. Friel's 5% is a population
# benchmark; what the rider needs to know is where this ride sits among their
# own comparable rides. Same logic as the night reading: the reference is the
# athlete's own history, not a published threshold.
def _percentile_rank(values: list[float], value: float) -> int:
    below = sum(1 for v in values if v < value)
    equal = sum(1 for v in values if v == value)
    return round((below + 0.5 * equal) / len(values) * 100)


def _sport_group(entry: dict[str, Any]) -> str:
    """Return the comparison group an activity belongs to."""
    kind = str(entry.get("type") or "")
    if kind in ("Ride", "VirtualRide", "GravelRide", "MountainBikeRide"):
        return "ride"
    if kind in ("Run", "TrailRun", "VirtualRun"):
        return "run"
    return kind or "other"


def _caliper_percent(width: float) -> tuple[float, float]:
    """Return the (lower, upper) percent bounds of a log-duration caliper.

    A caliper that is symmetric in the log is NOT symmetric in percent. Showing
    it as a single "±x %" is a lie in one direction, so both numbers travel
    (docs/ausbau.md C3).
    """
    return (round((math.exp(-width) - 1) * 100, 1), round((math.exp(width) - 1) * 100, 1))


def session_context(data: dict[str, Any], activity_id: str) -> dict[str, Any]:
    """Place this session's key numbers among the athlete's comparable sessions.

    Comparable means: same sport group, and duration and intensity inside a
    CALIPER measured in the athlete's own standard deviations - on the log
    duration, because durations are right-skewed and 45 min to 3 h is not a
    symmetric plus/minus. The caliper widens in fixed steps until a metric has
    enough peers to be ranked, and the step that was reached is always reported.

    The widening runs against the n OF THE METRIC, not against the number of
    peers: only some sessions carry a decoupling value, and widening against
    the peer count would print "8 sessions" beside "too thin" (docs/ausbau.md C3).
    """
    activities = data.get("activities") or {}
    activity = activities.get(str(activity_id))
    if not activity:
        return {"available": False}

    day = str(activity.get("start_date_local") or "")[:10]
    group = _sport_group(activity)
    intensity = _f(activity.get("icu_intensity")) or 0.0
    minutes = (activity.get("moving_time") or 0) / 60

    # The spread is measured over the whole group, not only over the earlier
    # sessions - otherwise the caliper of an old session would be computed from
    # a handful of values. It therefore MOVES as the archive grows, and the
    # panel says so.
    population = [
        other for other in activities.values()
        if isinstance(other, dict) and _sport_group(other) == group
        and (other.get("moving_time") or 0) > 0
    ]
    log_durations = [math.log((other.get("moving_time") or 0) / 60) for other in population]
    intensities = [_f(other.get("icu_intensity")) or 0.0 for other in population]
    sd_log = pstdev(log_durations) if len(log_durations) > 1 else 0.0
    sd_intensity = pstdev(intensities) if len(intensities) > 1 else 0.0

    earlier = []
    for key, other in activities.items():
        if key == str(activity_id) or _sport_group(other) != group:
            continue
        other_day = str(other.get("start_date_local") or "")[:10]
        if not other_day or other_day >= day:
            continue
        earlier.append(other)

    log_minutes = math.log(minutes) if minutes > 0 else None

    def within(other: dict[str, Any], stage: float) -> bool:
        if sd_intensity > 0:
            if abs((_f(other.get("icu_intensity")) or 0.0) - intensity) > stage * sd_intensity:
                return False
        if sd_log > 0 and log_minutes is not None:
            other_minutes = (other.get("moving_time") or 0) / 60
            if other_minutes <= 0:
                return False
            if abs(math.log(other_minutes) - log_minutes) > stage * sd_log:
                return False
        return True

    metrics = (
        ("decoupling", "Entkopplung", "%", "down", lambda e: _f(e.get("decoupling"))),
        ("ef", "Watt pro Herzschlag", "", "up",
         lambda e: (_f(e.get("icu_weighted_avg_watts") or e.get("icu_average_watts")) or 0)
                   / (_f(e.get("average_heartrate")) or 1)
                   if e.get("average_heartrate") else None),
        ("hr", "Ø Herzfrequenz", "bpm", "down", lambda e: _f(e.get("average_heartrate"))),
    )

    out: dict[str, Any] = {}
    widest = None
    for key, label, unit, good, getter in metrics:
        value = getter(activity)
        if value is None:
            continue
        # Two different reasons for "no group", two different sentences. The
        # first heals by itself as the archive grows, the second does not.
        available = [v for v in (getter(other) for other in earlier) if v is not None]
        chosen, history = None, []
        for stage in PEER_CALIPER_STAGES:
            history = [
                v for v in (getter(other) for other in earlier if within(other, stage))
                if v is not None
            ]
            if len(history) >= MIN_PEERS_TO_RANK_METRIC:
                chosen = stage
                break
        if chosen is None:
            too_early = len(available) < MIN_PEERS_TO_RANK_METRIC
            out[key] = {
                "label": label, "unit": unit, "value": round(value, 2),
                "n": len(history), "enough": False,
                "why": "too_early" if too_early else "too_few",
                "say": (
                    f"zu früh in deiner Historie — davor liegen erst {len(available)} "
                    f"Einheiten mit diesem Wert"
                ) if too_early else (
                    f"zu wenige vergleichbare Einheiten — auch auf der weitesten Stufe "
                    f"({PEER_CALIPER_STAGES[-1]:.1f} SD) nur {len(history)}"
                ),
            }
            continue
        widest = chosen if widest is None else max(widest, chosen)
        low_pct, high_pct = _caliper_percent(chosen * sd_log)
        ordered = sorted(history)
        rank = _percentile_rank(ordered, value)
        # The verdict hangs on leaving the MIDDLE HALF, not on the percentile.
        # In a tight distribution a hair's difference lands at rank 62, and
        # calling that "worse than usual" would be noise dressed as a finding.
        # The middle half is also exactly the band the panel draws, so the
        # words and the picture cannot disagree.
        low, high = ordered[max(0, len(ordered) // 4 - 1)], ordered[min(len(ordered) - 1, (3 * len(ordered)) // 4)]
        above, below = value > high, value < low
        favourable = above if good == "up" else below
        unfavourable = below if good == "up" else above
        out[key] = {
            "label": label, "unit": unit, "value": round(value, 2),
            "median": round(median(ordered), 2),
            "best": round(ordered[0] if good == "down" else ordered[-1], 2),
            "worst": round(ordered[-1] if good == "down" else ordered[0], 2),
            "p25": round(ordered[max(0, len(ordered) // 4 - 1)], 2),
            "p75": round(ordered[min(len(ordered) - 1, (3 * len(ordered)) // 4)], 2),
            "n": len(history), "enough": True, "rank": rank, "good": good,
            "stage": chosen,
            "duration_low_pct": low_pct,
            "duration_high_pct": high_pct,
            "intensity_points": round(chosen * sd_intensity, 1),
            "verdict": ("besser als sonst" if favourable else
                        "schlechter als sonst" if unfavourable else "im üblichen Bereich"),
        }

    return {
        "available": bool(out),
        "group": group,
        "earlier": len(earlier),
        "stages": list(PEER_CALIPER_STAGES),
        "widest_used": widest,
        "min_peers": MIN_PEERS_TO_RANK_METRIC,
        "sd_log_duration": round(sd_log, 3),
        "sd_intensity": round(sd_intensity, 2),
        "population": len(population),
        "window": {"intensity": round(intensity), "minutes": round(minutes)},
        "metrics": out,
        "note": (
            "Verglichen wird mit deinen eigenen FRÜHEREN Einheiten derselben Sportart. "
            "Die Toleranz ist keine feste Prozentzahl, sondern ein Vielfaches deiner "
            "eigenen Streuung — bei der Dauer auf dem Logarithmus gerechnet, weil "
            "45 Minuten und 3 Stunden kein symmetrisches Plus/Minus sind. Deshalb "
            "steht die Spanne mit zwei Zahlen da und nicht als ±. Reicht die engste "
            "Stufe nicht, wird in festen Schritten geweitet, bis genug Einheiten "
            "zusammenkommen; die erreichte Stufe steht bei jeder Zeile. Geweitet wird "
            "gegen die Zahl der Einheiten MIT DIESEM WERT, nicht gegen die Zahl der "
            "Vergleichseinheiten. Die Streuung wird aus deinem gesamten Bestand dieser "
            "Sportart gerechnet und wandert deshalb mit: dieselbe alte Einheit kann in "
            "einigen Monaten eine etwas andere Gruppe bekommen."
        ),
    }


# --- what is possible today ---------------------------------------------------
# Built against the criticism of composite readiness scores, not in spite of it.
#
# The distinction that most dashboards lose: RECOVERY describes what happened
# in response to past stress; READINESS describes what can be tolerated right
# now. A single number collapses the two, and worse - a low score from a short
# night and a low score from a starting infection are not the same state, but
# they look identical. Of fourteen commercial scores across ten manufacturers,
# not one publishes its formula and few offer any validation.
#
# So this page answers three questions in order, which is exactly what the
# review recommends doing with such data instead of treating it as a verdict:
#   1. WHAT IS POSSIBLE TODAY - one sentence and a load ceiling
#   2. WHAT CHANGED, AND WHICH SYSTEM - the signals that actually moved, named
#      by the system they belong to, never averaged into a score
#   3. WHERE IT COMES FROM - the last days of training and the night after
# And only today. Beyond that the load outside training is unknown, so the
# page does not pretend to reach further.
def _signal_bands(data: dict[str, Any], day: str) -> dict[str, Any]:
    """Baseline and the SD thresholds, converted back into real units."""
    wellness = data.get("wellness") or {}
    days = sorted(d for d in wellness if d <= day)[-60:]
    out: dict[str, Any] = {}
    for key, field, use_log, direction, label, unit in NIGHT_FIELDS:
        raw = []
        wts = []
        for d in days:
            value = _f((wellness.get(d) or {}).get(field))
            if value is None or value <= 0:
                continue
            raw.append(value)
            wts.append(day_context.weight_for(data, d))
        band = _norm_band(raw, log=use_log, weights=wts)
        if band is None:
            continue
        base, spread = band.base, band.spread
        scale = 1 / 3600 if field == "sleepSecs" else 1

        def at(sd: float) -> float:
            value = base + sd * spread
            return (math.exp(value) if use_log else value) * scale

        entry = {
            "baseline": round(at(0), 2),
            "noise": [round(at(-SWC_SD), 2), round(at(SWC_SD), 2)],
            "usual": [round(at(-1), 2), round(at(1), 2)],
            "slump": round(at(-HRV_DROP_SD if direction > 0 else HRV_DROP_SD), 2),
            "unit": unit,
            "weighted": band.weighted,
        }
        if (note := _fallback_note(band)) is not None:
            entry["note"] = note
        out[key] = entry
    return out


def today(data: dict[str, Any], budget: dict[str, Any] | None = None) -> dict[str, Any]:
    wellness = data.get("wellness") or {}
    if not wellness:
        return {"available": False}
    days = sorted(wellness)
    current = days[-1]

    condition = state(data)
    anchors_now = anchors(data)
    series = {row["date"]: row["state"] for row in state_series(data)}

    # the signals, each kept separate and named by the system it reports on
    signals: list[dict[str, Any]] = []
    z_now = _night_z(data, current)
    SYSTEM = {
        "hrv": ("Autonomes Nervensystem", "Nachtmessung der Uhr, nicht die validierte "
                                          "Morgenmessung im Liegen"),
        "rhr": ("Autonomes Nervensystem", "reagiert träger als die HRV, dafür stabiler"),
        "sleep": ("Verhalten", "Dauer aus der Uhr geschätzt; kein autonomer Messwert"),
    }
    for key, entry in z_now.items():
        system, limit = SYSTEM.get(key, ("", ""))
        z = entry["z"]
        signals.append({
            "key": key, "label": entry["label"], "unit": entry["unit"],
            "value": entry["value"], "baseline": entry["baseline"], "z": z,
            "system": system, "limit": limit,
            "moved": abs(z) >= SWC_SD,
            "direction": "günstig" if z >= SWC_SD else "ungünstig" if z <= -SWC_SD else "unauffällig",
        })

    # recent training - the other half of "how does this fit what you did"
    # The day's load comes from the ACTIVITIES, not from the wellness row: that
    # field is not filled on every account, and reading it there reported "0
    # load in seven days" on a week that contained a ride and a walk.
    by_day: dict[str, list[dict[str, Any]]] = {}
    for activity in (data.get("activities") or {}).values():
        key = str(activity.get("start_date_local") or "")[:10]
        if key:
            by_day.setdefault(key, []).append(activity)

    def _day_load(day_key: str) -> float:
        """One way to the day's load, used by both the 7-day strip and the
        42-day event track. Two callers computing this separately is exactly
        the defect class that produced "0 load in seven days"."""
        sessions = by_day.get(day_key, [])
        load = sum(_f(a.get("icu_training_load")) or 0 for a in sessions)
        if not load:
            load = _f((wellness.get(day_key) or {}).get("load")) or 0
        return load

    recent = []
    for day_key in days[-7:]:
        sessions = by_day.get(day_key, [])
        recent.append({
            "date": day_key,
            "load": round(_day_load(day_key)),
            "sessions": [{"name": a.get("name"), "type": a.get("type"),
                          "minutes": round((a.get("moving_time") or 0) / 60)}
                         for a in sessions],
            "state": series.get(day_key, "unknown"),
        })
    week_load = sum(row["load"] for row in recent)
    rest_days = sum(1 for row in recent if row["load"] == 0)

    # the night after the last session - recovery, explicitly labelled as such
    last_activity = None
    for key, activity in (data.get("activities") or {}).items():
        day_key = str(activity.get("start_date_local") or "")[:10]
        if not day_key:
            continue
        if last_activity is None or day_key > last_activity[1]:
            last_activity = (key, day_key)
    night = night_after(data, last_activity[0]) if last_activity else {"available": False}

    # the ceiling for today
    ceiling = None
    if budget and budget.get("recommended") is not None:
        ceiling = round(budget["recommended"])

    CAPACITY = {
        "slump": ("Ruhetag", "Heute nichts. Der Einbruch ist akut.", 0),
        "recovering": ("Locker oder frei", "Wenn überhaupt, dann ganz locker und kurz.", 30),
        "rebound": ("Ruhig fahren", "Die Erholung läuft. Ruhig fahren geht, hart noch nicht.", 60),
        "strained": ("Grundlage", "Beansprucht — Umfang ja, Intensität nein.", 75),
        "ready": ("Alles möglich", "Nichts spricht gegen einen harten Reiz.", None),
        "elevated": ("Grundlage", "Auffällig hohe Werte — heute ruhig halten.", 70),
        "unknown": ("Nach Gefühl", "Zu wenige Daten für eine Aussage.", None),
    }
    capacity, capacity_text, cap_load = CAPACITY.get(
        condition["state"], CAPACITY["unknown"])
    if cap_load is not None:
        ceiling = cap_load if ceiling is None else min(ceiling, cap_load)

    # Where the signals and the verdict disagree, SAY so. A page that prints
    # "nothing speaks against a hard session" above two signals sitting below
    # baseline looks broken - and the reason it is not broken is worth one
    # sentence: a single day below the line is noise, the rule runs on the
    # three-day mean and on a threshold twice this size.
    tension = None
    unfavourable = [s for s in signals if s["direction"] == "ungünstig"]
    favourable = [s for s in signals if s["direction"] == "günstig"]
    if unfavourable and condition["state"] in ("ready", "elevated"):
        names = " und ".join(s["label"] for s in unfavourable)
        tension = (
            f"{names} liegt heute unter deiner Basislinie — aber weder weit genug noch "
            f"lange genug für einen Einbruch. Die Regel entscheidet über das Mittel der "
            f"letzten drei Tage und ab {HRV_DROP_SD:.0f} Standardabweichungen; ein "
            "einzelner Tag darunter ist Rauschen. Wenn es morgen wieder so aussieht, "
            "ist es keins mehr."
        )
    elif favourable and condition["state"] in ("slump", "recovering"):
        tension = (
            "Einzelne Werte sehen heute gut aus, der Zustand bleibt trotzdem gedämpft: "
            "nach einem Einbruch zählt, ob die letzten Tage zusammen wieder über der "
            "Basislinie liegen, nicht ein guter Morgen."
        )

    return {
        "available": True,
        "date": current,
        "tension": tension,
        "capacity": capacity,
        "capacity_text": capacity_text,
        "ceiling": ceiling,
        "state": condition["state"],
        "state_label": condition.get("label"),
        "state_text": condition.get("text"),
        # day context (docs/ausbau.md B3): today's label, whether the current
        # verdict is explained by one, and the fallback hint with numbers
        "explained": condition.get("explained", False),
        "context": condition.get("context"),
        "context_note": condition.get("baseline_note"),
        "signals": signals,
        # The bands that matter, expressed in the signal's OWN unit rather than
        # in standard deviations - a rider recognises 41 ms, not -1.5 SD. They
        # are the same thresholds the rules already use: +-0.5 SD is noise by
        # definition, +-1 SD is the ordinary spread, and 2 SD is where a drop
        # stops being noise and becomes a slump.
        "bands": _signal_bands(data, current),
        # 42 days per signal, so the enlarged card can show a curve instead of
        # a single number with nothing to compare it against
        "history": {
            key: [_f((wellness.get(d) or {}).get(field)) * (1 / 3600 if field == "sleepSecs" else 1)
                  if _f((wellness.get(d) or {}).get(field)) else None
                  for d in days[-42:]]
            for key, field, _log, _sign, _label, _unit in NIGHT_FIELDS
        },
        # The SAME 42 days as "history", but named. The enlarged signal card
        # draws a diagram, and a diagram needs an axis - and these are the
        # wellness days that EXIST, not 42 consecutive calendar days, so the
        # frontend cannot reconstruct them from "today minus n" without being
        # wrong after the first gap. Load and state travel along so the card
        # can carry an event track ("HRV drops two days after the long ride")
        # without a tab change.
        "history_days": [
            {"date": d, "load": round(_day_load(d)), "state": series.get(d, "unknown"),
             **({"context": {"tag": e["tag"], "weight": day_context.weight_for(data, d)}}
                if (e := day_context.entry_for(data, d)) else {})}
            for d in days[-42:]
        ],
        "moved": [s for s in signals if s["moved"]],
        "recent": recent,
        "week_load": round(week_load),
        "rest_days": rest_days,
        "night": night,
        "anchors": anchors_now,
        "horizon": (
            "Nur für heute. Was morgen geht, hängt an der Belastung außerhalb des "
            "Trainings — Arbeit, Schlaf, Stress —, und die steht in keinen Daten. "
            "Der wirksamste Einsatz solcher Werte liegt in der Anpassung der heutigen "
            "Einheit, nicht in der Planung der Woche."
        ),
        "method": (
            "Bewusst KEIN Punktwert. Von vierzehn Bereitschaftswerten aus zehn "
            "Wearable-Häusern legt kein einziger seine Formel offen, und kaum einer "
            "hat eine Validierung vorzuweisen. Vor allem aber: eine niedrige Zahl "
            "aus einer kurzen Nacht und eine niedrige Zahl aus einem beginnenden "
            "Infekt sehen gleich aus und verlangen Gegenteiliges. Deshalb stehen die "
            "Signale hier einzeln, mit dem System, über das sie etwas aussagen, und "
            "mit dem, was sie nicht können."
        ),
    }
