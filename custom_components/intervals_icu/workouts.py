"""Real sessions, not categories.

Every workout here is a protocol from the literature, written in the plain
text syntax Intervals.icu parses, with the study it comes from and the
objection to that study next to it. The power targets are percentages of the
athlete's own FTP, the heart rate windows come from their own measured
aerobic threshold, and the expected DFA alpha-1 band is stated so the session
can be checked afterwards instead of believed.

What the sources actually say, in short:

  RONNESTAD  3 sets of 13 x 30 s work / 15 s recovery, 3 min between sets.
             Over 10 weeks, effort-matched against 4 x 5 min, the short
             intervals produced significantly larger gains in VO2max and
             cycling performance in well-trained cyclists. Work power is
             roughly what can be held for 5 minutes; the 15 s "off" is about
             half that, not a standstill.
  SEILER     4 x 8 min at ~90% of maximal heart rate came out ahead of 4 x 4
             and 4 x 16 in a randomised cycling trial - a middle duration
             that is repeatable.
  HELGERUD   4 x 4 min at 90-95% HRmax with 3 min active recovery; the
             classic protocol, validated in running.
  SWEETSPOT  88-94% FTP, the most threshold adaptation per hour invested.
             Widely used, thinner evidence base than the two above.
  SEILER_Z2  The low-intensity bulk, 75-80% of sessions in trained endurance
             athletes; works through duration, with expert consensus naming
             60-90 minutes as where the signalling really starts.
  CAUTION    The honest objection, from a 2025 review of interval formats:
             protocol names are not prescriptions, time near VO2max is a
             session measure rather than a proven predictor of long-term
             adaptation, and one hard aerobic session per week is a
             conservative starting point.
"""

from __future__ import annotations

from typing import Any

# Each entry: what it is, how it is built, what it should feel like in the
# data afterwards, and where it comes from.
LIBRARY: list[dict[str, Any]] = [
    {
        "key": "z2_60",
        "title": "Grundlage 60 min",
        "purpose": "Aerobe Basis",
        "minutes": 60,
        "intensity": 62,
        "load": 45,
        "blocks": [(10, 55, "Einrollen"), (45, 68, "gleichmäßig"), (5, 50, "Ausrollen")],
        "text": "- 10m 55% 85rpm\n- 45m 65-70% 85rpm\n- 5m 50%",
        "hr_hint": (0.88, 0.97),
        "dfa": "durchgehend über 0,75 — wenn er darunter rutscht, bist du zu schnell",
        "effect": "Kapillarisierung, mitochondriale Dichte, Fettstoffwechsel. Der Reiz "
                  "wirkt über die Dauer, nicht über die Härte.",
        "evidence": "Dreizonenmodell (Seiler): 75–80 % der Einheiten trainierter "
                    "Ausdauersportler liegen unter der ersten Schwelle.",
        "limit": "Expertenkonsens nennt 60–90 Minuten als Bereich, ab dem die Signalwege "
                 "wirklich anspringen — 30 Minuten locker sind Bewegung, kein Reiz.",
        "states": ["ready", "rebound", "strained", "recovering"],
    },
    {
        "key": "z2_90",
        "title": "Grundlage 90 min",
        "purpose": "Aerobe Basis, lange Variante",
        "minutes": 95,
        "intensity": 63,
        "load": 72,
        "blocks": [(10, 55, "Einrollen"), (80, 68, "gleichmäßig"), (5, 50, "Ausrollen")],
        "text": "- 10m 55% 85rpm\n- 80m 65-70% 85rpm\n- 5m 50%",
        "hr_hint": (0.88, 0.97),
        "dfa": "über 0,75; ein langsames Absinken gegen Ende ist die Ermüdung, "
               "die du hier trainierst",
        "effect": "Wie oben, plus Ermüdungswiderstand: erst ab dieser Dauer wird "
                  "trainiert, wie lange die Grundlage trägt.",
        "evidence": "Seiler; Entkopplung nach Friel (≤ 5 %) ist das Maß dafür, ob sie trägt.",
        "limit": "Nur sinnvoll, wenn Zeit und Erholung da sind — sonst ist die kurze "
                 "Variante die bessere Wahl.",
        "states": ["ready", "rebound"],
    },
    {
        "key": "tempo_2x20",
        "title": "Tempo 2×20 min",
        "purpose": "Aerobe Schwelle anheben",
        "minutes": 65,
        "intensity": 75,
        "load": 62,
        "blocks": [(12, 55, "Einrollen"), (20, 80, "Block 1"), (5, 55, "Pause"),
                   (20, 80, "Block 2"), (8, 50, "Ausrollen")],
        "text": "- 12m 55% 85rpm\n\n2x\n- 20m 78-82% 85rpm\n- 5m 55%\n\n- 8m 50%",
        "hr_hint": (0.97, 1.02),
        "dfa": "um 0,75 pendelnd — genau die Grenze, die du hier verschiebst",
        "effect": "Arbeitet dicht unter der aeroben Schwelle: verschiebt sie nach oben, "
                  "ohne die Erholung eines harten Tages zu kosten.",
        "evidence": "Der Bereich zwischen erster und zweiter Schwelle; bei dir direkt an "
                    "der gemessenen DFA-Schwelle verankert.",
        "limit": "Der vielzitierte „Graubereich“ — zu hart für Erholung, zu weich für "
                 "einen VO2max-Reiz. Als eigenständiger Reiz gut, als Dauerkost nicht.",
        "states": ["ready", "rebound"],
    },
    {
        "key": "sweetspot_2x20",
        "title": "SweetSpot 2×20 min",
        "purpose": "Schwellenleistung",
        "minutes": 70,
        "intensity": 83,
        "load": 78,
        "blocks": [(12, 55, "Einrollen"), (20, 90, "Block 1"), (6, 55, "Pause"),
                   (20, 90, "Block 2"), (8, 50, "Ausrollen")],
        "text": "- 12m 55% 85rpm\n\n2x\n- 20m 88-93% 88rpm\n- 6m 55%\n\n- 8m 50%",
        "hr_hint": (1.02, 1.08),
        "dfa": "0,5–0,75 in den Blöcken, in den Pausen wieder darüber",
        "effect": "Der beste Zuwachs an Schwellenleistung pro investierter Stunde. "
                  "Kostet ein bis zwei Erholungstage.",
        "evidence": "88–94 % FTP, weit verbreitete Praxis.",
        "limit": "Dünnere Studienlage als 30/15 oder 4×8 — viel Erfahrung, wenig "
                 "kontrollierter Vergleich.",
        "states": ["ready"],
    },
    {
        "key": "threshold_3x12",
        "title": "Schwelle 3×12 min",
        "purpose": "FTP",
        "minutes": 72,
        "intensity": 87,
        "load": 85,
        "blocks": [(15, 55, "Einrollen"), (12, 98, "Block 1"), (6, 50, "Pause"),
                   (12, 98, "Block 2"), (6, 50, "Pause"), (12, 98, "Block 3"), (9, 50, "Ausrollen")],
        "text": "- 15m 55% 85rpm\n\n3x\n- 12m 95-100% 90rpm\n- 6m 50%\n\n- 9m 50%",
        "hr_hint": (1.05, 1.12),
        "dfa": "um 0,5 in den Blöcken — die anaerobe Schwelle",
        "effect": "Arbeitet an der zweiten Schwelle selbst: Laktattoleranz und die "
                  "Leistung, die du eine Stunde halten kannst.",
        "evidence": "Klassische Schwellenarbeit; DFA alpha-1 0,5 markiert nach "
                    "Rogers/Gronwald die anaerobe Schwelle.",
        "limit": "Hohe Last bei mäßigem VO2max-Reiz — als einzige harte Einheit der "
                 "Woche verschenkt sie Potenzial.",
        "states": ["ready"],
    },
    {
        "key": "vo2_4x8",
        "title": "VO2max 4×8 min",
        "purpose": "Maximale Sauerstoffaufnahme",
        "minutes": 67,
        "intensity": 90,
        "load": 95,
        "blocks": [(15, 55, "Einrollen"), (8, 106, "1"), (4, 50, "Pause"), (8, 106, "2"),
                   (4, 50, "Pause"), (8, 106, "3"), (4, 50, "Pause"), (8, 106, "4"), (8, 50, "Ausrollen")],
        "text": "- 15m 55% 85rpm\n\n4x\n- 8m 103-108% 90rpm\n- 4m 50%\n\n- 8m 50%",
        "hr_hint": (1.08, 1.16),
        "dfa": "deutlich unter 0,5 in den Blöcken",
        "effect": "Lange Intervalle an der Grenze: viel Zeit nahe der maximalen "
                  "Sauerstoffaufnahme bei beherrschbarer Spitzenbelastung.",
        "evidence": "Seiler 2013, randomisierter Vergleich bei Radfahrern: 4×8 min kam "
                    "vor 4×4 und 4×16 heraus.",
        "limit": "Nur ausgeruht sinnvoll. Ermüdet gefahren erzeugt die Einheit Last "
                 "ohne den eigentlichen Reiz.",
        "states": ["ready"],
    },
    {
        "key": "vo2_3015",
        "title": "30/15 nach Rønnestad",
        "purpose": "Maximale Sauerstoffaufnahme, kurze Intervalle",
        "minutes": 62,
        "intensity": 92,
        "load": 98,
        "blocks": [(15, 55, "Einrollen"), (10, 112, "Satz 1"), (3, 45, "Satzpause"),
                   (10, 112, "Satz 2"), (3, 45, "Satzpause"), (10, 112, "Satz 3"), (8, 50, "Ausrollen")],
        "text": ("- 15m 55% 85rpm\n\n3x\n13x\n- 30s 110-115% 95rpm\n- 15s 55%\n\n- 3m 45%\n\n- 8m 50%"),
        "hr_hint": (1.08, 1.18),
        "dfa": "unter 0,5, in den 15-Sekunden-Pausen kaum Erholung — das ist Absicht",
        "effect": "Hält dich länger nahe der maximalen Sauerstoffaufnahme als gleich "
                  "harte lange Intervalle, weil die Pausen zu kurz zum Absinken sind.",
        "evidence": "Rønnestad: 3 Sätze à 13×30 s / 15 s, über 10 Wochen gegen "
                    "aufwandsgleiche 4×5 min — signifikant größere Zuwächse bei VO2max "
                    "und Radleistung bei gut trainierten Fahrern.",
        "limit": "Protokollnamen sind keine Verschreibungen: die Zeit nahe VO2max ist ein "
                 "Sitzungsmaß, kein bewiesener Prädiktor langfristiger Anpassung. Und "
                 "die Leistung muss sitzen — zu hart begonnen bricht der dritte Satz weg.",
        "states": ["ready"],
    },
    {
        "key": "recovery_40",
        "title": "Regeneration 40 min",
        "purpose": "Durchblutung",
        "minutes": 40,
        "intensity": 45,
        "load": 18,
        "blocks": [(40, 50, "ganz locker")],
        "text": "- 40m 45-55% 80rpm",
        "hr_hint": (0.72, 0.82),
        "dfa": "durchgehend über 1,0",
        "effect": "Bewegung ohne nennenswerten Reiz. Kostet nichts und hält den Rhythmus.",
        "evidence": "Die lockere Seite des Dreizonenmodells.",
        "limit": "Zu locker, um zu trainieren — das ist der Zweck, nicht der Mangel.",
        "states": ["recovering", "rebound", "strained", "ready", "slump"],
    },
    {
        "key": "return_45",
        "title": "Wiedereinstieg 45 min",
        "purpose": "Rückkehr nach Pause oder Infekt",
        "minutes": 45,
        "intensity": 58,
        "load": 32,
        "blocks": [(10, 50, "Einrollen"), (30, 62, "ruhig"), (5, 45, "Ausrollen")],
        "text": "- 10m 50% 85rpm\n- 30m 58-65% 85rpm\n- 5m 45%",
        "hr_hint": (0.85, 0.94),
        "dfa": "über 0,75 halten — fällt er darunter, obwohl die Watt stimmen, ist der "
               "Körper noch nicht zurück",
        "effect": "Setzt den Reiz, der nach einer Pause ohnehin wirkt, ohne Spitzen. "
                  "Gleichzeitig eine Messung: Puls bei gewohnter Leistung.",
        "evidence": "Stufenweise Rückkehr nach Infekt; nach bis zu zwei Wochen Pause ist "
                    "der Verlust überwiegend Plasmavolumen (Mujika/Coyle) und in wenigen "
                    "Einheiten zurück.",
        "limit": "Bei wiederkehrenden Symptomen abbrechen. Systemische Infektion plus "
                 "harte Belastung ist die eine Kombination mit ernstem Risiko.",
        "states": ["rebound", "recovering", "strained", "ready"],
    },
]

BY_KEY = {entry["key"]: entry for entry in LIBRARY}

# Which sessions fit which state, hardest first - the picker walks this list.
PRIORITY: dict[str, list[str]] = {
    "slump": ["recovery_40"],
    "recovering": ["recovery_40", "return_45"],
    "rebound": ["return_45", "z2_60", "recovery_40"],
    "strained": ["z2_60", "recovery_40", "tempo_2x20"],
    "ready": ["vo2_3015", "vo2_4x8", "sweetspot_2x20", "threshold_3x12", "tempo_2x20", "z2_90", "z2_60"],
    "elevated": ["z2_60", "tempo_2x20", "recovery_40"],
    "unknown": ["z2_60", "recovery_40"],
}


def scaled(entry: dict[str, Any], ftp: float | None, aerobic_hr: int | None) -> dict[str, Any]:
    """Fill in the athlete's own numbers: watts from FTP, heart rate from the
    measured aerobic threshold. Without those the shape still stands."""
    out = dict(entry)
    if ftp:
        out["blocks_w"] = [(minutes, round(ftp * pct / 100), label)
                           for minutes, pct, label in entry["blocks"]]
    if aerobic_hr and entry.get("hr_hint"):
        low, high = entry["hr_hint"]
        out["hr_window"] = (round(aerobic_hr * low), round(aerobic_hr * high))
    return out


def suggest(state: str, ftp: float | None = None, aerobic_hr: int | None = None,
            budget: float | None = None, hard_days_last_7: int = 0,
            layoff_days: int | None = None, limit: int = 3) -> list[dict[str, Any]]:
    """Return concrete sessions for today, best first, each with a reason.

    The order is not taste: after a break or in a slump the ladder decides, a
    second hard day inside a week is filtered out (one hard aerobic session a
    week is the conservative starting point the reviews name), and anything
    clearly over the load budget is marked rather than hidden.
    """
    keys = PRIORITY.get(state, PRIORITY["unknown"])
    if layoff_days is not None and layoff_days >= 4 and state != "slump":
        keys = ["return_45", "z2_60", "recovery_40"]
    if hard_days_last_7 >= 2:
        keys = [k for k in keys if BY_KEY[k]["intensity"] < 80] or ["z2_60"]

    out: list[dict[str, Any]] = []
    for key in keys[:limit]:
        entry = scaled(BY_KEY[key], ftp, aerobic_hr)
        entry = dict(entry)
        entry["fits_budget"] = None if budget is None else entry["load"] <= budget
        out.append(entry)
    return out


DEFAULT_NOTE = "Vorgeschlagen von Home Assistant"


def to_event(entry: dict[str, Any], day: str, sport: str = "Ride",
             note: str | None = DEFAULT_NOTE) -> dict[str, Any]:
    """Turn a workout into the payload Intervals.icu accepts on its calendar.

    The steps go into `description` in the plain text syntax Intervals parses
    into a structured workout - the same route the web UI uses, and the one
    confirmed working in the forum. `workout_doc` stays empty on purpose:
    letting Intervals do the parsing means one format to get right, not two.

    The note defaults to a line naming where the entry came from: an event
    that appears in someone's calendar should say who put it there. Pass
    note=None to leave it out.
    """
    description = entry["text"]
    if note:
        description = f"{note}\n\n{description}"
    return {
        "category": "WORKOUT",
        "start_date_local": f"{day}T00:00:00",
        "type": sport,
        "name": entry["title"],
        "description": description,
        "moving_time": int(entry["minutes"] * 60),
        "icu_training_load": int(entry["load"]),
        "target": "POWER",
        "workout_doc": {},
    }
