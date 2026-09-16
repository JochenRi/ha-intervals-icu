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
        RAMP_COOLDOWN_MIN,
        RAMP_END_RESERVE_MIN,
        RAMP_EXPECTED_MIN,
        RAMP_FALLBACK_END_PCT,
        RAMP_FALLBACK_START_PCT,
        RAMP_STEP_W_PER_MIN,
        RAMP_WARMUP_MIN,
        CURVE_TARGET_SHARE,
    )
except ImportError:  # standalone (test suite loads this file directly)
    from const import (  # type: ignore[no-redef]
        DURABILITY_FUELLING_G_PER_H,
        RAMP_COOLDOWN_MIN,
        RAMP_END_RESERVE_MIN,
        RAMP_EXPECTED_MIN,
        RAMP_FALLBACK_END_PCT,
        RAMP_FALLBACK_START_PCT,
        RAMP_STEP_W_PER_MIN,
        RAMP_WARMUP_MIN,
        CURVE_TARGET_SHARE,
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

# --- Der Stufentest (docs/ausbau.md N) ---------------------------------------
# EIN Termin, EINE Fahrt, drei Zahlen. Anders als das abgeloeste
# Durability-Protokoll braucht er weder einen Anker noch eine abgeleitete
# Dauer - er steht deshalb als gewoehnlicher Katalogeintrag hier.
#
# DIE EINZIGEN FESTEN ZAHLEN SIND DIE DAUERN (N1). Einrollen, Ausrollen und
# die Rampensteigung stehen in const.py; die LEISTUNGEN kommen aus den eigenen
# Werten. Die Prozentwerte in `blocks` sind eine ERWARTUNG fuer die
# Lastschaetzung und keine Vorgabe: gemessen wird, was gefahren wurde. Ohne
# eigene Messwerte faellt alles sichtbar auf die FTP zurueck.
RAMP_TEST = {
    "key": "ramp_test",
    "title": "Stufentest",
    "purpose": "Beide Schwellen in einer Fahrt",
    # Die Rampendauer ist eine ERWARTUNG fuer die Lastschaetzung. Sie endet an
    # einem ZUSTAND und nicht an der Uhr, und wie lange das dauert, haengt an
    # der eigenen Spanne - bei einem starken Fahrer laenger.
    "minutes": RAMP_WARMUP_MIN + RAMP_EXPECTED_MIN + RAMP_COOLDOWN_MIN,
    "intensity": 72,
    "load": 55,
    # PLATZHALTER, und zwar ausdruecklich: ramp_protocol() ersetzt Leistungen
    # UND Dauer der Rampe immer. Ohne FTP gibt es keine Dauer, weil die Spanne
    # an den eigenen Werten haengt - eine Zahl, die hier stuende, waere genau
    # der Widerspruch aus §7 (Dauer, Steigung und Spanne passten nur bei einer
    # einzigen FTP zusammen). Die Prozentwerte sind der FTP-Rueckfall und
    # stehen in const.py.
    "blocks": [
        (RAMP_WARMUP_MIN, RAMP_FALLBACK_START_PCT, "Einrollen, ruhig"),
        (RAMP_EXPECTED_MIN, RAMP_FALLBACK_END_PCT, "Rampe (Platzhalter — die Dauer wird gerechnet)"),
        (RAMP_COOLDOWN_MIN, RAMP_FALLBACK_START_PCT, "Ausrollen, konstant"),
    ],
    "text": (f"- {RAMP_WARMUP_MIN}m {RAMP_FALLBACK_START_PCT}% 85rpm\n"
             f"- ramp {RAMP_FALLBACK_START_PCT}-{RAMP_FALLBACK_END_PCT}% "
             f"({RAMP_STEP_W_PER_MIN} W/min, nicht ERG)\n"
             f"- {RAMP_COOLDOWN_MIN}m {RAMP_FALLBACK_START_PCT}% (gleich bleiben, nicht abkürzen)"),
    # KEIN hr_hint (seit 0.51.1). Bei jeder anderen Einheit ist das Fenster ein
    # ZIEL, in dem man bleibt. Bei einer Rampe wandert der Puls ueber den ganzen
    # Bereich - ein Fenster waere dort nicht bloss ungenau, es waere die falsche
    # ART von Aussage: ein Ziel, wo es keines gibt. Wer darin bliebe, braeche den
    # Test ab. Die alten (0,70-1,00) skalierten ausserdem die AEROBE Schwelle und
    # endeten damit bei 160 bpm, waehrend die Rampe bis ueber die anaerobe geht
    # (eigene Blockmessung: 172-186 bpm). Statt der Spanne steht ein Satz da.
    "hr_note": (
        "Ein Pulsfenster gibt es hier nicht: bei einer Rampe wandert der Puls "
        "über den ganzen Bereich — vom ruhigen Einrollen bis an dein Maximum. "
        "Eine Spanne wäre ein Ziel, und ein Ziel gibt es in diesem Test nicht."),
    "dfa": "der Zweck der Fahrt: von über 1,0 stetig bis stabil unter 0,5",
    "effect": ("Misst nichts am Körper und trainiert auch nichts — er liest deine "
               "beiden Schwellen ab, in EINER Fahrt unter gleichen Bedingungen. "
               "Alle paar Monate."),
    "evidence": ("Rogers u. a. (2021): DFA a1 erreicht 0,75 an der ersten und 0,5 an "
                 "der zweiten Schwelle. Die 0,75 stammt vom LAUFBAND; für das Rad "
                 "gibt es eigene Belege (Elite-Triathleten 247,0 gegen 252,3 W; "
                 "Herzpatienten 67,8 gegen 73,2 W bei r = 0,87)."),
    "limit": ("Belastbar ist die VERÄNDERUNG bei dir, nicht die absolute Höhe: die "
              "zweite Schwelle stimmt in Studien gut, die erste zeigt erheblichen "
              "systematischen Bias. Grüner Zustand ist Pflicht — ein müder Test "
              "misst die Müdigkeit."),
    "states": ["ready"],
}

# Was zum Test dazugehoert, auf der Karte gedruckt. JEDE Zahl bringt ihren
# GRUND mit: wer nur die Zahl liest, kuerzt sie beim naechsten Mal ab - und
# die Beschreibung entscheidet, ob jemand den Test richtig faehrt oder eine
# Stunde umsonst tritt (N5).
RAMP_TEST_STANDARD = [
    "Auf der Rolle, mit BRUSTGURT. Die optische Messung am Handgelenk taugt "
    "dafür nachweislich nicht — sie liefert keine sauberen Abstände zwischen den "
    "Herzschlägen, und genau die werden hier ausgewertet.",
    "Ausgeruht. Bei gelbem oder rotem Zustand wird der Test gar nicht erst "
    "vorgeschlagen: er misst dann deine Müdigkeit und nicht deine Schwellen.",
    f"{RAMP_WARMUP_MIN} Minuten ruhig einrollen. Weder Rogers 2021 (Laufband) noch "
    "Olieslagers 2026 (Rad) nennt ein Einrollen — diese Zeit ist GESETZT, und der "
    "Grund ist unsere Auswertung: "
    "der alpha-Wert braucht ein bis zwei Minuten, bis er eingeschwungen ist, und "
    "das Rechenfenster ist zwei Minuten breit.",
    f"Dann je Minute {RAMP_STEP_W_PER_MIN} Watt mehr, bis du nicht mehr kannst. "
    "Olieslagers 2026 fuhr auf dem Rad eine flache Rampe; Rogers 2021 kam vom "
    "Laufband, wo die Steigung anders zählt. Unsere ist FLACH und wächst nicht "
    "mit deiner Stärke: bei steileren "
    "Rampen hinkt die Sauerstoffaufnahme hinterher, und dann ist die Wattzahl "
    "nicht mehr ablesbar. Der Preis ist ein längerer Test.",
    "Während der Rampe: gleichmäßig treten, nicht aus dem Sattel, Trittfrequenz "
    "konstant halten, nicht sprechen. Alles davon verändert die Abstände zwischen "
    "den Herzschlägen — und die sind die Messung.",
    "Abbrechen, wenn du nicht mehr kannst — in Rogers 2021 (Laufband) hieß das "
    "Abbruchkriterium ebenfalls willentliche Erschöpfung, ein Zustand und keine "
    "Wattzahl. Das ist VORGESEHEN und kein Fehlversuch: wichtig ist nur, dass dein "
    "alpha vorher stabil unter 0,5 war. Kommst du dort nicht an, fehlt die zweite "
    "Schwelle — die erste steht trotzdem. Und die erste ist die schwächere: "
    "Olieslagers 2026 fand für sie am Rad schlechte Übereinstimmung mit LT1/VT1 "
    "(Bias −21 bis −45 W), für die zweite dagegen deutlich bessere. Die 0,75 "
    "stammt vom LAUFBAND.",
    f"Danach {RAMP_COOLDOWN_MIN} Minuten ausrollen, bei derselben ruhigen "
    "Leistung, gleich bleibend. NICHT abkürzen: diese Zeit ist Teil der Messung. "
    "Eine Protokollvorgabe dafür gibt es nicht — gesetzt ist sie, weil Michael "
    "u. a. 2017 die parasympathische Reaktivierung im Fenster 0 bis 10 Minuten "
    "nach Belastungsende betrachtet (die vollständige Rückkehr dauert laut "
    "Stanley/Peake/Buchheit 2013 24 bis 72 Stunden). Eine Ausrolldauer nennt "
    "keine der beiden Arbeiten. Gleiche Haltung und gleiche Leistung wie "
    "beim letzten Mal, sonst misst der zweite Test etwas anderes als der erste.",
    "Danach die Fahrt im Aktivitätsdetail als Stufentest MARKIEREN. Das System "
    "erkennt sie nicht von selbst — und soll es auch nicht.",
    "Was der Test NICHT kann: er sagt nicht, wie hoch deine Schwellen absolut "
    "sind. Belastbar ist, wie sie sich bei DIR über die Monate verändern.",
    # DER ZEHNTE PUNKT, seit 0.51.1. Vorher stand auf der Karte "ramp 60-115%"
    # und niemand konnte das fuer eine Vorgabe halten. Jetzt steht dort eine
    # konkrete Wattzahl aus den EIGENEN Messwerten - und eine konkrete Wattzahl
    # ohne Beschriftung wird als Vorgabe gelesen. Genau deshalb dieser Punkt.
    "Die Wattzahlen auf dieser Karte sind eine ERWARTUNG, keine Vorgabe. Start "
    "und Ende kommen aus deinen eigenen Messwerten — der Start aus deiner "
    "Ermüdungskurve, das Ende aus deiner Leitzahl plus einer gesetzten Reserve; "
    "steht beides nicht zur Verfügung, fällt beides sichtbar auf die FTP zurück. "
    "Der Test ENDET AM ALPHA-WERT, nicht an der Zahl: erreichst du das "
    "ausgewiesene Ende früher nicht mehr, ist das kein Fehlversuch, solange dein "
    "alpha vorher stabil unter 0,5 lag. Fährst du darüber hinaus, ist das auch "
    "in Ordnung — gerechnet wird, was gemessen wurde, und über das gemessene "
    "Segment hinaus wird nichts hochgerechnet.",
]

# Die Beschreibung haengt AN DER EINHEIT, genau wie beim abgeloesten
# Durability-Protokoll (0.44.0). Das Panel liest sie dort als `entry.standard` -
# in 0.51.0 lag sie stattdessen in der ramp_tests-Payload unter `protocol`, und
# ein `|| []` hat die Luecke lautlos in eine leere Liste verwandelt (§7,
# neunzehnter Fall). EINE Quelle: RAMP_TEST_STANDARD, hier angehaengt.
RAMP_TEST["standard"] = list(RAMP_TEST_STANDARD)

LIBRARY.append(RAMP_TEST)
BY_KEY[RAMP_TEST["key"]] = RAMP_TEST

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


# --- Die Quellenkette je Familie (docs/ausbau.md N2) -------------------------
# EINE Tabelle, keine verstreuten Bedingungen. Die Rangfolge ist je Familie
# VERSCHIEDEN, und genau deshalb steht sie an einer Stelle: eine Rangfolge, die
# in drei if-Zweigen verteilt liegt, driftet beim naechsten Umbau auseinander -
# das war in diesem Projekt siebenmal die Listen-Klasse (§7). Ein Waechter in
# test_workouts haelt diese Tabelle gegen die Reihenfolge, die `scaled()`
# tatsaechlich durchlaeuft.
#
# Warum welche Schwelle des Stufentests:
#   HRVT2 (alpha 0,5) gehoert gegen die LEITZAHL, die Leistung im ersten
#   eingeschwungenen Block - das ist per Definition dieselbe Groesse.
#   HRVT1 (alpha 0,75) gehoert gegen P(0,75) aus der Ermuedungskurve, ebenfalls
#   dieselbe Groesse. HRVT2 gegen eine VO2max-TRAININGSVORGABE zu halten waere
#   0.49.2 in neuer Gestalt: zwei verschieden erhobene Zahlen unter einer
#   Ueberschrift.
#
# Tempo und Schwelle haben keine eigene erste Stufe - fuer sie IST der
# Stufentest die Messung. Welche seiner beiden Schwellen: HRVT2, weil beide
# Familien am oberen Ende liegen. Das ist eine SETZUNG, keine Vorgabe aus N2.
SOURCE_CHAIN: dict[str, tuple[str, ...]] = {
    "vo2max":    ("blocks", "ramp_hrvt2", "ftp"),
    "sweetspot": ("blocks", "ramp_hrvt2", "ftp"),
    "tempo":     ("ramp_hrvt2", "ftp"),
    "threshold": ("ramp_hrvt2", "ftp"),
    "endurance": ("curve", "ramp_hrvt1", "ftp"),
    "long":      ("curve", "ramp_hrvt1", "ftp"),
}

# Wie jede Stufe heisst, wenn die Karte sie nennt. Eine Zahl OHNE Herkunft ist
# in diesem Projekt schon zweimal als Messung gelesen worden, die keine war -
# deshalb traegt AUCH der Rueckfall eine Beschriftung.
SOURCE_LABEL: dict[str, str] = {
    "blocks": "gemessen an deinen Arbeitsblöcken",
    "curve": "gemessen an deiner Ermüdungskurve",
    "ramp_hrvt2": "gemessen im Stufentest, zweite Schwelle",
    "ramp_hrvt1": "gemessen im Stufentest, erste Schwelle",
    "ftp": "Rückfall auf die FTP — nicht gemessen",
}


RAMP_START_CHAIN: tuple[str, ...] = ("curve", "ramp_hrvt1", "ftp")
RAMP_END_CHAIN: tuple[str, ...] = ("blocks", "ramp_hrvt2", "ftp")


def _ramp_node(ramp: dict[str, Any] | None, which: str) -> dict[str, Any] | None:
    """Eine Schwelle aus einem markierten Stufentest, oder nichts."""
    node = ((ramp or {}).get("result") or {}).get(which)
    return node if isinstance(node, dict) and node.get("watts") else None


def ramp_protocol(ftp: float | None, curve: dict[str, Any] | None = None,
                  blocks: dict[str, Any] | None = None,
                  ramp: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Start- und Endleistung des Stufentests - und die DARAUS gerechnete Dauer.

    N1 laesst genau drei feste Zahlen zu: Einrolldauer, Ausrolldauer und die
    Rampensteigung. Alles andere kommt aus den eigenen Werten, jede Seite mit
    ihrer eigenen Rangfolge:

        Start   Ermuedungskurve -> Stufentest HRVT1 -> FTP
        Ende    Blockmessung (LEITZAHL) -> Stufentest HRVT2 -> FTP

    WARUM DIE LEITZAHL UND NICHT DIE TRAININGSVORGABE. N2 sagt es ausdruecklich:
    HRVT2 liegt bei alpha 0,5, und die Leitzahl ist der erste eingeschwungene
    Block - per Definition dieselbe Groesse. Die Trainingsvorgabe steht am
    MEDIAN-alpha (am eigenen Bestand 0,40 gegen 0,47) und ist eine andere Zahl.
    Sie hier zu nehmen waere 0.49.2 in neuer Gestalt: zwei verschieden erhobene
    Groessen unter einer Ueberschrift.

    DIE RESERVE IST EINE ZEIT, KEIN ANTEIL. Die Rampe muss ueber die eigene
    Leitzahl HINAUS gehen, sonst wird die flache Strecke unter 0,5 nie
    aufgezeichnet und die zweite Schwelle faellt aus - genau der Fall, den
    0.51.0 ausgeliefert hat (Ende 230 W bei einer Leitzahl von 257 W). Eine
    Zeit sagt, was sie bedeutet; ein Prozentsatz waere eine zweite Zahl, deren
    Bezug niemand mehr nachliest. SETZUNG, und die Karte sagt das.

    DIE DAUER WIRD GERECHNET, NIE GESETZT. Vorher standen Dauer, Steigung und
    Spanne nebeneinander und passten nur bei genau einer FTP zusammen
    (272,7 W). Jetzt folgt die Dauer aus den beiden Enden, und der Widerspruch
    ist nicht mehr herstellbar (§7, achtzehnter Fall).
    """
    if not ftp:
        return None
    step = float(RAMP_STEP_W_PER_MIN)
    reserve = RAMP_END_RESERVE_MIN * step

    # --- Start: dieselbe Groesse wie die Grundlagenvorgabe fuer eine Stunde ---
    start, start_from = None, "ftp"
    for stage_name in RAMP_START_CHAIN:
        if stage_name == "curve":
            at = curve_watts(curve, 0.5)
            if at:
                start, start_from = round(at["watts"] * CURVE_TARGET_SHARE), "curve"
                break
        elif stage_name == "ramp_hrvt1":
            node = _ramp_node(ramp, "hrvt1")
            if node:
                start = round(float(node["watts"]) * CURVE_TARGET_SHARE)
                start_from = "ramp_hrvt1"
                break
        else:
            start = round(ftp * RAMP_FALLBACK_START_PCT / 100)
    if start is None:
        start = round(ftp * RAMP_FALLBACK_START_PCT / 100)

    # --- Ende: die eigene Leitzahl plus Reserve -------------------------------
    end, end_from, lead = None, "ftp", None
    for stage_name in RAMP_END_CHAIN:
        if stage_name == "blocks":
            fam = ((blocks or {}).get("families") or {}).get("vo2max") or {}
            latest = fam.get("latest") if fam.get("source_ok") else None
            if isinstance(latest, dict) and latest.get("first_watts"):
                lead = {"watts": latest["first_watts"], "alpha": latest.get("first_alpha"),
                        "date": latest.get("date")}
                end, end_from = round(float(latest["first_watts"]) + reserve), "blocks"
                break
        elif stage_name == "ramp_hrvt2":
            node = _ramp_node(ramp, "hrvt2")
            if node:
                lead = {"watts": node["watts"], "alpha": node.get("alpha"),
                        "date": (ramp or {}).get("date")}
                end, end_from = round(float(node["watts"]) + reserve), "ramp_hrvt2"
                break
        else:
            end = round(ftp * RAMP_FALLBACK_END_PCT / 100)
    if end is None:
        end = round(ftp * RAMP_FALLBACK_END_PCT / 100)

    # Ein Ende unter dem Start ist keine Rampe. Das kann nur der gemischte Fall
    # herstellen (gemessener Start, FTP-Rueckfall am Ende) - dann faellt AUCH
    # der Start zurueck, damit nicht eine Seite gemessen neben einer geratenen
    # steht. Dieselbe Regel wie beim Gleichstand aus 0.47.1.
    if end <= start:
        start, start_from = round(ftp * RAMP_FALLBACK_START_PCT / 100), "ftp"
        end, end_from = round(ftp * RAMP_FALLBACK_END_PCT / 100), "ftp"
        lead = None

    minutes = max(1, round((end - start) / step))
    return {
        "start_w": start, "end_w": end, "minutes": minutes,
        "start_source": {"kind": start_from, "label": SOURCE_LABEL[start_from],
                         "share": CURVE_TARGET_SHARE if start_from != "ftp" else None},
        "end_source": {"kind": end_from, "label": SOURCE_LABEL[end_from],
                       "lead": lead, "reserve_min": RAMP_END_RESERVE_MIN,
                       "reserve_w": round(reserve)},
        "step_w_per_min": RAMP_STEP_W_PER_MIN,
    }


def scaled(entry: dict[str, Any], ftp: float | None, aerobic_hr: int | None,
           max_hr: float | None = None, curve: dict[str, Any] | None = None,
           blocks: dict[str, Any] | None = None,
           ramp: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fill in the athlete's own numbers: watts from the MEASURED curve where
    it carries, from the FTP where it does not - and the origin travels with
    the session, so a changed number is explainable instead of surprising."""
    out = dict(entry)
    if ftp:
        out["blocks_w"] = [(block[0], round(ftp * block[1] / 100), block[2], *block[3:])
                           for block in entry["blocks"]]
        out["text_w"] = _text_in_watts(entry, ftp)
        out["watt_source"] = "ftp"
    # Die harten Familien: Watt UND Herzfrequenz aus DERSELBEN Messung. Eine
    # Wattvorgabe, die mitwandert, neben einem HF-Fenster aus einer fremden
    # Schwelle waere in drei Monaten auseinander - gemessen wandern beide
    # gemeinsam (216 -> 251 W bei 176 -> 185 bpm, PROJEKTSTAND §7).
    fam = entry.get("family") or _family_of(entry.get("key"))

    # --- Der Stufentest hat ZWEI Anker und deshalb einen eigenen Weg ----------
    # Er ist keine Trainingseinheit mit einer Vorgabe, sondern eine Messung mit
    # einem Anfang und einem Ende, die aus VERSCHIEDENEN Quellen kommen. Die
    # gemeinsame Mechanik unten kennt nur eine Quelle je Einheit und koennte
    # das nicht abbilden.
    if entry.get("key") == "ramp_test":
        proto = ramp_protocol(ftp, curve, blocks, ramp)
        if proto:
            staged = [
                (RAMP_WARMUP_MIN, proto["start_w"], "Einrollen, ruhig"),
                (proto["minutes"], proto["end_w"],
                 f"Rampe {proto['start_w']}\u2013{proto['end_w']} W "
                 f"({RAMP_STEP_W_PER_MIN} W/min) — sie endet am alpha-Wert, nicht an der Uhr"),
                (RAMP_COOLDOWN_MIN, proto["start_w"], "Ausrollen, konstant"),
            ]
            out["blocks_w"] = staged
            out["ramp_protocol"] = proto
            # Was das Panel braucht, um eine Rampe ALS Rampe zu zeichnen: den
            # Abschnitt, seine beiden Enden, und dieselben Prozentwerte, in
            # denen der Balken rechnet. Ohne das stehen drei flach gleich hohe
            # Bloecke da und der Text nennt einen Mittelwert.
            out["ramp_segment"] = {
                "index": 1, "label": staged[1][2],
                "start_w": proto["start_w"], "end_w": proto["end_w"],
                "start_pct": round(proto["start_w"] / ftp * 100),
                "end_pct": round(proto["end_w"] / ftp * 100),
            }
            out["minutes"] = sum(block[0] for block in staged)
            out["template_minutes"] = entry.get("minutes")
            out["watt_source"] = proto["end_source"]["kind"]
            out["text_w"] = (
                f"- {RAMP_WARMUP_MIN}m {proto['start_w']}w  (Einrollen, ruhig)\n"
                f"- {proto['minutes']}m ramp {proto['start_w']}-{proto['end_w']}w  "
                f"({RAMP_STEP_W_PER_MIN} W/min, nicht ERG)\n"
                f"- {RAMP_COOLDOWN_MIN}m {proto['start_w']}w  (gleich bleiben, nicht abkürzen)")
        # UNVERAENDERT bis Punkt 3 entschieden ist: das Fenster kommt weiter
        # aus `hr_hint`. Es ist nachweislich falsch (0,70-1,00 der AEROBEN
        # Schwelle, waehrend die Rampe bis ueber die anaerobe geht) - aber ein
        # Schritt, der Punkt 1 und 2 baut, entscheidet Punkt 3 nicht nebenbei.
            # Der Rechenweg gehoert an die Karte, nicht in den Commit: wer
            # 307 W liest, muss sehen, dass 257 W gemessen sind und 50 W eine
            # Setzung. `derivation` ist das Feld, das die Karte dafuer schon
            # hat - es stand seit 0.51.0 leer, weil niemand es mehr fuellte.
            out["derivation"] = [
                f"Start {proto['start_w']} W — {proto['start_source']['label']}"
                + (f" (Anteil {proto['start_source']['share']:.2f} der Schwelle)"
                   if proto["start_source"]["share"] else ""),
                f"Ende {proto['end_w']} W — {proto['end_source']['label']}"
                + (f": Leitzahl {proto['end_source']['lead']['watts']} W"
                   + (f" bei alpha {proto['end_source']['lead']['alpha']:.2f}"
                      if proto["end_source"]["lead"].get("alpha") else "")
                   if proto["end_source"]["lead"] else ""),
                f"Reserve {proto['end_source']['reserve_w']} W = "
                f"{proto['end_source']['reserve_min']} min × {RAMP_STEP_W_PER_MIN} W/min. "
                "SETZUNG — die Literatur nennt dafür nichts. Ohne sie endet die Rampe "
                "auf der eigenen Leitzahl, und die flache Strecke unter 0,5 wird nie "
                "aufgezeichnet.",
                f"Dauer {proto['minutes']} min = ({proto['end_w']} − {proto['start_w']}) W "
                f"÷ {RAMP_STEP_W_PER_MIN} W/min. Gerechnet, nicht gesetzt.",
            ]
        _apply_hr_hint(out, entry, aerobic_hr, max_hr)
        return out

    measured = ((blocks or {}).get("families") or {}).get(fam) if blocks else None
    if measured and measured.get("source_ok") and measured.get("latest"):
        latest = measured["latest"]
        staged = []
        for block in entry["blocks"]:
            if len(block) > 3 and block[3] or str(block[2]).lower().startswith(("block", "1", "2", "3", "4")):
                staged.append((block[0], latest["median_watts"], block[2], *block[3:]))
            else:
                staged.append((block[0], round(ftp * block[1] / 100) if ftp else None,
                               block[2], *block[3:]))
        out["blocks_w"] = staged
        out["text_w"] = watts_text(staged) or out.get("text_w")
        out["watt_source"] = "blocks"
        out["block_source"] = {
            "date": latest["date"], "alpha": latest["median_alpha"],
            "n_blocks": latest["n_blocks"], "watts": latest["median_watts"],
            "sessions": measured["sessions"], "from": measured["from"], "to": measured["to"],
        }
        window = measured.get("hr_window")
        if window:
            out["hr_window"] = (window["low"], window["high"])
            out["hr_source"] = {**window, "family": fam}
        return out

    if curve and fam in CURVE_FAMILIES:
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
            # DIE MESSUNG IST NICHT DIE VORGABE. `at["watts"]` ist die
            # gemessene Schwelle; gefahren wird ein ANTEIL davon - sonst sitzt
            # eine Grundlageneinheit auf der Schwelle statt darunter, und die
            # Wattseite widerspricht der Pulsseite derselben Karte.
            target = round(at["watts"] * CURVE_TARGET_SHARE)
            staged.append((block[0], target, block[2], *block[3:]))
            changed = True
            out.setdefault("curve_blocks", []).append(
                {"label": block[2], "watts": target, "threshold": at["watts"],
                 "share": CURVE_TARGET_SHARE, "source": at["source"],
                 "n": at["n"], "hour": at["hour"]})
        if changed:
            out["curve_share"] = CURVE_TARGET_SHARE
            out["blocks_w"] = staged
            out["text_w"] = watts_text(staged) or out.get("text_w")
            out["watt_source"] = "curve"
    # --- Der Stufentest als naechste Stufe (N2) -------------------------------
    # Er steht NACH der Blockmessung und NACH der Kurve, weil SOURCE_CHAIN es
    # so sagt - fuer Tempo und Schwelle ist er die erste Stufe, weil dort
    # nichts darueber liegt. Hat eine hoehere Stufe getragen, ist hier
    # nichts mehr zu tun.
    if out.get("watt_source") not in (None, "ftp"):
        return out
    chain = SOURCE_CHAIN.get(fam or "", ("ftp",))
    want = next((step for step in chain if step.startswith("ramp_")), None)
    node = None
    if want and ramp:
        node = (ramp.get("result") or {}).get(
            "hrvt2" if want == "ramp_hrvt2" else "hrvt1")
    # BEIDE Seiten aus derselben Quelle (0.47.1). Traegt der Test an dieser
    # Stelle keine Herzfrequenz, wird er auch fuer die Watt nicht benutzt -
    # sonst faellt eine Seite auf ihn und die andere auf die aerobe Schwelle,
    # und genau das ist der Gleichstandsfehler, gegen den 0.47.1 gebaut wurde.
    if node and node.get("watts") and node.get("hr"):
        # Die MESSUNG IST NICHT IMMER DIE VORGABE: an der zweiten Schwelle ist
        # die gemessene Leistung dieselbe Groesse wie die Leitzahl und wird
        # direkt uebernommen; an der ersten ist sie eine SCHWELLE, und gefahren
        # wird derselbe Anteil davon wie bei der Kurve - eine Regel, nicht zwei.
        share = 1.0 if want == "ramp_hrvt2" else CURVE_TARGET_SHARE
        target = round(float(node["watts"]) * share)
        staged = []
        changed = False
        for block in entry["blocks"]:
            # WELCHE Abschnitte die Zahl bekommen, entscheidet dieselbe Regel
            # wie bei der Stufe, die der Test ersetzt - sonst faehrt dieselbe
            # Einheit je nach Quelle eine andere FORM. Bei der zweiten Schwelle
            # sind das die Arbeitsbloecke (wie bei der Blockmessung), bei der
            # ersten der gleichmaessige Hauptteil (wie bei der Kurve).
            work = (len(block) > 3 and block[3]) or (
                want == "ramp_hrvt2"
                and str(block[2]).lower().startswith(("block", "1", "2", "3", "4")))
            if work:
                staged.append((block[0], target, block[2], *block[3:]))
                changed = True
            else:
                staged.append((block[0], round(ftp * block[1] / 100) if ftp else None,
                               block[2], *block[3:]))
        if changed:
            out["blocks_w"] = staged
            out["text_w"] = watts_text(staged) or out.get("text_w")
            out["watt_source"] = want
            out["ramp_source"] = {
                "alpha": node.get("alpha"), "watts": node.get("watts"),
                "hr": node.get("hr"), "date": ramp.get("date"),
                "share": share,
            }
            # Die Pulsseite kommt aus DEMSELBEN Messpunkt. Ein Punkt, kein
            # Fenster - eine Breite dazuzuerfinden waere eine Setzung, die
            # niemand belegen kann.
            # Ueber .get() aus Gewohnheit, nicht aus Pflicht: die Bauregel
            # dazu (§9, ERSTE der zwei aus 0.41.0) gilt ihrem Wortlaut nach
            # fuer TESTCODE, nicht fuer dieses Modul. Der Satz stand hier
            # frueher mit falscher Nummer und ohne diesen Vorbehalt - und hat
            # damit zwei Sitzungen lang einen Befund erzeugt, den es nicht
            # gab (§7, sechzehnter Fall). node["watts"] drei Zeilen weiter
            # oben ist deshalb KEIN Verstoss; es steht unter der Vorpruefung
            # in derselben Bedingung und kann nicht fehlen.
            _hr = node.get("hr")
            out["hr_point"] = round(float(_hr)) if _hr else None
            out["hr_source"] = {"kind": want, "family": fam,
                                "hr": out["hr_point"], "date": ramp.get("date")}
            return out

    _apply_hr_hint(out, entry, aerobic_hr, max_hr)
    return out


def _apply_hr_hint(out: dict[str, Any], entry: dict[str, Any],
                   aerobic_hr: int | None, max_hr: float | None) -> None:
    """Das Pulsfenster aus `hr_hint`, als eigener Schritt.

    Herausgezogen in 0.51.1, weil der Stufentest die gemeinsame Mechanik
    frueher verlaesst und sein Fenster sonst STILL verlieren wuerde. Ein
    Schritt, der nur Punkt 1 und 2 aendern soll, darf nicht nebenbei die
    Anzeige veraendern - wo das Fenster herkommt und ob es hier ueberhaupt
    taugt, ist eine eigene Entscheidung.
    """
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
    # Eigene Familie, keine Spielart der langen Fahrt (K1): eine MESSUNG ist
    # eine andere Art von Einheit als ein Training, und unter den langen
    # Fahrten saehe sie aus wie eine haertere Variante davon.
    ("ramp_test", "Stufentest", ["ramp_test"]),
]

# What each state can carry. Not a filter - a verdict per family, so every kind
# of session stays visible and says what it would cost today.
FIT_BY_STATE: dict[str, dict[str, str]] = {
    "slump":      {"recovery": "ok", "return": "maybe", "endurance": "no", "long": "no",
                   "tempo": "no", "sweetspot": "no", "threshold": "no", "vo2max": "no",
                   "ramp_test": "no"},
    "recovering": {"recovery": "ok", "return": "ok", "endurance": "maybe", "long": "no",
                   "tempo": "no", "sweetspot": "no", "threshold": "no", "vo2max": "no",
                   "ramp_test": "no"},
    "rebound":    {"recovery": "ok", "return": "ok", "endurance": "ok", "long": "maybe",
                   "tempo": "maybe", "sweetspot": "maybe", "threshold": "no", "vo2max": "no",
                   "ramp_test": "no"},
    "strained":   {"recovery": "ok", "return": "ok", "endurance": "ok", "long": "maybe",
                   "tempo": "maybe", "sweetspot": "maybe", "threshold": "no", "vo2max": "no",
                   "ramp_test": "no"},
    "ready":      {"recovery": "ok", "return": "ok", "endurance": "ok", "long": "ok",
                   "tempo": "ok", "sweetspot": "ok", "threshold": "ok", "vo2max": "ok",
                   "ramp_test": "ok"},
    "elevated":   {"recovery": "ok", "return": "ok", "endurance": "ok", "long": "maybe",
                   "tempo": "maybe", "sweetspot": "maybe", "threshold": "no", "vo2max": "no",
                   "ramp_test": "no"},
    "unknown":    {"recovery": "ok", "return": "ok", "endurance": "ok", "long": "maybe",
                   "tempo": "maybe", "sweetspot": "maybe", "threshold": "maybe", "vo2max": "maybe",
                   "ramp_test": "no"},
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
    if family_key == "ramp_test" and verdict != "ok" and reason == FIT_REASON.get(state, ""):
        reason = ("Bei gelbem oder rotem Zustand misst der Test deine Müdigkeit statt "
                  "deiner Schwellen. Das ist kein Sicherheitshinweis, sondern ein "
                  "Messfehler: die Zahl wäre später nicht mehr von einer echten "
                  "Veränderung zu unterscheiden.")
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


def watts_text(blocks: list[tuple]) -> str | None:
    """Die Schrittliste fuer Abschnitte, die schon WATT tragen.

    `steps_text(blocks, None)` liest `block[1]` als Prozent - richtig fuer die
    Vorlage, falsch fuer gestaffelte Abschnitte aus Kurve, Bloecken oder
    Stufentest, die an dieser Stelle Watt tragen. Bis 0.56.0 stand dort
    "45m 135%" fuer 135 W (PROJEKTSTAND §7). Fehlt einem Abschnitt die Zahl
    (keine FTP fuer Ein- und Ausrollen), gibt es KEINE Wattliste statt einer
    halben: die Vorlage bleibt stehen und sagt, dass sie Prozent ist.
    """
    if not blocks or any(block[1] is None for block in blocks):
        return None
    return "\n".join(f"- {block[0]}m {block[1]}w  ({block[2]})" for block in blocks)


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
            curve: dict[str, Any] | None = None,
            blocks: dict[str, Any] | None = None,
            ramp: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """One session per family, each judged for today - never filtered away.

    The earlier version filtered: in a rebound state everything hard vanished
    and three base rides were left, which is not a choice. This keeps every
    kind of session visible and attaches the verdict to it, because the
    decision is the athlete's; the data's job is to say what it costs.
    """
    order = {
        "long_ride": ["long", "endurance", "ramp_test", "sweetspot", "tempo", "threshold", "vo2max", "recovery", "return"],
        "ftp": ["threshold", "sweetspot", "endurance", "vo2max", "tempo", "long", "ramp_test", "recovery", "return"],
        "vo2max": ["vo2max", "threshold", "endurance", "sweetspot", "tempo", "long", "ramp_test", "recovery", "return"],
        "health": ["endurance", "tempo", "recovery", "sweetspot", "threshold", "vo2max", "long", "ramp_test", "return"],
    }.get(goal or "", ["endurance", "vo2max", "sweetspot", "threshold", "tempo", "long", "ramp_test", "recovery", "return"])

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
        entry = dict(scaled(BY_KEY[key], ftp, aerobic_hr, max_hr, curve, blocks, ramp))
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
                  max_hr: float | None = None,
                  curve: dict[str, Any] | None = None,
                  blocks: dict[str, Any] | None = None,
                  ramp: dict[str, Any] | None = None) -> list[dict[str, Any]]:
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
        full = scaled(template, ftp, aerobic_hr, max_hr, curve, blocks, ramp)
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
