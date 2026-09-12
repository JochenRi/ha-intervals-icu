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
from typing import Any

# --- thresholds, all of them sourced ------------------------------------------
HRV_DROP_SD = 2.0          # PLEWS: an acute drop of this size is not noise
RHR_RISE_SD = 2.0
RECOVERY_WINDOW = 10       # days a slump keeps colouring the picture
LAYOFF_DAYS = 4            # MUJIKA: below this, nothing measurable is lost
DFA_AEROBIC = 0.75         # ROGERS
DFA_ANAEROBIC = 0.5        # ROGERS
DECOUPLING_GOOD = 5.0      # FRIEL
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


def _norm_band(raw: list[float], *, log: bool) -> tuple[float, float] | None:
    """THE baseline of a wellness signal - the only place it is computed.

    One primitive instead of four hand-rolled copies: `state()`,
    `_z_series()`, `_night_z()` and `_signal_bands()` all call this, so the
    scale (HRV on the log scale, the published ln(rMSSD) comparison), the
    20-value floor and the flat-band rejection cannot drift apart again.
    Until 0.36.1 `state()` computed the HRV band on the RAW scale while the
    series ran on logs - the trainer verdict and the history bands could
    disagree on the same day. A guard in test_coach.py checks the callers.

    Returns (base, spread) on the (possibly log) scale, or None when the
    history is too thin to mean anything.
    """
    values = [math.log(v) for v in raw if v > 0] if log else list(raw)
    if len(values) < 20:
        return None
    base, spread = _band(values)
    if spread <= 0:
        return None
    return (base, spread)


def _z_at(value: float | None, band: tuple[float, float] | None, *,
          log: bool, sign: int = 1) -> float | None:
    """A value's distance from its band, on the band's own scale."""
    if value is None or band is None:
        return None
    if log:
        if value <= 0:
            return None
        value = math.log(value)
    base, spread = band
    return sign * (value - base) / spread


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
                "slump": None, "confidence": "keine"}

    today = days[-1]
    hrv = _series(wellness, "hrv", days)
    rhr = _series(wellness, "restingHR", days) or _series(wellness, "resting_hr", days)

    hrv_days = sorted(hrv)
    base_days = [d for d in hrv_days if d < today][-60:]
    hrv_band = _norm_band([hrv[d] for d in base_days], log=True)
    rhr_base_days = [d for d in sorted(rhr) if d < today][-60:]
    rhr_band = _norm_band([rhr[d] for d in rhr_base_days], log=False)

    def z_hrv(day: str) -> float | None:
        return _z_at(hrv.get(day), hrv_band, log=True)

    def z_rhr(day: str) -> float | None:
        return _z_at(rhr.get(day), rhr_band, log=False)

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
    week_z = (((mean(week) - hrv_band[0]) / hrv_band[1])
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
            return _st("slump", "Einbruch", slump_day, cause_text,
                       week_z, now_hrv, now_rhr, "hoch", slump_cause, infection)
        if recovered:
            return _st("rebound", "Erholung nach Einbruch", slump_day,
                       f"Der Einbruch war vor {days_since} Tagen. Die letzten Tage liegen "
                       "wieder über deiner Basislinie, der Ruhepuls darunter — der Körper "
                       "ist auf dem Rückweg. Das 7-Tage-Mittel hinkt noch nach, weil der "
                       "Einbruch darin steckt." + infection_note,
                       week_z, now_hrv, now_rhr, "mittel", slump_cause, infection)
        return _st("recovering", "noch im Einbruch", slump_day,
                   f"Der Einbruch war vor {days_since} Tagen und die Werte sind noch nicht "
                   "zurück auf deiner Basislinie." + infection_note,
                   week_z, now_hrv, now_rhr, "hoch", slump_cause, infection)

    if week_z is None:
        return _st("unknown", "keine Einschätzung", None,
                   "Zu wenige HRV-Werte für einen Vergleich.", None, now_hrv, now_rhr, "keine")
    if week_z < -swc:
        return _st("strained", "beansprucht", None,
                   "Das 7-Tage-Mittel liegt unter deinem Normalband — nach der Regel von "
                   "Javaloyes ist das ein Tag für Umfang, nicht für Intensität.",
                   week_z, now_hrv, now_rhr, "mittel")
    if week_z > 1.5:
        return _st("elevated", "auffällig hoch", None,
                   "Das 7-Tage-Mittel liegt deutlich über dem Normalband. Nach Plews ist "
                   "das nicht automatisch gut: dauerhaft erhöhte Werte können auch "
                   "Erschöpfung anzeigen. Im Zweifel: wie gewohnt trainieren und beobachten.",
                   week_z, now_hrv, now_rhr, "gering")
    return _st("ready", "im Normalbereich", None,
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
        hr = _f(summary.get("hr_at_threshold"))
        if hr is None or hr <= 0 or (summary.get("threshold_samples") or 0) < 5:
            continue
        act = acts.get(key) or {}
        rows.append({"date": str(act.get("start_date_local") or "")[:10],
                     "hr": hr, "power": _f(summary.get("power_at_threshold"))})
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


def durability(data: dict[str, Any], min_minutes: int = 45) -> dict[str, Any] | None:
    """How well the athlete holds up over duration - measured, not assumed."""
    rows = []
    for activity in (data.get("activities") or {}).values():
        minutes = (activity.get("moving_time") or 0) / 60
        dec = _f(activity.get("decoupling"))
        if minutes < min_minutes or dec is None:
            continue
        if (_f(activity.get("icu_intensity")) or 0) >= 80:
            continue
        rows.append({"min": minutes, "dec": dec})
    if len(rows) < 8:
        return None
    short = [r["dec"] for r in rows if r["min"] < 90]
    long = [r["dec"] for r in rows if r["min"] >= 90]
    return {
        "n": len(rows),
        "short": round(median(short), 1) if short else None,
        "long": round(median(long), 1) if long else None,
        "verdict": ("die aerobe Basis trägt auch lange Einheiten"
                    if (long and median(long) <= DECOUPLING_GOOD) or
                       (not long and short and median(short) <= DECOUPLING_GOOD)
                    else "die Entkopplung steigt mit der Dauer — die Grundlage trägt lange "
                         "Einheiten noch nicht"),
        "source": "Friel: bis 5 % Entkopplung auf ruhigen Dauereinheiten ist unauffällig",
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
              log: bool = False, sign: int = 1) -> dict[str, float]:
    """Distance from a trailing baseline, in standard deviations.

    The baseline trails the day it judges, so today is never part of its own
    normal - otherwise a slow drift would erase itself.
    """
    out: dict[str, float] = {}
    ordered = [d for d in days if d in values]
    for index, day in enumerate(ordered):
        history = ordered[max(0, index - window):index]
        band = _norm_band([values[d] for d in history], log=log)
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
    z_hrv = _z_series(hrv, days, log=True, sign=1)
    z_rhr = _z_series(rhr, days, sign=1)      # unsigned here: a RISE is the warning

    out: list[dict[str, str]] = []
    slump_day: str | None = None
    for day in days:
        zh, zr = z_hrv.get(day), z_rhr.get(day)
        if zh is None and zr is None:
            out.append({"date": day, "state": "unknown"})
            continue
        hrv_hit = zh is not None and zh <= -HRV_DROP_SD
        rhr_hit = zr is not None and zr >= RHR_RISE_SD
        prev = _shift(day, -1)
        persists = ((hrv_hit and z_hrv.get(prev) is not None and z_hrv[prev] <= -HRV_DROP_SD)
                    or (rhr_hit and z_rhr.get(prev) is not None and z_rhr[prev] >= RHR_RISE_SD))
        acute = (hrv_hit and rhr_hit) or persists
        if acute:
            slump_day = day
            out.append({"date": day, "state": "slump"})
            continue
        if slump_day is not None:
            since = (date.fromisoformat(day) - date.fromisoformat(slump_day)).days
            if since > RECOVERY_WINDOW:
                slump_day = None
            else:
                # Same rule as state(): judge the recovery on the mean of the
                # last three days, not on one day. A single dip below the
                # baseline is noise, and the bands in the chart have to say
                # exactly what the trainer view says.
                window = [d for d in days if d <= day][-3:]
                hs = [z_hrv[d] for d in window if d in z_hrv]
                rs = [z_rhr[d] for d in window if d in z_rhr]
                back = ((not hs or mean(hs) >= 0) and (not rs or mean(rs) <= 0))
                out.append({"date": day, "state": "rebound" if back else "recovering"})
                continue
        if zh is not None and zh < -0.5:
            out.append({"date": day, "state": "strained"})
        else:
            out.append({"date": day, "state": "ready"})
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
        for d in days:
            value = _f((wellness.get(d) or {}).get(field))
            if value is None or value <= 0:
                continue
            raw.append(value)
        current = _f((wellness.get(day) or {}).get(field))
        band = _norm_band(raw, log=use_log)
        z = _z_at(current if current and current > 0 else None, band,
                  log=use_log, sign=direction)
        if z is None:
            continue
        base, _spread = band
        scale = 1 / 3600 if field == "sleepSecs" else 1
        out[key] = {
            "label": label, "unit": unit,
            "value": round(current * scale, 2),
            "baseline": round((math.exp(base) if use_log else base) * scale, 2),
            "z": round(z, 2),
        }
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


def session_context(data: dict[str, Any], activity_id: str) -> dict[str, Any]:
    """Place this session's key numbers among the athlete's comparable sessions.

    Comparable means: same sport group, intensity within 10 points, duration
    within 40%. Without that narrowing a three-hour base ride would be judged
    against a 45-minute interval session, and the comparison would be noise.
    """
    activities = data.get("activities") or {}
    activity = activities.get(str(activity_id))
    if not activity:
        return {"available": False}

    def _group(entry: dict[str, Any]) -> str:
        kind = str(entry.get("type") or "")
        if kind in ("Ride", "VirtualRide", "GravelRide", "MountainBikeRide"):
            return "ride"
        if kind in ("Run", "TrailRun", "VirtualRun"):
            return "run"
        return kind or "other"

    day = str(activity.get("start_date_local") or "")[:10]
    group = _group(activity)
    intensity = _f(activity.get("icu_intensity")) or 0.0
    minutes = (activity.get("moving_time") or 0) / 60

    peers = []
    for key, other in activities.items():
        if key == str(activity_id) or _group(other) != group:
            continue
        other_day = str(other.get("start_date_local") or "")[:10]
        if not other_day or other_day >= day:
            continue
        other_int = _f(other.get("icu_intensity")) or 0.0
        other_min = (other.get("moving_time") or 0) / 60
        if abs(other_int - intensity) > 10:
            continue
        if minutes > 0 and abs(other_min - minutes) > minutes * 0.4:
            continue
        peers.append(other)

    metrics = (
        ("decoupling", "Entkopplung", "%", "down", lambda e: _f(e.get("decoupling"))),
        ("ef", "Watt pro Herzschlag", "", "up",
         lambda e: (_f(e.get("icu_weighted_avg_watts") or e.get("icu_average_watts")) or 0)
                   / (_f(e.get("average_heartrate")) or 1)
                   if e.get("average_heartrate") else None),
        ("hr", "Ø Herzfrequenz", "bpm", "down", lambda e: _f(e.get("average_heartrate"))),
    )

    out: dict[str, Any] = {}
    for key, label, unit, good, getter in metrics:
        value = getter(activity)
        if value is None:
            continue
        history = [v for v in (getter(p) for p in peers) if v is not None]
        if len(history) < 6:
            out[key] = {"label": label, "unit": unit, "value": round(value, 2),
                        "n": len(history), "enough": False}
            continue
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
            "verdict": ("besser als sonst" if favourable else
                        "schlechter als sonst" if unfavourable else "im üblichen Bereich"),
        }

    return {
        "available": bool(out),
        "group": group,
        "peers": len(peers),
        "window": {"intensity": round(intensity), "minutes": round(minutes)},
        "metrics": out,
        "note": (
            "Verglichen wird mit deinen eigenen früheren Einheiten derselben Sportart, "
            "deren Intensität um höchstens 10 Punkte und deren Dauer um höchstens 40 % "
            "abweicht. Ohne diese Eingrenzung stünde eine Dreistundenfahrt neben einer "
            "45-Minuten-Intervalleinheit, und der Vergleich wäre Rauschen. Der "
            "Prozentrang sagt, wie viele der Vergleichseinheiten schlechter lagen — "
            "50 heißt genau im Mittelfeld."
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
        for d in days:
            value = _f((wellness.get(d) or {}).get(field))
            if value is None or value <= 0:
                continue
            raw.append(value)
        band = _norm_band(raw, log=use_log)
        if band is None:
            continue
        base, spread = band
        scale = 1 / 3600 if field == "sleepSecs" else 1

        def at(sd: float) -> float:
            value = base + sd * spread
            return (math.exp(value) if use_log else value) * scale

        out[key] = {
            "baseline": round(at(0), 2),
            "noise": [round(at(-SWC_SD), 2), round(at(SWC_SD), 2)],
            "usual": [round(at(-1), 2), round(at(1), 2)],
            "slump": round(at(-HRV_DROP_SD if direction > 0 else HRV_DROP_SD), 2),
            "unit": unit,
        }
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
            {"date": d, "load": round(_day_load(d)), "state": series.get(d, "unknown")}
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
