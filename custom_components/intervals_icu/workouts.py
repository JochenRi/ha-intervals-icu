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

try:  # inside the package (Home Assistant)
    from .const import (
        DURABILITY_FUELLING_G_PER_H,
        DURABILITY_TEST_ALLOUT_5_FACTOR,
        DURABILITY_TEST_BLOCK_FRACTION,
        DURABILITY_TEST_COOLDOWN_MIN,
        DURABILITY_TEST_EASY_FRACTION,
        DURABILITY_TEST_LONG_MIN,
        DURABILITY_TEST_RECOVERY_MIN,
        DURABILITY_TEST_REFERENCE,
        DURABILITY_TEST_SHORT_MIN,
        DURABILITY_TEST_SPIN_FRACTION,
        DURABILITY_TEST_WARMUP_MIN,
        DURABILITY_TEST_WORK_J,
        DURABILITY_TEST_WORK_KJ,
    )
except ImportError:  # standalone (test suite loads this file directly)
    from const import (  # type: ignore[no-redef]
        DURABILITY_FUELLING_G_PER_H,
        DURABILITY_TEST_ALLOUT_5_FACTOR,
        DURABILITY_TEST_BLOCK_FRACTION,
        DURABILITY_TEST_COOLDOWN_MIN,
        DURABILITY_TEST_EASY_FRACTION,
        DURABILITY_TEST_LONG_MIN,
        DURABILITY_TEST_RECOVERY_MIN,
        DURABILITY_TEST_REFERENCE,
        DURABILITY_TEST_SHORT_MIN,
        DURABILITY_TEST_SPIN_FRACTION,
        DURABILITY_TEST_WARMUP_MIN,
        DURABILITY_TEST_WORK_J,
        DURABILITY_TEST_WORK_KJ,
    )

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
        "blocks": [(10, 55, "Einrollen"), (45, 68, "gleichmäßig", True), (5, 50, "Ausrollen")],
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
        "blocks": [(10, 55, "Einrollen"), (80, 68, "gleichmäßig", True), (5, 50, "Ausrollen")],
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
        "blocks": [(12, 55, "Einrollen"), (130, 67, "gleichmäßig", True), (8, 50, "Ausrollen")],
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
        "blocks": [(12, 55, "Einrollen"), (150, 67, "gleichmäßig", True), (10, 88, "Endblock 1"),
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

# --- the two protocol sessions (docs/ausbau.md K0/K1) -------------------------
# These two are NOT ordinary catalogue entries and are deliberately kept out of
# LIBRARY/BY_KEY's percentage world:
#
#   1. Their targets are a share of the athlete's own FRESH 20-MINUTE POWER,
#      not of the FTP field. On this account the profile carries 215 W while
#      the measured 20-minute best is 192 (K0). 80 % of an FTP-derived anchor
#      would be ~181 W - 35 W above the measured aerobic threshold, a time
#      trial to exhaustion instead of a fatigue block. So they carry ABSOLUTE
#      WATTS and are marked `abs_watts`, and `scaled()` leaves them alone.
#   2. The fatigued session's DURATION is derived, not catalogued: the fatigue
#      block holds fixed WORK (1.000 kJ), so its length is 1.000.000 J divided
#      by the target power. Write 108 minutes into a table and it is wrong
#      after the next measurement - the load bug of I3, one layer up.
#
# The fresh session has no anchor requirement (it IS the measurement), so it
# stands as a plain entry with percentage blocks like everything else.
DURABILITY_TEST_FRESH = {
    "key": "durability_test_fresh",
    "title": "Durability-Test, frisch",
    "purpose": "Termin 1: die beiden Bezugswerte",
    "minutes": (DURABILITY_TEST_WARMUP_MIN + DURABILITY_TEST_SHORT_MIN
                + DURABILITY_TEST_RECOVERY_MIN + DURABILITY_TEST_LONG_MIN
                + DURABILITY_TEST_COOLDOWN_MIN),
    "intensity": 78,
    "load": 62,
    # The two all-out percentages are an EXPECTATION, not a target: they feed
    # the load estimate and give the rider something to pace against on a
    # roller. What is measured is what the ride records. They are the one
    # place in this session where an FTP percentage appears at all, and they
    # decide nothing - the anchor is the RESULT of this session, not its input.
    "blocks": [
        (DURABILITY_TEST_WARMUP_MIN, 55, "Einrollen"),
        (DURABILITY_TEST_SHORT_MIN, 115,
         f"{DURABILITY_TEST_SHORT_MIN} min all-out (Erwartung, kein Ziel)"),
        (DURABILITY_TEST_RECOVERY_MIN, 50, "locker"),
        (DURABILITY_TEST_LONG_MIN, 100,
         f"{DURABILITY_TEST_LONG_MIN} min all-out (Erwartung, kein Ziel)"),
        (DURABILITY_TEST_COOLDOWN_MIN, 50, "Ausrollen"),
    ],
    "text": (f"- {DURABILITY_TEST_WARMUP_MIN}m 55% 85rpm\n"
             f"- {DURABILITY_TEST_SHORT_MIN}m 110-130% (all-out, nicht ERG)\n"
             f"- {DURABILITY_TEST_RECOVERY_MIN}m 50%\n"
             f"- {DURABILITY_TEST_LONG_MIN}m 95-110% (all-out, nicht ERG)\n"
             f"- {DURABILITY_TEST_COOLDOWN_MIN}m 50%"),
    "hr_hint": (1.00, 1.15),
    "dfa": "in den All-outs weit unter 0,5 — wenn nicht, war es kein All-out",
    "effect": (f"Misst nichts am Körper, sondern legt den Anker: die frische "
               f"{DURABILITY_TEST_SHORT_MIN}- und "
               f"{DURABILITY_TEST_LONG_MIN}-Minuten-Bestleistung. Aus der "
               f"{DURABILITY_TEST_LONG_MIN}-Minuten-Leistung folgt die "
               "Zielleistung von Termin 2 und damit alles Weitere."),
    "evidence": ("Barsumyan/Soost/Burchard, BMC Sports Sci Med Rehabil 17:192 "
                 "(2025): Heimtest an zwei Terminen, ausdrücklich für Amateure "
                 "entwickelt statt für Profis. Validiert an 20 gut trainierten "
                 f"Amateuren ({DURABILITY_TEST_REFERENCE})."),
    "limit": ("Die Reihenfolge kurz vor lang stammt aus dem Protokoll und wird "
              f"nicht gedreht. Die {DURABILITY_TEST_RECOVERY_MIN} Minuten "
              "dazwischen sind eine SETZUNG — das Protokoll nennt keine "
              "Erholungsdauer —, aber sie müssen an beiden Terminen gleich "
              "sein, sonst vergleicht Termin 2 etwas anderes. Grüner Zustand "
              "ist Pflicht: ein zu niedriger Anker macht den Ermüdungsblock zu "
              "leicht und den gemessenen Erhalt zu gut."),
    "states": ["ready"],
    "protocol": "fresh",
    "standard": list(),  # filled below, once DURABILITY_TEST_STANDARD exists
}

DURABILITY_TEST_FATIGUED_META = {
    "key": "durability_test_fatigued",
    "title": "Durability-Test, ermüdet",
    "purpose": "Termin 2: der Erhalt nach 1.000 kJ",
    "hr_hint": (1.00, 1.15),
    "dfa": "im Ermüdungsblock um 0,75, in den All-outs weit darunter",
    "effect": ("Misst, wie viel der frischen Leistung nach "
               f"{DURABILITY_TEST_WORK_KJ:.0f} kJ Arbeit übrig ist. Das ist "
               "die Größe, die aus gewöhnlichen Fahrten nachweislich nicht "
               "herausrechenbar ist."),
    "evidence": ("Barsumyan/Soost/Burchard, BMC Sports Sci Med Rehabil 17:192 "
                 f"(2025). Größenordnung der Validierung: {DURABILITY_TEST_REFERENCE}."),
    "states": ["ready"],
    "protocol": "fatigued",
}

# The standardisation both appointments carry, printed on the card (K1).
DURABILITY_TEST_STANDARD = [
    "Rolle, nicht Straße — konstante Bedingungen sind für einen Vergleichswert "
    "wichtiger als Freiluft. Der Ermüdungsblock in ERG, die All-outs NICHT in "
    "ERG: ERG deckelt genau das, was gemessen werden soll.",
    "Gleiche Mahlzeit im gleichen zeitlichen Abstand vor beiden Terminen. "
    f"Während Termin 2 mindestens {DURABILITY_FUELLING_G_PER_H} g Kohlenhydrate "
    "je Stunde — ein schlecht gefütterter Termin 2 misst die Energiezufuhr, "
    "nicht die Ermüdung.",
    f"Die {DURABILITY_TEST_WORK_KJ:.0f} kJ zählen ab Beginn des "
    "Ermüdungsblocks, nicht ab Fahrtbeginn. Der Radcomputer zeigt die "
    "Gesamtarbeit: den Wert beim Blockstart notieren und "
    f"{DURABILITY_TEST_WORK_KJ:.0f} addieren.",
    "Gleiche Tageszeit, gleicher Lüfter, gleiche Übersetzung. Alles, was nicht "
    "gleich war, gehört in den Rechenweg.",
]

DURABILITY_TEST_FRESH["standard"] = list(DURABILITY_TEST_STANDARD)

# The fresh session IS an ordinary catalogue entry - percentages, fixed shape,
# schedulable. Registering it here rather than inside LIBRARY keeps its long
# comment next to the session it belongs to.
LIBRARY.append(DURABILITY_TEST_FRESH)
BY_KEY[DURABILITY_TEST_FRESH["key"]] = DURABILITY_TEST_FRESH


def protocol_load(blocks_w: list[tuple], ftp: float | None) -> int | None:
    """The load of a protocol session, COMPUTED from its absolute watts.

    Why this is not a catalogue number, and why `session_load()` does not fit
    (docs/ausbau.md K1, corrected before the build):

    `session_load()` stretches a catalogue load by the ratio of the hours, and
    its docstring says what makes that valid - CONSTANT INTENSITY. A longer
    base ride is the same ride for longer. The fatigue block is not: it holds
    fixed WORK, so a lower target power makes it LONGER and at the same time
    LESS intense. The hours-scaler sees only the first half and moves the load
    in the direction the second half contradicts.

    So both inputs are taken as they are. Load is an intensity-squared times
    hours quantity, and the reference for the intensity is the FTP INTERVALS
    ITSELF COMPUTES WITH (`icu_ftp`) - not the anchor. The budget this number
    is held against comes from Intervals' own `icu_training_load`, and two
    numbers compared against each other must stand on the same reference, even
    when one of them is the value K0 refuses to steer by. The anchor decides
    the WATTS; the FTP decides what those watts cost.

    Returns None without an FTP: percentages are the honest fallback for a
    shape, but there is no honest fallback for a number.
    """
    if not ftp or ftp <= 0 or not blocks_w:
        return None
    total = 0.0
    for block in blocks_w:
        minutes = float(block[0])
        watts = float(block[1])
        if minutes <= 0 or watts <= 0:
            continue
        total += (watts / float(ftp)) ** 2 * (minutes / 60.0) * 100.0
    return round(total)


def fatigued_session(p20_fresh: float | None, aerobic_power: float | None = None,
                     ftp: float | None = None) -> dict[str, Any]:
    """Build Termin 2 from the fresh anchor - or refuse, and say why.

    Three outcomes, never a silent one (Fehlerklasse 4):

      * no anchor       -> `available` False, reason "Termin 1 fehlt"
      * anchor too low  -> `available` False, the plausibility rule from K0
      * otherwise       -> the full session, every number derived

    The plausibility rule: if the target power computed from Termin 1 sits
    BELOW the measured aerobic threshold, Termin 1 was not an all-out. A
    fatigue block under the aerobic threshold does not fatigue. Both numbers
    travel in the answer, because "not issued" without the two figures is the
    silent exit again.

    Note what the rule does NOT do: it is one-sided. It catches an anchor that
    is too LOW. Against one that is too HIGH - the 215 W in the profile, which
    would put the block 35 W above the aerobic threshold - it does nothing at
    all. The only protection there is that the anchor is never read from the
    FTP field, which is why that has its own counter-test.
    """
    if not p20_fresh or p20_fresh <= 0:
        return {
            "available": False,
            "why": "no_anchor",
            "reason": ("Termin 1 fehlt. Die Zielleistung des Ermüdungsblocks ist "
                       f"{DURABILITY_TEST_BLOCK_FRACTION:.0%} der frischen "
                       f"{DURABILITY_TEST_LONG_MIN}-Minuten-Leistung — ohne "
                       "gemessenen frischen Test gibt es sie nicht, und aus dem "
                       "FTP-Feld wird sie bewusst nicht abgeleitet."),
            "cta": DURABILITY_TEST_FRESH["key"],
        }

    target = round(float(p20_fresh) * DURABILITY_TEST_BLOCK_FRACTION)
    if aerobic_power and target < float(aerobic_power):
        return {
            "available": False,
            "why": "below_aerobic",
            "target_w": target,
            "aerobic_w": round(float(aerobic_power)),
            "p20_fresh": round(float(p20_fresh)),
            "reason": (f"Die aus Termin 1 errechnete Zielleistung liegt bei {target} W "
                       f"und damit unter der gemessenen aeroben Schwelle von "
                       f"{round(float(aerobic_power))} W. Dann war Termin 1 kein "
                       "All-out — ein Ermüdungsblock unterhalb der aeroben Schwelle "
                       "ermüdet nicht. Termin 1 wiederholen, ausgeruht."),
            "cta": DURABILITY_TEST_FRESH["key"],
        }

    block_min = round(DURABILITY_TEST_WORK_J / target / 60.0)
    easy = round(float(p20_fresh) * DURABILITY_TEST_EASY_FRACTION)
    spin = round(float(p20_fresh) * DURABILITY_TEST_SPIN_FRACTION)
    # the two all-outs have NO target - these are the expected values that go
    # into the load estimate only, and the card says so.
    expect_long = round(float(p20_fresh))
    expect_short = round(float(p20_fresh) * DURABILITY_TEST_ALLOUT_5_FACTOR)

    blocks_w = [
        (DURABILITY_TEST_WARMUP_MIN, easy, "Einrollen"),
        (block_min, target, f"Ermüdungsblock bis {DURABILITY_TEST_WORK_KJ:.0f} kJ (ERG)"),
        (DURABILITY_TEST_SHORT_MIN, expect_short,
         f"{DURABILITY_TEST_SHORT_MIN} min all-out (kein Ziel)"),
        (DURABILITY_TEST_RECOVERY_MIN, spin, "locker"),
        (DURABILITY_TEST_LONG_MIN, expect_long,
         f"{DURABILITY_TEST_LONG_MIN} min all-out (kein Ziel)"),
        (DURABILITY_TEST_COOLDOWN_MIN, spin, "Ausrollen"),
    ]
    minutes = sum(int(block[0]) for block in blocks_w)
    fuel = round(DURABILITY_FUELLING_G_PER_H * minutes / 60.0)

    entry = {
        **DURABILITY_TEST_FATIGUED_META,
        "minutes": minutes,
        "intensity": round(100.0 * target / float(p20_fresh)),
        "blocks_w": blocks_w,
        "abs_watts": True,
        "target_w": target,
        "p20_fresh": round(float(p20_fresh)),
        "block_minutes": block_min,
        "expected_w": {"short": expect_short, "long": expect_long},
        "fuel_g": fuel,
        "text_w": steps_text(blocks_w, None),
        "load": protocol_load(blocks_w, ftp),
        "limit": (f"Die härteste Einheit im Katalog: rund {minutes // 60} h "
                  f"{minutes % 60:02d} min, davon {block_min} min Ermüdungsblock. "
                  "Mindestens zwei ruhige Tage davor, grüner Zustand, keine harte "
                  "Einheit in den 48 h danach. Der Grund: ein Test in müdem "
                  "Zustand liefert eine Zahl, die später nicht mehr von einer "
                  "echten Verschlechterung zu unterscheiden ist."),
        "derivation": [
            f"Anker: {round(float(p20_fresh))} W — die gemessene frische "
            f"{DURABILITY_TEST_LONG_MIN}-Minuten-Leistung aus Termin 1, NICHT das "
            "FTP-Feld.",
            f"Zielleistung: {DURABILITY_TEST_BLOCK_FRACTION:.0%} davon = {target} W.",
            f"Blockdauer: {DURABILITY_TEST_WORK_KJ:.0f} kJ ÷ {target} W = "
            f"{block_min} min. Die Arbeit ist fest, die Dauer folgt daraus — "
            "deshalb steht hier keine Zahl aus einer Tabelle.",
            "Last: aus den Abschnitten gerechnet, nicht aus einem Katalogwert "
            "auf die Dauer skaliert. Das Skalieren gilt bei KONSTANTER "
            "Intensität; hier ist die Arbeit fest, also wird der Block bei "
            "schwächerem Anker länger UND lockerer, und ein Stunden-Faktor "
            "allein zöge die Last in die falsche Richtung.",
            f"Verpflegung: mindestens {DURABILITY_FUELLING_G_PER_H} g "
            f"Kohlenhydrate je Stunde, hier rund {fuel} g.",
        ],
        "standard": list(DURABILITY_TEST_STANDARD),
    }
    return {"available": True, "entry": entry}

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


# Welche Familien ihre Wattvorgabe aus der eigenen MESSUNG beziehen. Nicht:
# "die anderen sind zu hart". Sondern: aus arbiträren Fahrten ist oberhalb
# dieser Familien kein tragfähiger Fit zu gewinnen - eine Einheit mit Blöcken
# und Pausen liefert eine Gerade über ZWEI getrennte Punktwolken (gemessen:
# alpha 0,25 bis 1,77 in derselben Stunde, P(0,75) 181 W im Block-Abschnitt
# gegen 154 W beim Ausfahren derselben Fahrt). Der Weg zu Vorgaben für die
# übrigen Familien führt über eine EIGENE Messeinheit, nicht über die FTP -
# die bleibt dort Rückfall und wird als solcher beschriftet (docs/ausbau.md).
CURVE_FAMILIES = ("endurance", "long")


def _family_of(key: str | None) -> str | None:
    """Zu welcher Familie gehoert ein Katalogschluessel? EINE Quelle - FAMILIES."""
    for family_key, _label, keys in FAMILIES:
        if key in keys:
            return family_key
    return None


def curve_watts(curve: dict[str, Any] | None, hours: float) -> dict[str, Any] | None:
    """Return the measured threshold power at `hours` into a ride.

    Gestaffelt wird auf der GEPAARTEN Reihe: die ungepaarte enthält einen
    nachgewiesenen Auswahlanteil (PROJEKTSTAND §7). Bis zur letzten gemessenen
    Stunde ist das Messung, darüber Studienform - und welches von beidem, sagt
    jeder Abschnitt selbst.
    """
    if not curve:
        return None
    measured = curve.get("measured") or []
    if not measured:
        return None

    # Erst die gestaffelte Reihe bauen, SOLANGE die Paare tragen - dann den
    # Punkt waehlen. Andersherum fiel eine Dauer zwischen zwei Messstunden in
    # die Literatur, obwohl sie mitten im gemessenen Bereich liegt.
    steps = [{"t": measured[0]["t"], "hour": measured[0]["hour"],
              "watts": float(measured[0]["watts"]), "n": measured[0]["n"]}]
    for step in curve.get("paired") or []:
        if not step.get("enough"):
            break
        row = next((m for m in measured if m["hour"] == step["to_hour"]), None)
        if row is None:
            break
        steps.append({"t": row["t"], "hour": row["hour"],
                      "watts": steps[-1]["watts"] + float(step["delta"]), "n": row["n"]})

    last = steps[-1]
    # Innerhalb des gemessenen Bereichs: der naechstgelegene Stundenpunkt.
    # Eine halbe Stunde Reichweite je Punkt - das ist die Breite der Bins,
    # aus denen er stammt, nicht eine zusaetzliche Annahme.
    if hours <= last["t"] + 0.5:
        near = min(steps, key=lambda r: abs(r["t"] - hours))
        return {"watts": round(near["watts"]), "source": "measured",
                "n": near["n"], "hour": near["hour"]}

    # Darueber: die Studienform, am zuletzt GEMESSENEN Punkt verankert.
    lit = curve.get("literature") or []
    here = min(lit, key=lambda r: abs(r["t"] - hours), default=None)
    anchor = next((r for r in lit if r.get("hour") == last["hour"]), None)
    if here is None or anchor is None or not anchor.get("watts"):
        return {"watts": round(last["watts"]), "source": "measured",
                "n": last["n"], "hour": last["hour"]}
    return {"watts": round(last["watts"] * here["watts"] / anchor["watts"]),
            "source": "literature", "n": None, "hour": None}


def scaled(entry: dict[str, Any], ftp: float | None, aerobic_hr: int | None,
           max_hr: float | None = None, curve: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fill in the athlete's own numbers: watts from the MEASURED curve where
    it carries, from the FTP where it does not - and the origin travels with
    the session, so a changed number is explainable instead of surprising."""
    out = dict(entry)
    if ftp:
        out["blocks_w"] = [(block[0], round(ftp * block[1] / 100), block[2], *block[3:])
                           for block in entry["blocks"]]
        out["text_w"] = _text_in_watts(entry, ftp)
        out["watt_source"] = "ftp"
    if curve and (entry.get("family") or _family_of(entry.get("key"))) in CURVE_FAMILIES:
        staged, elapsed, changed = [], 0.0, False
        for block in entry["blocks"]:
            minutes = float(block[0])
            # Der Zeitpunkt in der MITTE des Abschnitts: ein Block von 80
            # Minuten hat keine Leistung, er hat einen Verlauf - die Mitte ist
            # der ehrlichste einzelne Wert dafür.
            at = curve_watts(curve, (elapsed + minutes / 2) / 60.0)
            elapsed += minutes
            # Nur der GLEICHMÄSSIGE Hauptteil kommt aus der Kurve. Ein- und
            # Ausrollen sind Prozentangaben auf eine Schwelle, die dort nicht
            # gemessen wurde.
            if at is None or not (len(block) > 3 and block[3]):
                staged.append((block[0], round(ftp * block[1] / 100) if ftp else None,
                               block[2], *block[3:]))
                continue
            staged.append((block[0], at["watts"], block[2], *block[3:]))
            changed = True
            out.setdefault("curve_blocks", []).append(
                {"label": block[2], "watts": at["watts"], "source": at["source"],
                 "n": at["n"], "hour": at["hour"]})
        if changed:
            out["blocks_w"] = staged
            out["text_w"] = steps_text(staged, None)
            out["watt_source"] = "curve"
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
    # Own family, not a variant under "Lange Fahrt" (K1): a measurement is a
    # different kind of session from a training session, and tucking it into
    # the long-ride family would make it look like a harder version of one.
    # The fatigued appointment is NOT listed here - it has no fixed shape to
    # list, it is derived per anchor by fatigued_session().
    ("durability_test", "Durability-Test", ["durability_test_fresh"]),
]

# What each state can carry. Not a filter - a verdict per family, so every kind
# of session stays visible and says what it would cost today.
FIT_BY_STATE: dict[str, dict[str, str]] = {
    "slump":      {"recovery": "ok", "return": "maybe", "endurance": "no", "long": "no",
                   "tempo": "no", "sweetspot": "no", "threshold": "no", "vo2max": "no",
                   "durability_test": "no"},
    "recovering": {"recovery": "ok", "return": "ok", "endurance": "maybe", "long": "no",
                   "tempo": "no", "sweetspot": "no", "threshold": "no", "vo2max": "no",
                   "durability_test": "no"},
    "rebound":    {"recovery": "ok", "return": "ok", "endurance": "ok", "long": "maybe",
                   "tempo": "maybe", "sweetspot": "maybe", "threshold": "no", "vo2max": "no",
                   "durability_test": "no"},
    "strained":   {"recovery": "ok", "return": "ok", "endurance": "ok", "long": "maybe",
                   "tempo": "maybe", "sweetspot": "maybe", "threshold": "no", "vo2max": "no",
                   "durability_test": "no"},
    "ready":      {"recovery": "ok", "return": "ok", "endurance": "ok", "long": "ok",
                   "tempo": "ok", "sweetspot": "ok", "threshold": "ok", "vo2max": "ok",
                   "durability_test": "ok"},
    "elevated":   {"recovery": "ok", "return": "ok", "endurance": "ok", "long": "maybe",
                   "tempo": "maybe", "sweetspot": "maybe", "threshold": "no", "vo2max": "no",
                   "durability_test": "no"},
    "unknown":    {"recovery": "ok", "return": "ok", "endurance": "ok", "long": "maybe",
                   "tempo": "maybe", "sweetspot": "maybe", "threshold": "maybe", "vo2max": "maybe",
                   "durability_test": "no"},
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
    # The protocol tests are blocked outside a green state for a reason that is
    # NOT the usual one (K4). Every other family says "it costs more today";
    # this one says the NUMBER would be wrong. Only the generic state sentence
    # is replaced - the hard-day and infection rules below are more specific
    # and keep their own wording.
    if family_key == "durability_test" and verdict != "ok" and reason == FIT_REASON.get(state, ""):
        reason = ("Bei gelbem oder rotem Zustand misst der Test die Ermüdung statt der "
                  "Durability. Das ist kein Sicherheitshinweis, sondern ein Messfehler: "
                  "die Zahl wäre später nicht mehr von einer echten Verschlechterung zu "
                  "unterscheiden.")
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


# --- stretching a template to the planned duration (docs/ausbau.md I12) -------
# Elasticity is a PROPERTY OF THE SECTION, written down per session in the
# catalogue by whoever wrote the session - not a threshold somebody derived.
# Warm-up, cool-down, intervals and their rests are fixed; a steady block is
# elastic and absorbs the difference. A template WITHOUT an elastic section is
# not stretched at all: its duration is part of what it is (the 40-minute
# recovery ride, the graded return, every interval protocol), and inventing a
# longer version of it would be putting words in the author's mouth.
#
# The honest label travels with it: this is an AUTHOR'S STATEMENT per session,
# not a measurement.
# Two different kinds of statement, and they are kept apart on the card,
# because collapsing them is how a setting starts passing for a finding.
#
# WHAT IS SOURCED - and therefore not up for discussion: the warm-up does NOT
# grow with the ride, and the intervals do not either.
# WHAT IS A SETTING: that the whole difference lands on the steady block. It
# FOLLOWS from the sourced part - if warm-up, intervals and cool-down are
# fixed, nothing else is left - but it was never measured as such.
ELASTIC_EVIDENCE = {
    "rule": (
        "Der Aufbau stammt aus der Vorlage und wurde auf die geplante Dauer gebracht: "
        "Einrollen, Ausrollen, Intervalle und Pausen bleiben, wie sie sind — die "
        "gleichmäßigen Abschnitte nehmen die Differenz auf. Welcher Abschnitt dehnbar "
        "ist, steht je Einheit im Katalog."
    ),
    "evidence": (
        "Belegt ist, dass das Einrollen NICHT mitwächst: die Literatur verschreibt "
        "Aufwärmen in absoluten Minuten — 10 bis 15, optimal 15 bis 20, und bei "
        "Ausdauerbelastungen über drei Stunden eher 10 bis 15. Zu langes Aufwärmen "
        "ermüdet nachweislich: ein traditionelles Aufwärmen über 50 Minuten erzeugte "
        "Ermüdung und minderte die Leistung (J Appl Physiol 2011, „Less is more“). Je "
        "länger die Einheit, desto weniger Aufwärmen — nicht mehr. Intervalle stehen "
        "ebenfalls absolut in der Literatur (4×4, 2×20, 5×8), nie als Anteil."
    ),
    "limit": (
        "Eine Setzung ist dagegen, dass die gesamte Differenz auf den gleichmäßigen "
        "Block geht. Das folgt aus dem Belegten — wenn Aufwärmen, Intervalle und "
        "Ausrollen fest sind, bleibt nichts anderes übrig —, ist aber selbst nicht "
        "gemessen. Welcher Abschnitt als dehnbar gilt, ist eine Angabe des Autors der "
        "Einheit."
    ),
}

FIXED_EVIDENCE = {
    "rule": (
        "Diese Vorlage hat keinen dehnbaren Abschnitt. Der Aufbau steht deshalb so da, "
        "wie er geschrieben wurde, und die geplante Dauer daneben."
    ),
    "evidence": (
        "Intervalle und ihre Pausen stehen in der Literatur absolut (4×4, 2×20, 5×8), "
        "nie als Anteil einer Gesamtdauer; dasselbe gilt für das Aufwärmen davor. Eine "
        "feste Dosierung — die Regenerationsfahrt, der abgestufte Wiedereinstieg — ist "
        "ihre Dauer."
    ),
    "limit": (
        "Deshalb wird hier nichts gedehnt, und beide Zahlen bleiben sichtbar. Eine "
        "längere Fassung zu erfinden hieße, dem Autor der Einheit Worte in den Mund zu "
        "legen."
    ),
}


def is_elastic(block: Any) -> bool:
    """Whether a catalogue block may absorb a change in duration."""
    return bool(len(block) > 3 and block[3])


def stretch_blocks(entry: dict[str, Any], hours: float | None) -> list[tuple] | None:
    """Fit a template's sections to the planned duration, or refuse.

    Returns None - and the caller then keeps the template AND the planned
    duration side by side - when there is nothing to stretch: no hours given,
    no elastic section, the duration already matches, or the fixed sections
    alone already fill (or overfill) the planned ride. Silence would be the
    worse answer in every one of those cases.
    """
    blocks = entry.get("blocks") or []
    if not hours or not blocks:
        return None
    elastic = [index for index, block in enumerate(blocks) if is_elastic(block)]
    if not elastic:
        return None

    target = round(float(hours) * 60)
    fixed = sum(block[0] for index, block in enumerate(blocks) if index not in elastic)
    room = target - fixed
    current = sum(block[0] for index, block in enumerate(blocks) if index in elastic)
    if room < 1 or current <= 0 or room == current:
        return None

    out = [list(block) for block in blocks]
    share = room / current
    for index in elastic:
        out[index][0] = max(1, round(out[index][0] * share))
    # rounding never silently changes the total: the drift lands on the
    # longest elastic section, and the sum matches the planned duration
    drift = target - sum(row[0] for row in out)
    if drift:
        biggest = max(elastic, key=lambda i: out[i][0])
        out[biggest][0] = max(1, out[biggest][0] + drift)
    return [tuple(row) for row in out]


def steps_text(blocks: list[tuple], ftp: float | None) -> str:
    """The step list for stretched sessions, built FROM the blocks.

    The hand-written `text` of a template states its own minutes. Printing it
    next to a stretched bar would be two durations for one session - the exact
    shape of the load bug, one layer up.
    """
    lines = []
    for block in blocks:
        value = f"{round(ftp * block[1] / 100)}w" if ftp else f"{block[1]}%"
        lines.append(f"- {block[0]}m {value}  ({block[2]})")
    return "\n".join(lines)


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
            layoff_days: int | None = None, limit: int = 9,
            goal: str | None = None,
            recovery_offered: bool = False,
            curve: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """One session per family, each judged for today - never filtered away.

    The earlier version filtered: in a rebound state everything hard vanished
    and three base rides were left, which is not a choice. This keeps every
    kind of session visible and attaches the verdict to it, because the
    decision is the athlete's; the data's job is to say what it costs.
    """
    order = {
        "long_ride": ["long", "endurance", "durability_test", "sweetspot", "tempo", "threshold", "vo2max", "recovery", "return"],
        "ftp": ["threshold", "sweetspot", "endurance", "vo2max", "tempo", "long", "durability_test", "recovery", "return"],
        "vo2max": ["vo2max", "threshold", "endurance", "sweetspot", "tempo", "long", "durability_test", "recovery", "return"],
        "health": ["endurance", "tempo", "recovery", "sweetspot", "threshold", "vo2max", "long", "durability_test", "return"],
    }.get(goal or "", ["endurance", "vo2max", "sweetspot", "threshold", "tempo", "long", "durability_test", "recovery", "return"])

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
        entry = dict(scaled(BY_KEY[key], ftp, aerobic_hr, max_hr, curve))
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


def protocol_block(state: str, p20_fresh: float | None = None,
                   aerobic_power: float | None = None, ftp: float | None = None,
                   budget: float | None = None, hard_days_last_7: int = 0,
                   recovery_offered: bool = False,
                   infection: bool = False) -> dict[str, Any]:
    """Termin 2 for the panel: either a graded session, or a sentence and a button.

    K1 is explicit that a missing Termin 1 does not produce an empty slot or a
    greyed-out card: the session is NOT in the catalogue, and what stands in
    its place is a sentence saying WHICH appointment is missing, plus the
    button that puts Termin 1 in the calendar. Same shape as "Was das ausbaut"
    in G5 - the reason, not just the lack.

    When it IS available it gets the full four-grade treatment from I3, with
    no exception for being a test (K4). Exempting it would soften exactly the
    rule I3 defends against special cases.
    """
    built = fatigued_session(p20_fresh, aerobic_power, ftp)
    if not built.get("available"):
        return {**built, "title": DURABILITY_TEST_FATIGUED_META["title"],
                "cta_title": DURABILITY_TEST_FRESH["title"]}

    entry = dict(built["entry"])
    verdict, reason = fit_for("durability_test", state, entry["intensity"],
                              hard_days_last_7=hard_days_last_7, infection=infection)
    load = entry.get("load")
    fits_budget = None if budget is None or load is None else load <= budget
    entry.update({
        "family": "durability_test",
        "family_label": "Durability-Test",
        "fit": verdict,
        "fit_reason": reason,
        "fits_budget": fits_budget,
        "stage": stage(verdict, fits_budget, recovery_offered),
    })
    return {"available": True, "entry": entry}


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
                  max_hr: float | None = None,
                  curve: dict[str, Any] | None = None) -> list[dict[str, Any]]:
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
        # The sections are fitted to the planned duration where the catalogue
        # says they may be. Where it does not, nothing is stretched and the
        # card keeps BOTH durations side by side (docs/ausbau.md I12).
        stretched = stretch_blocks(entry, session.get("hours"))
        template = dict(entry)
        if stretched:
            template["blocks"] = stretched
            template["minutes"] = sum(block[0] for block in stretched)
            template["text"] = steps_text(stretched, None)
        full = scaled(template, ftp, aerobic_hr, max_hr, curve)
        if stretched and ftp:
            full["text_w"] = steps_text(stretched, ftp)
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
            "minutes": template.get("minutes"),
            "template_minutes": entry.get("minutes"),
            "stretched": bool(stretched),
            "stretch_note": ELASTIC_EVIDENCE if stretched else FIXED_EVIDENCE,
            "elastic_sections": [block[2] for block in (entry.get("blocks") or [])
                                 if is_elastic(block)],
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
