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

import re
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
        "key": "z2_150",
        "title": "Lange Grundlage 2,5 h",
        "purpose": "Ermüdungswiderstand",
        "minutes": 150,
        "intensity": 63,
        "load": 115,
        "blocks": [(12, 55, "Einrollen"), (130, 67, "gleichmäßig"), (8, 50, "Ausrollen")],
        "text": "- 12m 55% 85rpm\n- 130m 64-70% 85rpm\n- 8m 50%",
        "hr_hint": (0.88, 0.97),
        "dfa": "über 0,75; sinkt er im letzten Drittel, ist die Grundlage am Ende",
        "effect": "Ab dieser Dauer wird trainiert, wie lange die Grundlage trägt — "
                  "Fettoxidation, Ermüdungswiderstand, Widerstand gegen Muskelschaden.",
        "evidence": "Durability nach Maunder: Zeitpunkt und Ausmaß der Verschlechterung "
                    "während langer Belastung. Eine eigene Eigenschaft, unabhängig von FTP.",
        "limit": "Durchgehend verpflegen. Der Reiz soll aus der Belastung kommen, nicht "
                 "aus leeren Speichern — das ist der häufigste Fehler bei langen Einheiten.",
        "states": ["ready", "rebound"],
    },
    {
        "key": "z2_210_late",
        "title": "Lange Fahrt 3,5 h mit Endblock",
        "purpose": "Durability, spezifisch",
        "minutes": 210,
        "intensity": 68,
        "load": 175,
        "blocks": [(12, 55, "Einrollen"), (150, 67, "gleichmäßig"), (10, 88, "Endblock 1"),
                   (5, 55, "locker"), (10, 88, "Endblock 2"), (23, 50, "Ausrollen")],
        "text": ("- 12m 55% 85rpm\n- 150m 64-70% 85rpm\n\n2x\n- 10m 86-90% 88rpm\n"
                 "- 5m 55%\n\n- 23m 50%"),
        "hr_hint": (0.88, 1.05),
        "dfa": "über 0,75 im Hauptteil, in den Endblöcken um 0,6 — im ermüdeten Zustand",
        "effect": "Qualität am ENDE der langen Fahrt: genau der Zustand, den eine "
                  "Sechsstundenfahrt im letzten Drittel verlangt.",
        "evidence": "Ab etwa sechs bis acht Wochen vor dem Ziel gehört harte Arbeit ans "
                    "Ende der langen Fahrt — ein frischer Intervallblock trainiert nicht, "
                    "was nach Stunden gebraucht wird.",
        "limit": "Die teuerste Einheit im Katalog. Nur mit grünem Zustand und mindestens "
                 "zwei ruhigen Tagen davor.",
        "states": ["ready"],
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
        "evidence": "Rønnestad: 3 Sätze à 13×30 s / 15 s, über 10 Wochen gegen 4×5 min — "
                    "signifikant größere Zuwächse bei VO2max und Radleistung bei gut "
                    "trainierten Fahrern.",
        "limit": "Oft wird der Vergleich als aufwandsgleich zitiert — er ist es nicht: "
                 "3×13×30/15 sind 29,5 Minuten Arbeit gegen 20 Minuten bei 4×5. Ein Teil "
                 "des Vorsprungs ist schlicht mehr Arbeit. Dazu: Protokollnamen sind keine "
                 "Verschreibungen, und die Leistung muss sitzen — zu hart begonnen bricht "
                 "der dritte Satz weg.",
        "states": ["ready"],
    },
    {
        "key": "vo2_4x4",
        "title": "VO2max 4×4 min",
        "purpose": "Maximale Sauerstoffaufnahme",
        "minutes": 58,
        "intensity": 89,
        "load": 82,
        "blocks": [(15, 55, "Einrollen"), (4, 110, "1"), (4, 50, "Pause"), (4, 110, "2"),
                   (4, 50, "Pause"), (4, 110, "3"), (4, 50, "Pause"), (4, 110, "4"), (11, 50, "Ausrollen")],
        "text": "- 15m 55% 85rpm\n\n4x\n- 4m 106-110% 95rpm\n- 4m 50%\n\n- 11m 50%",
        "hr_hint": (1.06, 1.15),
        "dfa": "unter 0,5 in den Blöcken",
        "effect": "Der Einstieg in die VO2max-Arbeit: kurz genug, um sauber durchzukommen, "
                  "lang genug für den Reiz.",
        "evidence": "Das am häufigsten untersuchte Format; als Einstiegsdosis vor 5×4 und "
                    "30/15 empfohlen.",
        "limit": "Wer den letzten Block nicht mit derselben Leistung schafft, ist zu hart "
                 "gestartet — beim nächsten Mal 2 bis 3 % niedriger ansetzen.",
        "states": ["ready"],
    },
    {
        "key": "vo2_5x4",
        "title": "VO2max 5×4 min",
        "purpose": "Maximale Sauerstoffaufnahme",
        "minutes": 66,
        "intensity": 91,
        "load": 92,
        "blocks": [(15, 55, "Einrollen"), (4, 112, "1"), (4, 50, "Pause"), (4, 112, "2"),
                   (4, 50, "Pause"), (4, 112, "3"), (4, 50, "Pause"), (4, 112, "4"),
                   (4, 50, "Pause"), (4, 112, "5"), (11, 50, "Ausrollen")],
        "text": "- 15m 55% 85rpm\n\n5x\n- 4m 108-112% 95rpm\n- 4m 50%\n\n- 11m 50%",
        "hr_hint": (1.07, 1.16),
        "dfa": "unter 0,5, gegen Ende deutlich",
        "effect": "Die Steigerung gegenüber 4×4: 20 statt 16 Minuten Arbeitszeit.",
        "evidence": "Als Progression nach zwei Wochen 4×4 beschrieben; als Startdosis gilt "
                    "5×4 bei 110–115 % FTP mit vier Minuten locker.",
        "limit": "Ist der fünfte Block fast unmöglich, stimmt die Leistung. Sind alle "
                 "beherrschbar, darf sie beim nächsten Mal 5 % höher liegen.",
        "states": ["ready"],
    },
    {
        "key": "vo2_3030",
        "title": "30/30 nach Billat",
        "purpose": "Maximale Sauerstoffaufnahme, kurze Intervalle",
        "minutes": 56,
        "intensity": 87,
        "load": 78,
        "blocks": [(15, 55, "Einrollen"), (10, 105, "Satz 1"), (4, 45, "Satzpause"),
                   (10, 105, "Satz 2"), (4, 45, "Satzpause"), (10, 105, "Satz 3"), (3, 50, "Ausrollen")],
        "text": "- 15m 55% 85rpm\n\n3x\n10x\n- 30s 100-110% 95rpm\n- 30s 50%\n\n- 4m 45%\n\n- 3m 50%",
        "hr_hint": (1.05, 1.14),
        "dfa": "um 0,5 schwankend — die 30 Sekunden Pause reichen für eine Teilerholung",
        "effect": "In der halben Pause bleibt der Stoffwechsel oben: aus 30 Sekunden Arbeit "
                  "wird rund eine Minute nahe der maximalen Sauerstoffaufnahme.",
        "evidence": "Billat-Protokoll; als Ziel gelten 16 bis 36 Minuten Gesamtarbeit.",
        "limit": "Mit steigender Form stößt man an eine Decke — dann liegt man "
                 "stoffwechselseitig eher an der Schwelle als bei VO2max, und es ist Zeit "
                 "für ein anderes Format.",
        "states": ["ready"],
    },
    {
        "key": "threshold_4x10",
        "title": "Schwelle 4×10 min",
        "purpose": "FTP, Einstiegsdosis",
        "minutes": 78,
        "intensity": 85,
        "load": 78,
        "blocks": [(15, 55, "Einrollen"), (10, 97, "1"), (5, 50, "Pause"), (10, 97, "2"),
                   (5, 50, "Pause"), (10, 97, "3"), (5, 50, "Pause"), (10, 97, "4"), (8, 50, "Ausrollen")],
        "text": "- 15m 55% 85rpm\n\n4x\n- 10m 95-100% 90rpm\n- 5m 50%\n\n- 8m 50%",
        "hr_hint": (1.04, 1.11),
        "dfa": "um 0,5 in den Blöcken",
        "effect": "Dieselbe Zeit an der Schwelle wie 2×20, aber in kürzeren Stücken — "
                  "leichter sauber zu fahren.",
        "evidence": "Die empfohlene Progression lautet: erst Häufigkeit, dann Dauer "
                    "(4×10 → 3×15 → 2×20), erst zuletzt Intensität.",
        "limit": "Wer im zweiten Block schon 15 Watt verliert, ist noch nicht bei 2×20.",
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
    "rebound": ["return_45", "z2_60", "z2_90", "recovery_40"],
    "strained": ["z2_60", "z2_90", "recovery_40", "tempo_2x20"],
    "ready": ["vo2_4x4", "vo2_5x4", "vo2_3015", "vo2_3030", "vo2_4x8", "threshold_4x10",
              "threshold_3x12", "sweetspot_2x20", "tempo_2x20", "z2_90", "z2_60"],
    "elevated": ["z2_60", "tempo_2x20", "recovery_40"],
    "unknown": ["z2_60", "recovery_40"],
}


def _text_in_watts(entry: dict[str, Any], ftp: float) -> str:
    """Rewrite the Intervals steps from percentages into absolute watts."""
    def swap(match: "re.Match[str]") -> str:
        low, high = match.group(1), match.group(3)
        if high:
            return f"{round(ftp * int(low) / 100)}-{round(ftp * int(high) / 100)}w"
        return f"{round(ftp * int(low) / 100)}w"

    import re as _re
    return _re.sub(r"(\d+)(-(\d+))?%", swap, entry["text"])


def scaled(entry: dict[str, Any], ftp: float | None, aerobic_hr: int | None,
           max_hr: float | None = None) -> dict[str, Any]:
    """Fill in the athlete's own numbers: watts from FTP, heart rate from the
    measured aerobic threshold. Without those the shape still stands."""
    out = dict(entry)
    if ftp:
        out["blocks_w"] = [(minutes, round(ftp * pct / 100), label)
                           for minutes, pct, label in entry["blocks"]]
        out["text_w"] = _text_in_watts(entry, ftp)
    if aerobic_hr and entry.get("hr_hint"):
        low, high = entry["hr_hint"]
        lo, hi = round(aerobic_hr * low), round(aerobic_hr * high)
        # The hint scales the AEROBIC threshold. For the hard families that
        # extrapolation can pass the athlete's measured maximum - and a heart
        # rate window above the maximum is not a window. Clamp it, and drop it
        # entirely when even its floor sits at the ceiling.
        if max_hr:
            hi = min(hi, round(max_hr))
            if lo >= round(max_hr):
                lo = hi + 1
        if lo <= hi:
            out["hr_window"] = (lo, hi)
    return out


# One entry per FAMILY, so the choice is between different kinds of training
# rather than between three base rides. Within a family the variant is picked
# to fit the athlete and the day.
FAMILIES: list[tuple[str, str, list[str]]] = [
    ("recovery", "Regeneration", ["recovery_40"]),
    ("endurance", "Grundlage", ["z2_90", "z2_60"]),
    ("long", "Lange Fahrt", ["z2_210_late", "z2_150"]),
    ("tempo", "Tempo", ["tempo_2x20"]),
    ("sweetspot", "SweetSpot", ["sweetspot_2x20"]),
    ("threshold", "Schwelle", ["threshold_4x10", "threshold_3x12"]),
    ("vo2max", "VO2max", ["vo2_4x4", "vo2_5x4", "vo2_3030", "vo2_3015", "vo2_4x8"]),
    ("return", "Wiedereinstieg", ["return_45"]),
]

# What each state can carry. Not a filter - a verdict per family, so every kind
# of session stays visible and says what it would cost today.
FIT_BY_STATE: dict[str, dict[str, str]] = {
    "slump":      {"recovery": "ok", "return": "maybe", "endurance": "no", "long": "no",
                   "tempo": "no", "sweetspot": "no", "threshold": "no", "vo2max": "no"},
    "recovering": {"recovery": "ok", "return": "ok", "endurance": "maybe", "long": "no",
                   "tempo": "no", "sweetspot": "no", "threshold": "no", "vo2max": "no"},
    "rebound":    {"recovery": "ok", "return": "ok", "endurance": "ok", "long": "maybe",
                   "tempo": "maybe", "sweetspot": "maybe", "threshold": "no", "vo2max": "no"},
    "strained":   {"recovery": "ok", "return": "ok", "endurance": "ok", "long": "maybe",
                   "tempo": "maybe", "sweetspot": "maybe", "threshold": "no", "vo2max": "no"},
    "ready":      {"recovery": "ok", "return": "ok", "endurance": "ok", "long": "ok",
                   "tempo": "ok", "sweetspot": "ok", "threshold": "ok", "vo2max": "ok"},
    "elevated":   {"recovery": "ok", "return": "ok", "endurance": "ok", "long": "maybe",
                   "tempo": "maybe", "sweetspot": "maybe", "threshold": "no", "vo2max": "no"},
    "unknown":    {"recovery": "ok", "return": "ok", "endurance": "ok", "long": "maybe",
                   "tempo": "maybe", "sweetspot": "maybe", "threshold": "maybe", "vo2max": "maybe"},
}

FIT_REASON = {
    "slump": "Der Einbruch ist akut — ein harter Reiz trifft heute auf ein System, das ihn "
             "nicht verarbeitet.",
    "recovering": "Noch im Einbruch. Intensität verlängert ihn, statt zu wirken.",
    "rebound": "Die Erholung läuft, aber die letzten Tage tragen noch keinen harten Reiz.",
    "strained": "Beansprucht — Umfang ja, Intensität kostet heute mehr, als sie bringt.",
    "elevated": "Auffällig hohe Werte. Erst sehen, ob das morgen noch so ist.",
    "unknown": "Zu wenige Daten für ein Urteil — nach Gefühl entscheiden.",
}


# --- the four grades (docs/ausbau.md I3, I5) -----------------------------------
# ONE place decides the grade, for BOTH views. Until 0.41.0 the trainer tab
# combined state and budget in the FRONTEND (`fit === "ok" && fits_budget ===
# false` -> amber) while the backend handed over the two halves separately.
# Putting the four grades in the backend and leaving that in place would have
# been two rules in the house - error class 3, the one thing this package rules
# out. So: decided here, carried in the payload, read by the panel.
#
# The grades are a JUDGEMENT register, four words, four shapes, four tones.
# They never mix with the category register (sport, purpose, label).
STAGES: dict[str, dict[str, str]] = {
    "green": {
        "label": "grün",
        "word": "passt",
        "detail": "Zustand unauffällig, die Last passt ins Budget.",
    },
    "yellow": {
        "label": "gelb",
        "word": "geht, kostet aber",
        "detail": "Der Zustand trägt nur bedingt. Die Einheit ist möglich, sie kostet heute "
                  "mehr als sonst.",
    },
    "stimulus": {
        "label": "Reiz",
        "word": "kostet Erholung, setzt aber den Reiz",
        "detail": "Über dem Lastbudget, aber der Zustand trägt und die letzten Tage boten "
                  "Erholung. Das ist funktionelles Überreichen: ein kurzer gewollter "
                  "Einbruch, der nach Erholung in Superkompensation mündet.",
    },
    "red": {
        "label": "rot",
        "word": "heute nicht",
        "detail": "Zustand oder Budget sprechen dagegen.",
    },
}

# The one place the objection to the stimulus grade is written down. It travels
# with every stimulus verdict - "dosiert dazu" is the statement, not "je öfter,
# desto besser".
STIMULUS_EVIDENCE = (
    "Funktionelles Überreichen, Konsenspapier Meeusen 2013 (ECSS/ACSM): ein kurzer "
    "gewollter Einbruch mündet nach Erholung in Superkompensation. Die Grenze gehört "
    "dazu — neuere Arbeiten finden bei überreichten Athleten teils SCHWÄCHERE "
    "Anpassungen. Dosiert dazu, nicht je öfter desto besser."
)

BLOCKED_BY = {
    "state": ("Der Zustand", "verbietet"),
    "budget": ("Das Lastbudget", "verbietet"),
    "both": ("Zustand und Lastbudget", "verbieten"),
}


def fit_for(family_key: str, state: str, intensity: float,
            hard_days_last_7: int = 0, layoff_days: int | None = None,
            infection: bool = False) -> tuple[str, str]:
    """What the STATE says about a family today - one rule, both views.

    Pulled out of `suggest()` in 0.42.0 so the week view can ask the same
    question about a planned session without restating the modifiers. Two
    copies of this ladder would have been the second state rule the package
    forbids; the grade in `stage()` sits on top of the answer given here.
    """
    fits = FIT_BY_STATE.get(state, FIT_BY_STATE["unknown"])
    verdict = fits.get(family_key, "maybe")
    # a second hard day inside the week downgrades, it does not hide
    if verdict == "ok" and intensity >= 80 and hard_days_last_7 >= 2:
        verdict = "maybe"
        reason = ("Zwei harte Tage liegen schon in dieser Woche. Zwei sind der Standard "
                  "für Wochen dieser Größe; ein dritter ist die Ausnahme, nicht die Regel.")
    else:
        reason = "" if verdict == "ok" else FIT_REASON.get(state, "")
    # after a real break the base ride stays on the table, judged - the
    # graded return is the better first step, not the only visible one
    if family_key == "endurance" and layoff_days and layoff_days >= 7 and verdict == "ok":
        verdict = "maybe"
        reason = (f"{layoff_days} Tage ohne Einheit — der abgestufte Wiedereinstieg ist "
                  "der bessere erste Schritt. Grundlage bleibt möglich, nur nicht als Sprung.")
    # infection pattern: the way back is a ladder of easy sessions, and the
    # next rung only without returning symptoms (return-to-sport practice,
    # a convention - marked as such, not a study rule)
    if infection and state in ("recovering", "rebound") and family_key not in ("recovery", "return"):
        if family_key == "endurance":
            if verdict == "ok":
                verdict = "maybe"
                reason = ("Infektmuster in den Signalen: erst mehrere lockere Einheiten "
                          "ohne Symptomrückkehr, dann die nächste Stufe "
                          "(Return-to-Sport-Praxis, eine Konvention).")
        else:
            # also for families the state already blocks: under the infection
            # pattern the ladder IS the reason, not the state
            verdict = "no"
            reason = ("Infektmuster in den Signalen: der Weg zurück ist eine Leiter über "
                      "mehrere lockere Einheiten — Intensität erst, wenn Stufen ohne "
                      "Symptomrückkehr gehalten wurden (Return-to-Sport-Praxis, eine "
                      "Konvention).")
    return verdict, reason


def session_load(entry: dict[str, Any], hours: float | None = None) -> int:
    """The load of a session AS PLANNED, not as catalogued.

    The plan calls the big day "5.0 h" and hands over `z2_210_late` - 210
    minutes, load 175. Judging the five-hour ride by the catalogue entry
    measures a three-and-a-half-hour ride instead, and does so at exactly the
    session the long-ride goal is about: systematically too green.

    At constant intensity load scales linearly with duration (load is an
    intensity-squared times hours quantity, and the intensity of the template
    does not change when the ride gets longer), so the catalogue load is
    stretched by the ratio of the hours. Without hours the catalogue entry IS
    the session and stands unchanged.
    """
    base = float(entry.get("load") or 0)
    minutes = float(entry.get("minutes") or 0)
    if not hours or minutes <= 0:
        return round(base)
    return round(base * (float(hours) * 60.0) / minutes)


def stage(fit: str, fits_budget: bool | None, recovery: bool = False) -> dict[str, Any]:
    """The one rule that turns state + budget into one of four grades.

    Total over its inputs, and deliberately small: every caller - the session
    list for today, the current week of the plan - asks THIS function and
    prints what it gets back. A threshold in the frontend would be the second
    rule the package forbids.

    `fits_budget` may be None: below 28 days of history there is no budget at
    all. An unknown budget blocks nothing - and it cannot be exceeded either,
    so the stimulus grade needs a budget that actually exists.
    """
    over_budget = fits_budget is False
    if fit == "no":
        key, blocked = "red", "both" if over_budget else "state"
    elif over_budget:
        if fit == "ok" and recovery:
            key, blocked = "stimulus", None
        else:
            key, blocked = "red", "budget" if fit == "ok" else "both"
    elif fit == "maybe":
        key, blocked = "yellow", None
    else:
        key, blocked = "green", None

    out = {"key": key, "blocked_by": blocked, **STAGES[key]}
    if blocked:
        subject, verb = BLOCKED_BY[blocked]
        out["detail"] = f"{subject} {verb} es heute."
    if key == "stimulus":
        out["evidence"] = STIMULUS_EVIDENCE
    return out


def _variant(keys: list[str], state: str, ftp: float | None, budget: float | None,
             hard_days_last_7: int) -> str:
    """Pick the variant of a family that fits this athlete today.

    Within VO2max that is a real decision: 4x4 is the entry dose, 5x4 its
    progression, 30/15 is for well-trained riders only. A second hard day in
    the same week takes the biggest one off the table.
    """
    if len(keys) == 1:
        return keys[0]
    if budget is not None:
        affordable = [k for k in keys if BY_KEY[k]["load"] <= budget]
        if affordable:
            keys = affordable
    if hard_days_last_7 >= 1:
        keys = sorted(keys, key=lambda k: BY_KEY[k]["load"])
    return keys[0]


def suggest(state: str, ftp: float | None = None, aerobic_hr: int | None = None,
            max_hr: float | None = None, infection: bool = False,
            budget: float | None = None, hard_days_last_7: int = 0,
            layoff_days: int | None = None, limit: int = 8,
            goal: str | None = None,
            recovery_offered: bool = False) -> list[dict[str, Any]]:
    """One session per family, each judged for today - never filtered away.

    The earlier version filtered: in a rebound state everything hard vanished
    and three base rides were left, which is not a choice. This keeps every
    kind of session visible and attaches the verdict to it, because the
    decision is the athlete's; the data's job is to say what it costs.
    """
    order = {
        "long_ride": ["long", "endurance", "sweetspot", "tempo", "threshold", "vo2max", "recovery", "return"],
        "ftp": ["threshold", "sweetspot", "endurance", "vo2max", "tempo", "long", "recovery", "return"],
        "vo2max": ["vo2max", "threshold", "endurance", "sweetspot", "tempo", "long", "recovery", "return"],
        "health": ["endurance", "tempo", "recovery", "sweetspot", "threshold", "vo2max", "long", "return"],
    }.get(goal or "", ["endurance", "vo2max", "sweetspot", "threshold", "tempo", "long", "recovery", "return"])

    out: list[dict[str, Any]] = []
    for family in order:
        match = next((f for f in FAMILIES if f[0] == family), None)
        if not match:
            continue
        family_key, family_label, keys = match
        # the graded return only EXISTS after a real break - adding it is not
        # filtering. The base ride, by contrast, is never hidden: after a long
        # break it stays visible and gets judged (see below).
        if family_key == "return" and not (layoff_days and layoff_days >= 4):
            continue

        key = _variant(keys, state, ftp, budget, hard_days_last_7)
        entry = dict(scaled(BY_KEY[key], ftp, aerobic_hr, max_hr))
        verdict, reason = fit_for(
            family_key, state, entry["intensity"],
            hard_days_last_7=hard_days_last_7, layoff_days=layoff_days,
            infection=infection,
        )
        fits_budget = None if budget is None else entry["load"] <= budget
        entry.update({
            "family": family_key, "family_label": family_label,
            "fit": verdict, "fit_reason": reason,
            "fits_budget": fits_budget,
            # the grade the panel prints - decided HERE, never in the frontend
            "stage": stage(verdict, fits_budget, recovery_offered),
            "alternatives": [{"key": k, "title": BY_KEY[k]["title"], "load": BY_KEY[k]["load"]}
                             for k in keys if k != key],
        })
        out.append(entry)
        if len(out) >= limit:
            break
    return out


FAMILY_OF_KEY: dict[str, str] = {
    key: family for family, _label, keys in FAMILIES for key in keys
}

NO_VERDICT_NOTE = (
    "Bewertet wird erst in der Woche selbst. Das Lastbudget rechnet aus den letzten "
    "sechs Tagen, der Zustand aus den Werten von heute — Budget und Zustand von "
    "übernächstem Donnerstag kennt niemand, auch dieses Panel nicht."
)


def rate_sessions(sessions: list[dict[str, Any]], state: str,
                  budget: float | None = None, recovery_offered: bool = False,
                  hard_days_last_7: int = 0, layoff_days: int | None = None,
                  infection: bool = False, ftp: float | None = None,
                  aerobic_hr: int | None = None,
                  max_hr: float | None = None) -> list[dict[str, Any]]:
    """Grade the planned sessions of the CURRENT week - a view, not a planner.

    Every session the plan produced carries a `workout` key into the catalogue.
    From there: the family for the state rule (`fit_for`), the catalogue entry
    for the intensity, and `session_load` for the load AS PLANNED. Nothing here
    decides what to ride - `plan.py` did that - and nothing here restates a
    rule: state comes from `fit_for`, the grade from `stage`.

    Only the current week is graded. A grade on a session five weeks out would
    be a forecast the system cannot check, which is the same objection that
    keeps the panel from asking about coming days (docs/ausbau.md I3, I4).
    """
    out: list[dict[str, Any]] = []
    for session in sessions or []:
        rated = dict(session)
        entry = BY_KEY.get(str(session.get("workout") or ""))
        family = FAMILY_OF_KEY.get(str(session.get("workout") or ""))
        if not entry or not family:
            # an unknown key gets no invented verdict - it gets none at all
            out.append(rated)
            continue
        # The SAME payload the session list carries, so both views can render
        # the same card. The week view used to get a thinner record and grew a
        # poorer card around it - segments, heart-rate window and purpose line
        # all missing, five paragraphs of prose instead (docs/ausbau.md I9).
        full = scaled(BY_KEY[str(session.get("workout"))], ftp, aerobic_hr, max_hr)
        load = session_load(entry, session.get("hours"))
        verdict, reason = fit_for(
            family, state, entry.get("intensity") or 0,
            hard_days_last_7=hard_days_last_7, layoff_days=layoff_days,
            infection=infection,
        )
        fits_budget = None if budget is None else load <= budget
        rated.update({
            "key": entry.get("key"),
            "family": family,
            "family_label": next((label for fam, label, _ in FAMILIES if fam == family), family),
            "minutes": entry.get("minutes"),
            "intensity": entry.get("intensity"),
            "blocks": full.get("blocks"),
            "blocks_w": full.get("blocks_w"),
            "text": full.get("text"),
            "text_w": full.get("text_w"),
            "hr_window": full.get("hr_window"),
            "dfa": entry.get("dfa"),
            "evidence": entry.get("evidence"),
            "limit": entry.get("limit"),
            "load": load,
            "catalogue_load": entry.get("load"),
            "catalogue_minutes": entry.get("minutes"),
            "fit": verdict,
            "fit_reason": reason,
            "fits_budget": fits_budget,
            "budget": None if budget is None else round(budget),
            "stage": stage(verdict, fits_budget, recovery_offered),
            "purpose": entry.get("purpose"),
            "effect": entry.get("effect"),
        })
        out.append(rated)
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
    # Watts, not percentages. A percentage only lands correctly if the FTP set
    # in Intervals matches the one this plan was built from - and if it does
    # not, every target in the session is silently wrong. Absolute watts carry
    # the intent no matter what the other side is configured to.
    description = entry.get("text_w") or entry["text"]
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


# --- do the two anchors agree? -------------------------------------------------
# The catalogue prescribes WATTS from FTP percentages and HEART RATE from the
# athlete's measured DFA threshold. Those are two independent stops on the same
# jig: nothing forces them to the same measurement. When the measured aerobic
# threshold power sits at or below the top of the base-ride watt window
# (65-70% FTP), a base ride ridden by watts lands ON the threshold and the
# "DFA above 0.75" instruction printed next to it cannot hold. That is a
# conflict the rider has to see - not a detail to silently average away.
#
# Which side is wrong is genuinely open: DFA alpha-1 shows a fitness-dependent
# bias (it tends to UNDERestimate thresholds in fitter athletes) and wide
# limits of agreement for the first threshold, while an FTP setting can simply
# be stale. So the message names both and tells the rider what to steer by
# until it is resolved.
Z2_TOP = 0.70          # upper bound of the base-ride watt window, share of FTP
CONFLICT_TOLERANCE = 1.03


def anchor_conflict(ftp: float | None, aerobic_power: float | None) -> dict[str, Any] | None:
    """Return a conflict record when FTP-derived watts collide with the DFA anchor."""
    if not ftp or not aerobic_power or ftp <= 0 or aerobic_power <= 0:
        return None
    if aerobic_power > ftp * Z2_TOP * CONFLICT_TOLERANCE:
        return None
    share = round(aerobic_power / ftp * 100)
    z2_low, z2_high = round(ftp * 0.65), round(ftp * Z2_TOP)
    return {
        "ftp": round(ftp),
        "aerobic_power": round(aerobic_power),
        "share_pct": share,
        "z2_window": [z2_low, z2_high],
        "text": (
            f"Deine FTP ({round(ftp)} W) und deine gemessene aerobe Schwelle "
            f"({round(aerobic_power)} W, DFA alpha-1 = 0,75) passen nicht zusammen: "
            f"die Schwelle läge bei nur {share} % der FTP, und das Grundlagenfenster "
            f"({z2_low}–{z2_high} W) reicht an sie heran oder darüber. Eine von beiden "
            "Zahlen stimmt nicht — entweder ist die FTP in Intervals veraltet, oder die "
            "DFA-Ablesung unterschätzt die Schwelle (das tut sie bei fitteren Athleten "
            "systematisch, und ihre Übereinstimmung mit der ersten Schwelle ist in "
            "neueren Validierungen schwach). Bis das geklärt ist: Grundlage nach "
            "Herzfrequenz und DFA fahren, nicht nach diesen Watt."
        ),
    }
