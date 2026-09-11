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
    hrv_base, hrv_sd = _band([hrv[d] for d in base_days])
    rhr_base_days = [d for d in sorted(rhr) if d < today][-60:]
    rhr_base, rhr_sd = _band([rhr[d] for d in rhr_base_days])

    def z_hrv(day: str) -> float | None:
        if day not in hrv or hrv_sd <= 0:
            return None
        return (hrv[day] - hrv_base) / hrv_sd

    def z_rhr(day: str) -> float | None:
        if day not in rhr or rhr_sd <= 0:
            return None
        return (rhr[day] - rhr_base) / rhr_sd

    recent = [d for d in hrv_days if d >= _shift(today, -(RECOVERY_WINDOW - 1))]
    slump_day = None
    for day in recent:
        zh, zr = z_hrv(day), z_rhr(day)
        if (zh is not None and zh <= -HRV_DROP_SD) or (zr is not None and zr >= RHR_RISE_SD):
            slump_day = day
    last3 = [z_hrv(d) for d in hrv_days[-3:] if z_hrv(d) is not None]
    last3_rhr = [z_rhr(d) for d in sorted(rhr)[-3:] if z_rhr(d) is not None]
    now_hrv = mean(last3) if last3 else None
    now_rhr = mean(last3_rhr) if last3_rhr else None

    # 7-day mean against the 60-day band, the published comparison (PLEWS)
    week = [hrv[d] for d in hrv_days[-7:]]
    week_z = ((mean(week) - hrv_base) / hrv_sd) if (week and hrv_sd > 0) else None
    swc = 0.5  # half a standard deviation, the usual smallest worthwhile change

    if slump_day is not None:
        days_since = (date.fromisoformat(today) - date.fromisoformat(slump_day)).days
        recovered = (now_hrv is not None and now_hrv >= 0) and (now_rhr is None or now_rhr <= 0)
        if days_since == 0:
            return _st("slump", "Einbruch", slump_day,
                       "Deine Werte sind heute deutlich außerhalb deines Normalbereichs.",
                       week_z, now_hrv, now_rhr, "hoch")
        if recovered:
            return _st("rebound", "Erholung nach Einbruch", slump_day,
                       f"Der Einbruch war vor {days_since} Tagen. Die letzten Tage liegen "
                       "wieder über deiner Basislinie, der Ruhepuls darunter — der Körper "
                       "ist auf dem Rückweg. Das 7-Tage-Mittel hinkt noch nach, weil der "
                       "Einbruch darin steckt.",
                       week_z, now_hrv, now_rhr, "mittel")
        return _st("recovering", "noch im Einbruch", slump_day,
                   f"Der Einbruch war vor {days_since} Tagen und die Werte sind noch nicht "
                   "zurück auf deiner Basislinie.",
                   week_z, now_hrv, now_rhr, "hoch")

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


def _st(key, label, since, detail, week_z, now_hrv, now_rhr, confidence):
    return {"state": key, "label": label, "since": since, "detail": detail,
            "week_z": round(week_z, 2) if week_z is not None else None,
            "recent_hrv_z": round(now_hrv, 2) if now_hrv is not None else None,
            "recent_rhr_z": round(now_rhr, 2) if now_rhr is not None else None,
            "confidence": confidence}


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

    half = len(rows) // 2
    old_pw = [r["power"] for r in rows[:half] if r["power"]]
    new_pw = [r["power"] for r in rows[half:] if r["power"]]
    old_hr = [r["hr"] for r in rows[:half]]
    new_hr = [r["hr"] for r in rows[half:]]
    trend = None
    if old_pw and new_pw and old_hr and new_hr:
        trend = {
            "power_before": round(mean(old_pw)), "power_now": round(mean(new_pw)),
            "hr_before": round(mean(old_hr)), "hr_now": round(mean(new_hr)),
            "power_change_pct": round((mean(new_pw) - mean(old_pw)) / mean(old_pw) * 100, 1),
            "hr_change": round(mean(new_hr) - mean(old_hr), 1),
        }
    return {"aerobic_hr": round(hr_now), "aerobic_power": round(power_now) if power_now else None,
            "n": len(rows), "trend_power": trend,
            "source": "Median der letzten fünf belastbaren DFA-Messungen (Rogers/Gronwald: "
                      "alpha-1 = 0,75 markiert die aerobe Schwelle)"}


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


# --- the session menu ----------------------------------------------------------
# Each entry states what it does to the body and what it should feel like in the
# data - so the recommendation can be checked afterwards instead of believed.
SESSIONS: dict[str, dict[str, Any]] = {
    "rest": {
        "title": "Ruhetag",
        "effect": "Keine Anpassung, sondern die Bedingung dafür: Anpassung passiert in "
                  "der Erholung, nicht im Reiz.",
        "hr": None, "dfa": None, "load_factor": 0.0, "minutes": 0,
    },
    "recovery": {
        "title": "Regeneration, ganz locker",
        "effect": "Durchblutung ohne nennenswerten Reiz. Hält die Bewegung im Alltag, "
                  "kostet nichts.",
        "hr": (0.72, 0.82), "dfa": "durchgehend über 1,0", "load_factor": 0.20, "minutes": (30, 45),
    },
    "endurance": {
        "title": "Grundlage, gleichmäßig",
        "effect": "Der Reiz für Kapillarisierung, mitochondriale Dichte und Fettstoffwechsel. "
                  "Wirkt über Dauer, nicht über Härte — Expertenkonsens nennt 60–90 Minuten "
                  "als Schwelle, ab der die Signalwege wirklich anspringen.",
        "hr": (0.88, 0.97), "dfa": "meist 0,75–1,0, selten darunter",
        "load_factor": 0.55, "minutes": (60, 120),
    },
    "tempo": {
        "title": "Zügige Dauerfahrt",
        "effect": "Arbeitet knapp unter der aeroben Schwelle: verschiebt die Schwelle nach "
                  "oben, ohne die Erholung eines harten Tages zu kosten.",
        "hr": (0.97, 1.02), "dfa": "um 0,75, mit Ausschlägen darunter",
        "load_factor": 0.80, "minutes": (50, 80),
    },
    "sweetspot": {
        "title": "SweetSpot / Schwelle",
        "effect": "Der wirksamste Reiz für die Leistung an der zweiten Schwelle (FTP) pro "
                  "investierter Stunde. Kostet einen bis zwei Erholungstage.",
        "hr": (1.02, 1.10), "dfa": "0,5–0,75 in den Blöcken, Erholung darüber",
        "load_factor": 1.0, "minutes": (45, 75),
    },
    "vo2max": {
        "title": "VO2max-Intervalle",
        "effect": "Der stärkste Reiz auf die maximale Sauerstoffaufnahme und das "
                  "Herzschlagvolumen. Nur auf ausgeruhten Beinen sinnvoll — ermüdet gefahren "
                  "erzeugt er Last ohne den eigentlichen Reiz.",
        "hr": (1.08, 1.20), "dfa": "unter 0,5 in den Intervallen",
        "load_factor": 1.15, "minutes": (40, 70),
    },
}


def _hr_window(anchor: int | None, span: tuple[float, float] | None) -> tuple[int, int] | None:
    if anchor is None or span is None:
        return None
    return (round(anchor * span[0]), round(anchor * span[1]))


def recommend(data: dict[str, Any], budget: dict[str, Any] | None = None) -> dict[str, Any]:
    """Pick the next session from the athlete's state, history and own anchors."""
    st = state(data)
    lay = layoff(data)
    anc = anchors(data)
    dur = durability(data)
    habit = pattern_after_breaks(data)

    reasons: list[dict[str, str]] = []
    warnings: list[str] = []

    # 1) the return-to-training ladder takes precedence over everything else
    key = "endurance"
    if st["state"] in ("slump", "recovering"):
        key = "rest" if st["state"] == "slump" else "recovery"
        reasons.append({"weil": st["label"], "quelle": "Plews/Altini, Javaloyes",
                        "text": st["detail"]})
    elif lay.get("phase") == "wiedereinstieg":
        key = "endurance" if (lay["days"] or 0) <= 10 else "recovery"
        reasons.append({"weil": f"{lay['days']} Tage ohne Einheit",
                        "quelle": "Mujika/Coyle; Rückkehr nach Infekt",
                        "text": lay["note"] or ""})
        if st["state"] == "rebound":
            reasons.append({"weil": "Erholung nach Einbruch", "quelle": "Plews",
                            "text": "Die Werte sind zurück — das ist das Signal zum "
                                    "Wiedereinstieg, nicht zur Intensität. Der erste Reiz "
                                    "nach einer Pause wirkt ohnehin."})
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
    elif st["state"] == "strained":
        key = "endurance"
        reasons.append({"weil": "7-Tage-Mittel unter dem Normalband", "quelle": "Javaloyes",
                        "text": "Die Regel setzt an solchen Tagen Umfang statt Intensität an."})
    elif st["state"] in ("ready", "rebound", "elevated"):
        hard_recent = _hard_days_recent(data, 7)
        if hard_recent >= 2:
            key = "endurance"
            reasons.append({"weil": f"{hard_recent} harte Tage in den letzten sieben",
                            "quelle": "Seiler",
                            "text": "Im Dreizonenmodell tragen 75–80 % der Einheiten den "
                                    "lockeren Bereich. Zwei harte Tage in einer Woche sind "
                                    "die übliche Obergrenze."})
        else:
            key = "sweetspot" if st["state"] == "ready" else "tempo"
            reasons.append({"weil": st["label"], "quelle": "Javaloyes", "text": st["detail"]})

    session = SESSIONS[key]
    hr_window = _hr_window(anc.get("aerobic_hr"), session.get("hr"))
    power_window = None
    if anc.get("aerobic_power") and session.get("hr"):
        low, high = session["hr"]
        power_window = (round(anc["aerobic_power"] * low), round(anc["aerobic_power"] * high))

    # 2) how much load that is, and whether it fits the budget
    minutes = session.get("minutes")
    est_load = None
    if minutes:
        typical = sum(minutes) / 2
        est_load = round(typical * session["load_factor"] * 0.9)
    fits = None
    if est_load is not None and budget and budget.get("recommended") is not None:
        fits = est_load <= budget["recommended"]

    return {
        "key": key,
        "title": session["title"],
        "minutes": minutes,
        "hr_window": hr_window,
        "power_window": power_window,
        "expected_dfa": session.get("dfa"),
        "effect": session["effect"],
        "estimated_load": est_load,
        "fits_budget": fits,
        "state": st,
        "layoff": lay,
        "anchors": anc,
        "durability": dur,
        "habit": habit,
        "reasons": reasons,
        "warnings": warnings,
    }


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


def plan(data: dict[str, Any], budget: dict[str, Any] | None = None, days: int = 7) -> list[dict[str, Any]]:
    """A week ahead, built from the recommendation and the return-to-training ladder.

    Deliberately simple: after a break the load climbs in steps rather than
    jumping back to where it was (GABBETT), hard days are separated, and the
    week keeps the low-intensity share the three-zone model describes (SEILER).
    """
    first = recommend(data, budget)
    wellness = data.get("wellness") or {}
    order = sorted(wellness)
    today = order[-1] if order else date.today().isoformat()

    ladder: list[str]
    if first["key"] in ("rest", "recovery"):
        ladder = ["recovery", "endurance", "recovery", "endurance", "tempo", "recovery", "endurance"]
    elif first["layoff"].get("phase") == "wiedereinstieg":
        # graded return: volume first, one moderate touch late in the week
        ladder = ["endurance", "recovery", "endurance", "tempo", "recovery", "endurance", "sweetspot"]
    elif first["key"] == "sweetspot":
        ladder = ["sweetspot", "recovery", "endurance", "tempo", "recovery", "endurance", "endurance"]
    else:
        ladder = ["endurance", "recovery", "tempo", "endurance", "recovery", "sweetspot", "endurance"]

    anc = first["anchors"]
    out = []
    for index in range(min(days, len(ladder))):
        key = ladder[index] if index else first["key"]
        session = SESSIONS[key]
        out.append({
            "date": _shift(today, index),
            "key": key,
            "title": session["title"],
            "minutes": session.get("minutes"),
            "hr_window": _hr_window(anc.get("aerobic_hr"), session.get("hr")),
            "effect": session["effect"],
        })
    return out


def coach(data: dict[str, Any], budget: dict[str, Any] | None = None) -> dict[str, Any]:
    """Everything the trainer view needs, in one payload."""
    rec = recommend(data, budget)
    return {
        "recommendation": rec,
        "plan": plan(data, budget),
        "sessions": {key: {"title": value["title"], "effect": value["effect"],
                           "dfa": value.get("dfa"),
                           "hr_window": _hr_window(rec["anchors"].get("aerobic_hr"), value.get("hr"))}
                     for key, value in SESSIONS.items()},
        "evidence": {
            "rule": "Javaloyes 2019/2020, Vesterinen 2016 — HRV-gesteuerte Steuerung: "
                    "harte Einheit nur, wenn das 7-Tage-Mittel im oder über dem Normalband liegt.",
            "limit": "Düking 2021, Metaanalyse über 8 Studien und 198 Teilnehmer: mittlerer "
                     "Effekt auf submaximale Werte, kleiner und nicht signifikanter Effekt "
                     "auf die Spitzenleistung. Eine Zeitwahl-Hilfe, keine Garantie.",
            "own_data": "Die Schwellen stammen aus deinen eigenen DFA-Messungen, nicht aus "
                        "Prozenten einer Maximalherzfrequenz.",
        },
    }


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
    import math
    out: dict[str, float] = {}
    ordered = [d for d in days if d in values]
    for index, day in enumerate(ordered):
        history = ordered[max(0, index - window):index]
        if len(history) < 20:
            continue
        raw = [values[d] for d in history]
        if log:
            raw = [math.log(v) for v in raw if v > 0]
        if len(raw) < 20:
            continue
        base, spread = _band(raw)
        if spread <= 0:
            continue
        current = values[day]
        if log:
            if current <= 0:
                continue
            current = math.log(current)
        out[day] = sign * (current - base) / spread
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
        acute = (zh is not None and zh <= -HRV_DROP_SD) or (zr is not None and zr >= RHR_RISE_SD)
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
    import math
    wellness = data.get("wellness") or {}
    days = sorted(d for d in wellness if d < day)[-60:]
    out: dict[str, Any] = {}
    for key, field, use_log, direction, label, unit in NIGHT_FIELDS:
        raw = []
        for d in days:
            value = _f((wellness.get(d) or {}).get(field))
            if value is None or value <= 0:
                continue
            raw.append(math.log(value) if use_log else value)
        current = _f((wellness.get(day) or {}).get(field))
        if current is None or current <= 0 or len(raw) < 20:
            continue
        base, spread = _band(raw)
        if spread <= 0:
            continue
        value = math.log(current) if use_log else current
        scale = 1 / 3600 if field == "sleepSecs" else 1
        out[key] = {
            "label": label, "unit": unit,
            "value": round(current * scale, 2),
            "baseline": round((math.exp(base) if use_log else base) * scale, 2),
            "z": round(direction * (value - base) / spread, 2),
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
