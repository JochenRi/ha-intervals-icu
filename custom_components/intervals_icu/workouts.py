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
        BLOCK_HR_WINDOW_SD_FACTOR,
        DURABILITY_FUELLING_G_PER_H,
        RAMP_COOLDOWN_MIN,
        RAMP_END_RESERVE_MIN,
        RAMP_EXPECTED_MIN,
        RAMP_FALLBACK_END_PCT,
        RAMP_FALLBACK_START_PCT,
        RAMP_STEP_W_PER_MIN,
        RAMP_WARMUP_MIN,
        CURVE_TARGET_SHARE,
        STEERING_STEP_W,
    )
except ImportError:  # standalone (test suite loads this file directly)
    from const import (  # type: ignore[no-redef]
        BLOCK_HR_WINDOW_SD_FACTOR,
        DURABILITY_FUELLING_G_PER_H,
        RAMP_COOLDOWN_MIN,
        RAMP_END_RESERVE_MIN,
        RAMP_EXPECTED_MIN,
        RAMP_FALLBACK_END_PCT,
        RAMP_FALLBACK_START_PCT,
        RAMP_STEP_W_PER_MIN,
        RAMP_WARMUP_MIN,
        CURVE_TARGET_SHARE,
        STEERING_STEP_W,
    )

# 0.72.0 (Skizze 2): der ehrliche Zusatz fuer die Schwellen-Formen, EIN Satz.
NEAL_NOTE = ("Ehrlich dazu: in Vergleichsstudien schnitten Schwellengruppen schlechter ab als polarisiertes Training (Neal et al. 2013, J Appl Physiol, PMID 23264537, 12 Radfahrer; Stöggl & Sperlich 2014).")

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
                    "Rogers/Gronwald 2021b (Laufband) die anaerobe Schwelle. " + NEAL_NOTE,
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
                    "(4×10 → 3×15 → 2×20), erst zuletzt Intensität. " + NEAL_NOTE,
        "limit": "Wer im zweiten Block schon 15 Watt verliert, ist noch nicht bei 2×20.",
        "states": ["ready"],
    },
    # 0.72.0 (Skizze 2, Entscheidung Johannes 26.09.): drei belegte Formen dazu -
    # je Familie mindestens fuenf verschieden belastende Einheiten. Die FAMILIE
    # bestimmt die Wattquelle (SOURCE_CHAIN unveraendert). Intensitaet und Hoehe
    # der Bloecke wie die Geschwister der Familie; die LAST ist aus den Bloecken
    # gerechnet (Dauer x IF^2 x 100, gerundet) - eine Setzung wie die Lasten der
    # anderen Eintraege. Wo die Studie ueber Herzfrequenz oder Laktat steuert,
    # ist die Uebertragung auf Watt als Setzung beschriftet.
    {
        "key": "threshold_4x16",
        "title": "Schwellennah 4×16 min",
        "purpose": "Schwellenleistung, lange Blöcke",
        "minutes": 93,
        "intensity": 83,
        "load": 90,
        "blocks": [(15, 55, "Einrollen"), (16, 90, "1"), (2, 55, "Pause"), (16, 90, "2"),
                   (2, 55, "Pause"), (16, 90, "3"), (2, 55, "Pause"), (16, 90, "4"), (8, 50, "Ausrollen")],
        "text": "- 15m 55% 85rpm\n\n4x\n- 16m 88-93% 88rpm\n- 2m 55%\n\n- 8m 50%",
        "hr_hint": (1.02, 1.08),
        "dfa": "0,5–0,75 in den Blöcken, gegen Ende des vierten Blocks eher darunter",
        "effect": "64 Minuten Arbeit knapp unter der Schwelle in vier langen Stücken — viel "
                  "Zeit im Bereich, mit kurzen Pausen, die den Puls kaum fallen lassen.",
        "evidence": "Seiler et al. 2013, Scand J Med Sci Sports 23:74–83, PMID 21812820 "
                    "(35 Radfahrer, gefahren bei 88 % der maximalen HF); Sylta et al. 2016, "
                    "Med Sci Sports Exerc, PMID 27300278 (63 Radfahrer). Die Studien steuern "
                    "über die HF — die Übertragung auf Watt (88–93 % FTP bzw. deine "
                    "SweetSpot-Vorgabe) ist eine Setzung. " + NEAL_NOTE,
        "limit": "Bei Seiler lag 4×16 hinter 4×8 — der Reiz ist die Dauer, nicht die Spitze. "
                 "Wer im vierten Block deutlich Leistung verliert, ist zu hoch gestartet.",
        "states": ["ready"],
    },
    {
        "key": "threshold_5x6",
        "title": "Schwelle 5×6 min",
        "purpose": "FTP, kurze Blöcke",
        "minutes": 61,
        "intensity": 85,
        "load": 61,
        "blocks": [(15, 55, "Einrollen"), (6, 97, "1"), (2, 50, "Pause"), (6, 97, "2"),
                   (2, 50, "Pause"), (6, 97, "3"), (2, 50, "Pause"), (6, 97, "4"),
                   (2, 50, "Pause"), (6, 97, "5"), (8, 50, "Ausrollen")],
        "text": "- 15m 55% 85rpm\n\n5x\n- 6m 95-100% 90rpm\n- 2m 50%\n\n- 8m 50%",
        "hr_hint": (1.04, 1.11),
        "dfa": "um 0,5 in den Blöcken",
        "effect": "Schwellenarbeit in kurzen Stücken — 30 Minuten an der Schwelle, sauber "
                  "zu halten, auch wenn die Form noch nicht für 10-Minuten-Blöcke reicht.",
        "evidence": "Stöggl & Sperlich 2014, Front Physiol, PMID 24550842, Schwellengruppe "
                    "(gemischte Ausdauersportler). Die Studie steuert über Laktat/HF an der "
                    "Schwelle — die Übertragung auf Watt (95–100 % FTP) ist eine Setzung. " + NEAL_NOTE,
        "limit": "Kurze Pausen, kurze Blöcke: die Einheit wirkt über die Summe. Als "
                 "einzige harte Einheit der Woche liegt sie hinter VO2max-Formen.",
        "states": ["ready"],
    },
    {
        "key": "threshold_3x15",
        "title": "Schwelle 3×15 min",
        "purpose": "FTP, Progression",
        "minutes": 74,
        "intensity": 87,
        "load": 84,
        "blocks": [(15, 55, "Einrollen"), (15, 97, "1"), (3, 55, "Pause, aktiv"), (15, 97, "2"),
                   (3, 55, "Pause, aktiv"), (15, 97, "3"), (8, 50, "Ausrollen")],
        "text": "- 15m 55% 85rpm\n\n3x\n- 15m 95-100% 90rpm\n- 3m 55%\n\n- 8m 50%",
        "hr_hint": (1.05, 1.12),
        "dfa": "um 0,5 in den Blöcken, im dritten eher darunter",
        "effect": "Die mittlere Stufe der Schwellen-Progression: 45 Minuten an der Schwelle in "
                  "drei Stücken — der Schritt von 4×10 in Richtung 3×20.",
        "evidence": "Stöggl & Sperlich 2014, Front Physiol, PMID 24550842, dieselbe "
                    "Schwellengruppe. Die Studie steuert über Laktat/HF — die Übertragung auf "
                    "Watt (95–100 % FTP) ist eine Setzung. " + NEAL_NOTE,
        "limit": "Progression: sitzen drei Blöcke sauber, folgt 3×20 min mit derselben "
                 "Leistung — erst die Dauer, dann die Intensität.",
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

# 0.72.0 (Skizze 3): JEDE KARTE TRAEGT IHRE KENNUNG - Studie oder Konvention,
# mit Quelle. Geprueft vom Vorarbeiter am 26.09. (PubMed/Volltexte). Nichts wird
# wegen "Konvention" entfernt; der alte Belegtext bleibt und steht dahinter.
# Die drei neuen Eintraege tragen ihre Quelle schon im Text.
EVIDENCE_KIND: dict[str, tuple[str, str]] = {
    "vo2_4x4": ("Studie", "Helgerud et al. 2007, Med Sci Sports Exerc, PMID 17414804 (Läufer); "
                          "Rad: Seiler et al. 2013"),
    "vo2_5x4": ("Konvention", "keine eigene Studie gefunden; Progression von 4×4"),
    "vo2_4x8": ("Studie", "Seiler et al. 2013, Scand J Med Sci Sports, PMID 21812820 (Radfahrer): "
                          "+11,4 % VO2peak gegen 4,2–5,6 %"),
    "vo2_3015": ("Studie", "Rønnestad et al. 2015, doi 10.1111/sms.12165 (Radfahrer); "
                           "Rønnestad et al. 2020, PMID 31977120"),
    "vo2_3030": ("Studie (Akutversuch, Läufer)", "Billat et al. 2000, Eur J Appl Physiol, PMID 10638376"),
    "sweetspot_2x20": ("Konvention", "Praxis (Allen & Coggan zugeschrieben, nicht belegt); keine Studie"),
    "tempo_2x20": ("Konvention", "keine Studie"),
    "threshold_4x10": ("Konvention", "keine Studie zu genau dieser Form"),
    "threshold_3x12": ("Konvention", "keine Studie zu genau dieser Form"),
    "z2_60": ("Studie (Beobachtung)", "Seiler & Kjerland 2006, PMID 16430681; Stöggl & Sperlich 2014"),
    "z2_90": ("Studie (Beobachtung)", "Seiler & Kjerland 2006, PMID 16430681; Stöggl & Sperlich 2014"),
    "recovery_40": ("Studie (Beobachtung)", "Seiler & Kjerland 2006, PMID 16430681; Stöggl & Sperlich 2014"),
    "z2_150": ("Konzept", "Maunder et al. 2021, Sports Med, PMID 33886100 (Übersicht)"),
    "z2_210_late": ("Konvention", "keine Quelle im Code"),
    "threshold_4x16": ("Studie", ""), "threshold_5x6": ("Studie", ""), "threshold_3x15": ("Studie", ""),
    # NICHT in der Tabelle der Skizze (Vorarbeiter) - aus dem eigenen Belegtext
    # der Einheit gelesen, im Bericht 0.72.0 zur Pruefung vorgelegt:
    "return_45": ("Konvention", "Return-to-Sport-Praxis (Stufenleiter nach Pause oder Infekt)"),
}
for _entry in LIBRARY:
    _kind, _src = EVIDENCE_KIND[_entry["key"]]
    _entry["evidence_kind"] = _kind
    _entry["evidence"] = f"{_kind} — {_src + '. ' if _src else ''}{_entry['evidence']}"

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
    # 0.72.0 (Skizze 3): Kennung wie jede Karte - der Stufentest steht NICHT in der
    # Tabelle der Skizze; "Studie" aus dem eigenen Belegtext, im Bericht vorgelegt.
    "evidence_kind": "Studie",
    "evidence": ("Studie — Rogers u. a. (2021a/b): DFA a1 erreicht 0,75 an der ersten und 0,5 an "
                 "der zweiten Schwelle. Beide kommen vom LAUFBAND; für das Rad "
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
    f"{RAMP_WARMUP_MIN} Minuten ruhig und flach einrollen. Ob Rogers 2021a/b (Laufband) "
    "oder Olieslagers 2026 (Rad) ein Einrollen vorgeben, ist nicht nachgelesen — diese "
    "Zeit ist GESETZT, und die Gründe sind unsere Auswertung: "
    "der alpha-Wert braucht ein bis zwei Minuten, bis er eingeschwungen ist, und "
    "das Rechenfenster ist zwei Minuten breit. Und die Suche nach deinem höchsten "
    f"alpha-Wert beginnt erst nach diesen {RAMP_WARMUP_MIN} Minuten, am Rampenbeginn — "
    "deshalb muss das Einrollen FLACH sein: steigt die Leistung schon hier, wird die "
    "Fahrt nicht ausgewertet.",
    f"Dann je Minute {RAMP_STEP_W_PER_MIN} Watt mehr, bis du nicht mehr kannst. "
    "Olieslagers 2026 fuhr auf dem Rad eine flache Rampe; Rogers 2021a/b kamen vom "
    "Laufband, wo die Steigung anders zählt. Unsere ist FLACH und wächst nicht "
    "mit deiner Stärke: bei steileren "
    "Rampen hinkt die Sauerstoffaufnahme hinterher, und dann ist die Wattzahl "
    "nicht mehr ablesbar. Der Preis ist ein längerer Test.",
    "Während der Rampe: gleichmäßig treten, nicht aus dem Sattel, Trittfrequenz "
    "konstant halten, nicht sprechen. Alles davon verändert die Abstände zwischen "
    "den Herzschlägen — und die sind die Messung.",
    "Abbrechen, wenn du nicht mehr kannst — in Rogers 2021a (Laufband) hieß das "
    "Abbruchkriterium ebenfalls willentliche Erschöpfung, ein Zustand und keine "
    "Wattzahl. Das ist VORGESEHEN und kein Fehlversuch. Für die zweite Schwelle muss "
    "dein alpha vorher stabil unter 0,5 gewesen sein; ausgewertet wird die Fahrt aber "
    "überhaupt nur, wenn Einrollen und Ausrollen wie beschrieben gefahren sind. "
    "Kommst du nicht unter 0,5, fehlt die zweite "
    "Schwelle — die erste steht trotzdem. Und die erste ist die schwächere: "
    "Olieslagers 2026 fand für sie am Rad schlechte Übereinstimmung mit LT1/VT1 "
    "(Bias −21 bis −45 W), für die zweite dagegen deutlich bessere. Die 0,75 "
    "stammt vom LAUFBAND.",
    f"Danach {RAMP_COOLDOWN_MIN} Minuten ausrollen, bei derselben ruhigen "
    "Leistung, gleich bleibend. NICHT abkürzen und nicht verlängern: diese Zeit ist "
    "Teil der Messung. Und das Ende deiner Belastung wird als Fahrtlänge minus "
    f"{RAMP_COOLDOWN_MIN} Minuten gerechnet — weicht das Ausrollen um zwei Minuten "
    "oder mehr ab, sitzt dieses Ende falsch und die Fahrt wird nicht ausgewertet; "
    "eine kleinere Abweichung kann das Ergebnis verschieben, ohne dass es auffällt. "
    "Ob die Arbeiten eine Ausrolldauer vorgeben, ist nicht nachgelesen — gesetzt "
    "ist sie, weil Michael "
    "u. a. 2017 die parasympathische Reaktivierung im Fenster 0 bis 10 Minuten "
    "nach Belastungsende betrachtet (die vollständige Rückkehr dauert laut "
    "Stanley/Peake/Buchheit 2013 24 bis 72 Stunden). Gleiche Haltung und gleiche Leistung wie "
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
    "ausgewiesene Ende früher nicht mehr, ist das kein Fehlversuch; die zweite "
    "Schwelle steht, wenn dein alpha vorher stabil unter 0,5 lag. Fährst du darüber hinaus, ist das auch "
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


# DIE KETTE HAT EINEN ERZEUGER (0.67.4, Sollzustand S3 - Entscheidung 24.09.,
# "Wahl 2 mit Schranke"): die Einheit liest die Kette der Ermuedungskachel
# (`curve["plan"]`, Kette A) bei der GEPLANTEN DAUER - dieselbe Frage wie die
# Kachel ("welche Leistung haelt sich ueber eine Fahrt dieser Laenge"). Bis
# 0.67.3 baute `curve_watts` eine ZWEITE Kette aus `measured`/`paired` (Abbruch
# unter 6 Paaren, Stundenmitte des Hauptabschnitts, Studienform darueber
# hinaus) - zwei Antworten aus denselben Stunden (Karte F2.3, W3.3).
#
# DIE SCHRANKE: eine Stunde zaehlt als belegt ab CURVE_HOUR_MIN_RIDES Fahrten.
# Ist die Stunde der Dauer nicht belegt, gilt die letzte gut belegte davor -
# auch jenseits des belegten Bereichs, statt der Studienform. Grund: sonst laese
# die 3,5-h-Einheit auf einer Stunde mit einer Fahrt.
#
# DIE RUNDUNG: nur VOLLE Stunden zaehlen, mindestens eine (planned_hour). Eine
# 2,5-h-Fahrt liest bei 2 h - die Kette sagt "fuer eine Fahrt von 2 h", und
# die dritte Stunde ist bei 2,5 h nicht gefahren.
CURVE_HOUR_MIN_RIDES = 3

# AB 3 H UNGEPRUEFT (0.68.0): die Kette der Umkehrung ist bis zur Abnahmefahrt
# (3 h bei ~Ziel der dritten Stunde) nicht gegen eine gefahrene Einheit
# geprueft. Jede Einheit ab so vielen GEPLANTEN Stunden traegt `unverified` -
# auch wenn sie mangels Belegung an einer frueheren Stunde abliest, denn
# gefahren wird die geplante Dauer.
GA_UNVERIFIED_FROM_HOUR = 3


def planned_hour(minutes: float) -> int:
    """Die Kettenstelle einer geplanten Dauer: volle Stunden, mindestens 1."""
    return max(1, int(float(minutes) // 60))


def ga_at(ga: dict[str, Any] | None, minutes: float) -> dict[str, Any] | None:
    """Ziel und Grenze der Umkehrung fuer eine Fahrt von `minutes` (0.68.0).

    Dieselbe Ablesestelle wie 0.67.4: volle Stunden (planned_hour), belegt ab
    CURVE_HOUR_MIN_RIDES Fahrten, sonst die letzte gut belegte Stunde davor -
    auch jenseits des belegten Bereichs. None ohne belegte Stunde.
    """
    rows = {int(r["hours"]): r for r in ((ga or {}).get("hours") or []) if r.get("hours") is not None}
    if not rows:
        return None
    hour = min(planned_hour(minutes), max(rows))
    while hour >= 1 and (hour not in rows or int(rows[hour].get("n") or 0) < CURVE_HOUR_MIN_RIDES):
        hour -= 1
    if hour < 1:
        return None
    r = rows[hour]
    return {"hour": hour, "n": int(r.get("n") or 0), "load_w": r.get("load_w"), "alpha": r.get("alpha"),
            "limit": round(float(r["limit_w"])),
            "target": (None if r.get("target_w") is None else round(float(r["target_w"])))}


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
# DER STUFENTEST STEUERT VORERST NICHTS (Johannes, 16.09.2026, Variante B).
# Bis 0.59.0 stand er hier als Stufe `ramp_hrvt2` (VO2max, SweetSpot, Tempo,
# Schwelle) und `ramp_hrvt1` (Grundlage, lang). Der Zweig in `scaled()` setzt
# aber jeden Arbeitsblock auf HRVT2 x 1,0 - am Test vom 16.09.2026 haetten vier
# Familien dieselben 233 W bekommen. Unsichtbar, solange hrvt2 immer leer war;
# Rechenweg e1 haette ihn scharf geschaltet (§7, achtunddreissigster Fall).
# Die Messung steht auf der Karte; wie daraus eine Vorgabe wird, ist ein eigener
# Auftrag (PROJEKTSTAND §10: Ablesung je alpha-Korridor statt Anteil einer
# Schwelle). Der Zweig in `scaled()` bleibt stehen und ist unerreichbar - ein
# Waechter in test_workouts haelt beides fest.
SOURCE_CHAIN: dict[str, tuple[str, ...]] = {
    "vo2max":    ("blocks", "ftp"),
    "sweetspot": ("blocks", "ftp"),
    "tempo":     ("ftp",),
    "threshold": ("ftp",),
    # 0.68.0: die Grundlage liest Ziel und Grenze der Umkehrung ("ga"), nicht
    # mehr die p075-Kette ("curve").
    "endurance": ("ga", "ftp"),
    "long":      ("ga", "ftp"),
}

# Wie jede Stufe heisst, wenn die Karte sie nennt. Eine Zahl OHNE Herkunft ist
# in diesem Projekt schon zweimal als Messung gelesen worden, die keine war -
# deshalb traegt AUCH der Rueckfall eine Beschriftung.
SOURCE_LABEL: dict[str, str] = {
    "blocks": "gemessen an deinen Arbeitsblöcken",
    # Dieselbe Messung, aber als VORGABE gefuehrt: die Zahl folgt nicht mehr
    # der letzten Einheit, sondern dem Startwert plus den Schritten, die C6
    # seither gerechnet hat.
    "steering": "deine Vorgabe — Startwert plus gerechnete Schritte",
    "curve": "gemessen an deiner Ermüdungskurve",
    "ga": "Setzung: Ziel und Grenze der Ermüdungskachel für diese Dauer",
    "ramp_hrvt2": "gemessen im Stufentest, zweite Schwelle",
    "ramp_hrvt1": "gemessen im Stufentest, erste Schwelle",
    "ftp": "Rückfall auf die FTP — nicht gemessen",
}


RAMP_START_CHAIN: tuple[str, ...] = ("ga", "ramp_hrvt1", "ftp")
# Die Steuerung steht VOR den Bloecken: sie ist dieselbe Messung, nur als
# Vorgabe gefuehrt. Ohne Schalter ist ihre Stufe nicht erreichbar und die
# Kette ist die von 0.60.0.
RAMP_END_CHAIN: tuple[str, ...] = ("steering", "blocks", "ramp_hrvt2", "ftp")


def _ramp_node(ramp: dict[str, Any] | None, which: str) -> dict[str, Any] | None:
    """Eine Schwelle aus einem markierten Stufentest, oder nichts."""
    node = ((ramp or {}).get("result") or {}).get(which)
    return node if isinstance(node, dict) and node.get("watts") else None


def ramp_protocol(ftp: float | None, curve: dict[str, Any] | None = None,
                  blocks: dict[str, Any] | None = None,
                  ramp: dict[str, Any] | None = None,
                  steering: dict[str, Any] | None = None,
                  ga: dict[str, Any] | None = None) -> dict[str, Any] | None:
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
        if stage_name == "ga":
            # dieselbe Groesse wie die Grundlagenvorgabe fuer eine Stunde (0.68.0):
            # das Ziel der Umkehrung, sonst ihre Grenze
            at = ga_at(ga, 60)
            if at:
                start = at["target"] if at.get("target") is not None else at["limit"]
                start_from = "ga"
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
        if stage_name == "steering":
            # DAS RAMPENENDE FOLGT DER VORGABE, nicht Block 1. Bis 0.60.0 hing
            # es an `first_watts` - der VERLAUFSgroesse, dem frischesten
            # Moment der letzten Einheit. Damit sprang das Ende mit jeder
            # Einheit, und es widersprach der Regel, dass Block 1 nicht
            # steuert. Gerechnet am Livebestand: 307 W (Block 1 257 W) gegen
            # 300 W (Vorgabe 250 W), Dauer 38 gegen 37 min.
            node = (steering or {}).get("vo2max") or {}
            if node.get("watts"):
                lead = {"watts": node["watts"], "alpha": None,
                        "date": node.get("anchor_date"), "source": "steering"}
                end, end_from = round(float(node["watts"]) + reserve), "steering"
                break
        elif stage_name == "blocks":
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
        # DIE AUSWAHL NEBEN DEM MESSWEG. Start und Ende kommen von Natur aus aus
        # zwei Ketten - das ist entworfen und kein Widerspruch. Seit es zwei
        # Schalter gibt, koennen die beiden Ketten aber aus verschiedenen
        # AUSWAHLEN kommen, und eine Zahl ohne Auswahl liest sich dann wie die
        # andere. Sie steht deshalb daneben, nicht in SOURCE_LABEL (dort ist
        # nach dem Messweg verschluesselt).
        "start_source": {"kind": start_from, "label": SOURCE_LABEL[start_from],
                         "share": CURVE_TARGET_SHARE if start_from != "ftp" else None,
                         "selection": None},
        "end_source": {"kind": end_from, "label": SOURCE_LABEL[end_from],
                       "lead": lead, "reserve_min": RAMP_END_RESERVE_MIN,
                       "reserve_w": round(reserve),
                       "selection": (blocks or {}).get("selection") if end_from == "blocks" else None},
        "step_w_per_min": RAMP_STEP_W_PER_MIN,
    }


# Ab welchem Anteil der FTP ein Abschnitt als ARBEIT gilt, wenn die Kachel
# ihre Quellen aufzaehlt. Am Katalog abgelesen, nicht gesetzt: Einrollen,
# Pausen und Ausrollen liegen zwischen 45 und 68 %, jeder Abschnitt darueber
# ist Arbeit - darunter fallen genau die Faelle, um die es hier geht (Satz 1-3
# bei 105 bzw. 112 %, Block 5 bei 112 %).
WORK_PCT_MIN = 80


def _is_work_block(block: tuple) -> bool:
    """Bekommt dieser Block die gemessene Vorgabe?

    DIESELBE Bedingung wie im heutigen Zweig - ein zweiter Begriff von
    "Arbeitsblock" waere die Klasse aus 0.42.2: zwei Bauarten fuer eine Sache
    driften auseinander. Sie steht hier nur EINMAL, damit die Ehrlichkeitsregel
    darunter dieselbe Auswahl beurteilt, die auch gerechnet wird.
    """
    # 0.70.0 (C7, V1): JEDE Blockzahl. Bis 0.69.2 endete die Regel bei "4" -
    # Block 5 einer 5x4 fiel auf die FTP (224 statt 250 W). Ein Etikett, das mit
    # einer Ziffer beginnt oder "Block" heisst, ist ein Arbeitsblock; Saetze,
    # Pausen, Ein- und Ausrollen nicht.
    label = str(block[2]).strip().lower()
    return bool(len(block) > 3 and block[3]
                or label.startswith("block") or label[:1].isdigit())


def _stage_from_measurement(entry: dict[str, Any], ftp: float | None, watts: int,
                            minutes: float | None) -> tuple[list[tuple], list[dict[str, Any]]]:
    """Die Wattliste - und je Block, WOHER seine Zahl kommt."""
    staged: list[tuple] = []
    sources: list[dict[str, Any]] = []
    for block in entry["blocks"]:
        work = _is_work_block(block)
        if work:
            staged.append((block[0], watts, block[2], *block[3:]))
        else:
            staged.append((block[0], round(ftp * block[1] / 100) if ftp else None,
                           block[2], *block[3:]))
        sources.append({
            "label": block[2], "minutes": block[0], "pct": block[1],
            "source": "steering" if work else "ftp",
            # Woran gemessen wurde, gegen das, was hier gefahren wird. Ein
            # Median aus 4-Minuten-Bloecken ist fuer einen 8-Minuten-Block
            # keine Messung, sondern eine Uebertragung - und sie wird benannt,
            # statt die Zahl stillschweigend zu tauschen.
            "stretched": bool(work and minutes and float(block[0]) > minutes * 1.5),
        })
    return staged, sources


def _source_note(sources: list[dict[str, Any]], minutes: float | None) -> str | None:
    """Ein Satz, der sagt, was an dieser Kachel gemessen ist und was nicht."""
    got = [x for x in sources if x["source"] == "steering"]
    # NUR echte Arbeitsabschnitte werden als Rueckfall gemeldet. Einrollen,
    # Pausen und Ausrollen stehen auf der FTP, weil sie dort hingehoeren - sie
    # in denselben Satz zu schreiben, macht aus einer Meldung Rauschen.
    fell = [x for x in sources
            if x["source"] != "steering" and float(x.get("pct") or 0) >= WORK_PCT_MIN]
    stretched = [x for x in got if x["stretched"]]
    if not got:
        return ("Kein Abschnitt dieser Einheit bekommt die gemessene Vorgabe — "
                "die Zahlen stehen auf der FTP.")
    parts = []
    if stretched and minutes:
        labels = " · ".join(str(x["label"]) for x in stretched)
        parts.append(f"Gemessen wurde an {minutes:g}-Minuten-Blöcken; "
                     f"{labels} dauert länger und bekommt dieselbe Zahl.")
    if fell:
        labels = " · ".join(str(x["label"]) for x in fell)
        parts.append(f"{labels} fällt auf die FTP zurück.")
    return " ".join(parts) or None


def scaled(entry: dict[str, Any], ftp: float | None, aerobic_hr: int | None,
           max_hr: float | None = None, curve: dict[str, Any] | None = None,
           blocks: dict[str, Any] | None = None,
           ramp: dict[str, Any] | None = None,
           steering: dict[str, Any] | None = None,
           ga: dict[str, Any] | None = None) -> dict[str, Any]:
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
        proto = ramp_protocol(ftp, curve, blocks, ramp, steering, ga)
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
                + (f", {proto['start_source']['selection']['label']}"
                   if (proto["start_source"].get("selection") or {}).get("label") else "")
                + (f" (Anteil {proto['start_source']['share']:.2f} der Schwelle)"
                   if proto["start_source"]["share"] else ""),
                f"Ende {proto['end_w']} W — {proto['end_source']['label']}"
                + (f", {proto['end_source']['selection']['label']}"
                   if (proto["end_source"].get("selection") or {}).get("label") else "")
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

    # --- STEUERUNG v2, nur bei umgelegtem Schalter ---------------------------
    # Steht der Schalter aus, ist `steering` None und der ganze Zweig
    # existiert nicht - darunter laeuft das heutige Verhalten bitgenau weiter.
    steered = (steering or {}).get(fam) if steering else None
    if steered and steered.get("watts"):
        staged, sources = _stage_from_measurement(entry, ftp, steered["watts"],
                                                  steered.get("measured_minutes"))
        out["blocks_w"] = staged
        out["text_w"] = watts_text(staged) or out.get("text_w")
        # EHRLICH: die Kachel traegt "gemessen" nur, wenn wirklich ein Block
        # die gemessene Zahl bekommen hat. Bis 0.60.0 stand "blocks" auch dort,
        # wo jeder Block auf die FTP zurueckfiel (vo2_3030, vo2_3015) - eine
        # Zahl mit fremdem Etikett, genau die Klasse aus PROJEKTSTAND §7.
        got = [x for x in sources if x["source"] == "steering"]
        out["watt_source"] = "steering" if got else "ftp"
        out["watt_sources"] = sources
        out["steering_source"] = {
            "watts": steered["watts"], "anchor_w": steered.get("anchor_w"),
            "anchor_date": steered.get("anchor_date"),
            "moves": steered.get("moves"), "n_since": steered.get("n_since"),
            "band": steered.get("band"), "hr_band": steered.get("hr_band"),
            "note": steered.get("note"), "band_note": steered.get("band_note"),
            "measured_minutes": steered.get("measured_minutes"),
            "n_units": steered.get("n_units"),
            "single_block": steered.get("single_block"),
            "family": fam,
            "mixed": bool(got) and len(got) != len(sources),
            "note_blocks": _source_note(sources, steered.get("measured_minutes")),
        }
        # WATT UND PULS AUS DERSELBEN QUELLE. Faellt die Wattseite auf die FTP
        # zurueck (vo2_3030, vo2_3015: kein Abschnitt bekommt die gemessene
        # Zahl), dann muss die Pulsseite mitfallen - sonst steht ein gemessenes
        # Fenster neben einer ungemessenen Zahl. Genau der Gleichstand, den
        # test_workouts seit 0.51.0 fuer die alte Kette erzwingt.
        band = steered.get("hr_band") if got else None
        if not got:
            _apply_hr_hint(out, entry, aerobic_hr, max_hr)
        if band:
            out["hr_window"] = (band["low"], band["high"])
            out["hr_source"] = {**band, "family": fam, "source": "steering"}
        elif steered.get("hr_band_note"):
            out["hr_window_note"] = steered["hr_band_note"]
        return out

    measured = ((blocks or {}).get("families") or {}).get(fam) if blocks else None
    if measured and measured.get("source_ok") and measured.get("latest"):
        latest = measured["latest"]
        staged = []
        for block in entry["blocks"]:
            if _is_work_block(block):   # EINE Etikettregel (0.70.0, C7)
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

    if fam in CURVE_FAMILIES and ga is not None:
        # DIE GA-EINHEIT LIEST DIE UMKEHRUNG (0.68.0): Ziel und Grenze der
        # Kachel fuer die geplante Dauer - ein Erzeuger, keine 0,90 mehr. Ohne
        # gueltigen Stufentest (ga["hours"] leer) bleibt die FTP, beschriftet.
        total = sum(float(block[0]) for block in entry["blocks"]) or float(entry.get("minutes") or 0)
        at = ga_at(ga, total)
        unverified = planned_hour(total) >= GA_UNVERIFIED_FROM_HOUR
        if at is None:
            out["ga_missing"] = ga.get("missing") or "kein gültiger Stufentest"
        else:
            staged, changed = [], False
            value = at["target"] if at.get("target") is not None else at["limit"]
            for block in entry["blocks"]:
                if not (len(block) > 3 and block[3]):
                    staged.append((block[0], round(ftp * block[1] / 100) if ftp else None,
                                   block[2], *block[3:]))
                    continue
                staged.append((block[0], value, block[2], *block[3:]))
                changed = True
                out.setdefault("ga_blocks", []).append(
                    {"label": block[2], "watts": value, "target": at.get("target"),
                     "limit": at["limit"], "hour": at["hour"], "n": at["n"],
                     "load_w": at["load_w"], "alpha": at["alpha"], "mid": ga.get("mid"),
                     "target_alpha": ga.get("target_alpha"), "limit_alpha": ga.get("limit_alpha"),
                     "unverified": unverified})
            if changed:
                out["blocks_w"] = staged
                out["text_w"] = watts_text(staged) or out.get("text_w")
                out["watt_source"] = "ga"
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
            work = _is_work_block(block) if want == "ramp_hrvt2" else is_elastic(block)   # 0.70.0, C7
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
    ("sweetspot", "SweetSpot", ["sweetspot_2x20", "threshold_4x16"]),
    ("threshold", "Schwelle", ["threshold_4x10", "threshold_3x12", "threshold_5x6", "threshold_3x15"]),
    ("vo2max", "VO2max", ["vo2_4x4", "vo2_5x4", "vo2_3030", "vo2_3015", "vo2_4x8"]),
    ("return", "Wiedereinstieg", ["return_45"]),
    # Eigene Familie, keine Spielart der langen Fahrt (K1): eine MESSUNG ist
    # eine andere Art von Einheit als ein Training, und unter den langen
    # Fahrten saehe sie aus wie eine haertere Variante davon.
    ("ramp_test", "Stufentest", ["ramp_test"]),
]

# 0.73.0 (Skizze §4): DIE GRUPPE EINER EINHEIT - eine Tabelle, neben FAMILIES.
# Drei Gruppen, dieselben wie die drei Familien im Trainer-Reiter
# (TRAINER_FAMILIES im Panel; test_workouts haelt beide gleich). Der Stufentest
# ist eine Messung und gehoert zu keiner Gruppe. Gelesen von
# analytics.activity_family - fuer Marken (Familie) wie fuer den Plan (Schluessel).
FAMILY_GROUP: dict[str, str] = {
    "endurance": "grundlage", "long": "grundlage", "recovery": "grundlage", "return": "grundlage",
    "sweetspot": "schwelle", "tempo": "schwelle", "threshold": "schwelle",
    "vo2max": "vo2max",
}
KEY_GROUP: dict[str, str] = {
    key: FAMILY_GROUP[family]
    for family, _label, keys in FAMILIES if family in FAMILY_GROUP
    for key in keys
}
GROUP_LABEL: dict[str, str] = {
    "grundlage": "Grundlage", "schwelle": "SweetSpot & Schwelle", "vo2max": "VO2max",
}
# Traegt eine Fahrt mehrere Gruppen, gibt die haerteste die Farbe - SETZUNG E3
# (Vorarbeiter 26.09.), kein Befund.
GROUP_ORDER: tuple[str, ...] = ("vo2max", "schwelle", "grundlage")

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
    # 0.72.2 (Entscheidung Johannes 26.09.): das Wort traegt NUR den Zustand und
    # wird nie ersetzt; "{tag}" setzt das Panel an EINER Stelle ein (heute/morgen).
    # Die Menge ueber der Obergrenze ist ein eigenes Zeichen (`quantity`).
    "green": {
        "label": "grün",
        "word": "passt {tag}",
        # 0.70.0 (C4): auf L1 - der Zustand traegt die Art, die Obergrenze die Menge.
        "detail": "Der Zustand trägt diese Art. Liegt die Last über der Obergrenze, bleibt "
                  "die Art und die Menge wird gekürzt.",
    },
    "yellow": {
        "label": "gelb",
        "word": "geht, kostet mehr",
        "detail": "Der Zustand trägt nur bedingt. Die Einheit ist möglich, sie kostet heute "
                  "mehr als sonst.",
    },
    "stimulus": {
        "label": "Reiz",
        "word": "gewollter Überreiz",
        "detail": "Über der Obergrenze, aber der Zustand trägt und die letzten Tage boten "
                  "Erholung. Das ist funktionelles Überreichen: ein kurzer gewollter "
                  "Einbruch, der nach Erholung in Superkompensation mündet.",
    },
    "red": {
        "label": "rot",
        "word": "{tag} nicht",
        "detail": "Der Zustand spricht dagegen. Nur ohne Zustand (keine HRV-Basislinie) "
                  "entscheidet die Last.",
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
        # 0.73.2 (T2): gezaehlt wird rollierend im Fenster des bewerteten Tags,
        # nicht in der Kalenderwoche.
        reason = ("Zwei harte Tage liegen schon in den sechs Tagen davor. Zwei in sieben Tagen "
                  "sind der Standard; ein dritter ist die Ausnahme, nicht die Regel.")
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


# L1 (0.69.0, Entscheidung 25.09.): DER ZUSTAND ENTSCHEIDET DIE ART, DIE LAST
# IST EIN GELAENDER AN DER MENGE. Bis 0.68.0 sperrte ein ueberschrittenes
# Budget die Einheit ("Das Lastbudget verbietet es heute") - am Livebestand an
# 5 von 30 Tagen einen bereiten Tag, waehrend an 13 Tagen das Budget "hart
# passt" sagte und der Zustand nicht. Jetzt: die Stufe kommt aus `fit`
# (Zustand); ueber der Obergrenze traegt sie `over_ceiling`, und `guard()`
# sagt, wie lang die Fahrt passen wuerde. Rot kommt nur noch aus dem Zustand -
# AUSSER es gibt keinen Zustand (Athlet ohne HRV-Basislinie, state "unknown"):
# dann entscheidet die Last, und die Karte sagt das (`by_load`).
GUARD_WORDS = {
    "over": "Geländer: Last {load} über der Obergrenze {ceiling} — die Art bleibt, die Menge nicht.",
    "fit": " Bis ~{hours} h passt sie unter die Obergrenze.",
    "fixed": " Die Einheit ist nicht kürzbar — heute als Ganzes über der Grenze.",
    # 0.69.2 (F2): eine ELASTISCHE Einheit, die auch gekuerzt (unter 0,5 h) nicht
    # mehr unter die Grenze passt, ist nicht "fest" - sie sagt, dass sie nirgends
    # hinpasst. Bis 0.69.1 stand an der Grundlage "nicht kuerzbar" (Grenze 0).
    "too_short": " Auch gekürzt passt sie nicht unter die Grenze — unter 0,5 h bleibt keine sinnvolle Fassung.",
    "by_load": "Ohne Zustand (keine HRV-Basislinie) entscheidet die Last: über der Obergrenze — heute nicht.",
    "green_over": "Zustand unauffällig — die Last liegt über der Obergrenze: Art bleibt, Menge kürzen.",
    "yellow_over": "Der Zustand trägt nur bedingt, und die Last liegt über der Obergrenze: Art bleibt, Menge kürzen.",
    # 0.72.2: "over_word" (0.69.1) ist entfallen - es ERSETZTE das Stufenwort und
    # machte aus zwei Aussagen ein Etikett. green_over/yellow_over sind nur noch der
    # Satz am Mengen-Zeichen.
    "quantity": "Menge über Wochenlast",
}


def stage(fit: str, fits_budget: bool | None, recovery: bool = False,
          by_load: bool = False) -> dict[str, Any]:
    """The one rule that turns state + budget into one of four grades.

    Total over its inputs, and deliberately small: every caller - the session
    list for today, the current week of the plan - asks THIS function and
    prints what it gets back. A threshold in the frontend would be the second
    rule the package forbids.

    `fits_budget` may be None: below 28 days of history there is no budget at
    all. An unknown budget blocks nothing - and it cannot be exceeded either,
    so the stimulus grade needs a budget that actually exists.

    L1: the grade follows `fit` (the state); an exceeded budget only marks
    `over_ceiling`. With `by_load` (no state to speak of) the budget decides.
    """
    over_budget = fits_budget is False
    if fit == "no":
        key, blocked = "red", "state"
    elif over_budget and by_load:
        key, blocked = "red", "budget"
    elif over_budget and fit == "ok" and recovery:
        key, blocked = "stimulus", None
    elif fit == "maybe":
        key, blocked = "yellow", None
    else:
        key, blocked = "green", None

    out = {"key": key, "blocked_by": blocked, "over_ceiling": over_budget, **STAGES[key]}
    if blocked == "state":
        subject, verb = BLOCKED_BY["state"]
        out["detail"] = f"{subject} {verb} es heute."
    elif blocked == "budget":
        out["detail"] = GUARD_WORDS["by_load"]
    elif over_budget and key in ("green", "yellow"):
        # 0.72.2: das Wort und der Satz bleiben die der Stufe; die Menge steht
        # daneben als eigenes Zeichen. Nicht bei stimulus (die Stufe IST der
        # gewollte Ueberreiz), rot, ohne Budget, und nicht bei der Regeneration
        # (guard_exempt -> fits_budget ist dort nie False).
        out["quantity"] = {"label": GUARD_WORDS["quantity"], "text": GUARD_WORDS[f"{key}_over"]}
    if key == "stimulus":
        out["evidence"] = STIMULUS_EVIDENCE
    return out


# 0.70.0 (C8, Entscheidung Johannes 25.09.): eine ERHOLUNGSEINHEIT ist nie "ueber
# der Grenze". Bis 0.69.2 stand bei Obergrenze 0 auch die Regeneration (Last 18)
# im Gelaender - die Einheit, die gerade dann die richtige ist. Die Familie steht
# hier, EINE Stelle; guard(), suggest() und rate_sessions() fragen sie.
GUARD_EXEMPT_FAMILIES = ("recovery",)


def guard_exempt(entry: dict[str, Any]) -> bool:
    """Steht diese Einheit ausserhalb des Gelaenders (C8)?"""
    fam = entry.get("family") or FAMILY_OF_KEY.get(str(entry.get("key") or ""))
    return fam in GUARD_EXEMPT_FAMILIES


def guard(entry: dict[str, Any], load: float, ceiling: float | None,
          hours: float | None = None) -> dict[str, Any] | None:
    """Das Gelaender an der Menge (L1): Last gegen Obergrenze, und bis zu
    welcher Dauer eine ELASTISCHE Einheit darunter passen wuerde.

    Die Dauer folgt aus session_load (Last ~ Dauer bei gleicher Intensitaet):
    hours_fit = Dauer x Obergrenze / Last, auf Viertelstunden abgerundet. Eine
    Einheit ohne elastischen Abschnitt hat keine kuerzere Fassung - sie sagt
    das, statt eine zu erfinden.
    """
    if ceiling is None:
        return None
    exempt = guard_exempt(entry)
    over = float(load) > float(ceiling) and not exempt
    out: dict[str, Any] = {"over": over, "load": round(load), "ceiling": round(ceiling), "hours_fit": None}
    if exempt:
        out["exempt"] = True
    if not over:
        return out
    text = GUARD_WORDS["over"].format(load=round(load), ceiling=round(ceiling))
    elastic = any(is_elastic(block) for block in (entry.get("blocks") or []))
    # 0.69.2 (F2): "nicht kuerzbar" heisst FEST - Arbeitsbloecke (Intervalle) oder
    # der Stufentest. Ein gleichmaessiger Abschnitt ohne elastische Marke (die
    # Regeneration) ist nicht fest, er traegt nur keine gerechnete Dauer.
    fixed = entry.get("key") == "ramp_test" or any(_is_work_block(block) for block in (entry.get("blocks") or []))
    minutes = float(entry.get("minutes") or 0)
    planned_h = float(hours) if hours else (minutes / 60.0 if minutes else 0.0)
    if elastic and planned_h > 0 and load > 0:
        fit_h = int((planned_h * float(ceiling) / float(load)) * 4) / 4.0
        if fit_h >= 0.5:
            out["hours_fit"] = fit_h
            text += GUARD_WORDS["fit"].format(hours=("%.1f" % fit_h).replace(".", ","))
        else:
            text += GUARD_WORDS["too_short"]
    elif fixed:
        text += GUARD_WORDS["fixed"]
    else:
        text += GUARD_WORDS["too_short"]
    out["text"] = text
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
            ramp: dict[str, Any] | None = None,
            steering: dict[str, Any] | None = None,
            ga: dict[str, Any] | None = None) -> list[dict[str, Any]]:
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

        # EINE Stelle, die eine Einheit fuer heute bewertet - fuer die gewaehlte
        # Variante UND (0.72.0, Skizze 1) fuer jede weitere der Familie. Das Panel
        # zeigt sie alle als Karten; es rechnet kein Urteil selbst.
        def judge(k: str) -> dict[str, Any]:
            one = dict(scaled(BY_KEY[k], ftp, aerobic_hr, max_hr, curve, blocks, ramp,
                              steering, ga))
            verdict, reason = fit_for(
                family_key, state, one["intensity"],
                hard_days_last_7=hard_days_last_7, layoff_days=layoff_days,
                infection=infection,
            )
            fits_budget = None if budget is None else (one["load"] <= budget or guard_exempt(BY_KEY[k]))
            one.update({
                "family": family_key, "family_label": family_label,
                "fit": verdict, "fit_reason": reason,
                "fits_budget": fits_budget,
                # the grade the panel prints - decided HERE, never in the frontend
                "stage": stage(verdict, fits_budget, recovery_offered, by_load=(state == "unknown")),
                "guard": guard(BY_KEY[k], one["load"], budget),
            })
            return one

        entry = judge(key)
        entry["alternatives"] = [{"key": k, "title": BY_KEY[k]["title"], "load": BY_KEY[k]["load"]}
                                 for k in keys if k != key]
        entry["variants"] = [judge(k) for k in keys if k != key]
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
                  ramp: dict[str, Any] | None = None,
                  steering: dict[str, Any] | None = None,
                  ga: dict[str, Any] | None = None) -> list[dict[str, Any]]:
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
        full = scaled(template, ftp, aerobic_hr, max_hr, curve, blocks, ramp, steering, ga)
        # KEINE ZWEITE WATTFASSUNG (0.67.2, F3.3 / S4): bis 0.67.1 stand hier
        # `steps_text(stretched, ftp)` - FTP x Prozent - ueber der Wattliste,
        # die scaled() aus Kurve/Bloecken/Steuerung gebaut hatte; die Karte trug
        # dann 130 W in der Liste und 134 W im Kalendertext. scaled() hat
        # text_w schon richtig gesetzt (die gestreckte Vorlage ging hinein).
        load = session_load(entry, session.get("hours"))
        verdict, reason = fit_for(
            family, state, entry.get("intensity") or 0,
            hard_days_last_7=hard_days_last_7, layoff_days=layoff_days,
            infection=infection,
        )
        fits_budget = None if budget is None else (load <= budget or guard_exempt(entry))
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
            # WOHER DIE WATT KOMMEN reist mit (0.67.2, F3.2) - dieselben Felder
            # wie die Trainer-Karte, damit die Wochenkarte ihre Herkunft nennen
            # kann statt so auszusehen, als staende sie auf der FTP.
            **{key: full.get(key) for key in ("watt_source", "steering_source", "block_source",
                                              "curve_blocks", "curve_share", "ga_blocks", "ga_missing", "ramp_source", "hr_source")
               if full.get(key) is not None},
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
            "stage": stage(verdict, fits_budget, recovery_offered, by_load=(state == "unknown")),
            "guard": guard(entry, load, budget, session.get("hours")),
            "purpose": entry.get("purpose"),
            "effect": entry.get("effect"),
        })
        out.append(rated)
    return out


DEFAULT_NOTE = "Vorgeschlagen von Home Assistant"
# 0.73.0: das Praefix der external_id, an dem analytics.activity_family ein
# eigenes Event erkennt ("ha-intervals-icu:{key}:{date}"). Seit 0.73.4 (E4)
# setzt to_event die Kennung auch; _planned_key liest den Schluessel bis zum
# ersten Doppelpunkt, das Datum stoert dort nicht.
EXTERNAL_ID_PREFIX = "ha-intervals-icu:"


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
    payload = {
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
    # E4 (0.73.4): eine feste Kennung, damit die gefahrene Einheit ihrer
    # Familie zugeordnet bleibt, auch wenn der Titel umbenannt wird. Ohne
    # Schluessel keine halbe Kennung. Kein upsert: gleiche Kennung ergibt in
    # intervals.icu ein zweites Event, geschrieben wird nur auf Klick.
    if entry.get("key"):
        payload["external_id"] = f"{EXTERNAL_ID_PREFIX}{entry['key']}:{day}"
    return payload


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


# --- B2c · DIE KACHEL-ERKLAERUNG ------------------------------------------------
# Der Kreislauf, in dem jede Vorgabe steht, in einfacher Sprache - und wo DIESE
# Einheit darin steht. Die Saetze reisen aus dem Modul (fuenfte Bauregel): das
# Panel ordnet sie nur an. Drei Stufen, weil es drei Arten gibt, zu einer Zahl
# zu kommen: eine Eintragung, eine Messung ueber erkannte Einheiten, eine
# Messung ueber das, was der Athlet selbst zugeordnet hat.
CYCLE = (
    ("ftp", "Die FTP bringt dich in Gang.",
     "Solange für eine Familie nichts gemessen ist, rechnen ihre Einheiten in Prozent "
     "deiner FTP. Die FTP ist eine Eintragung in Intervals, keine Messung."),
    ("alpha", "Dein alpha korrigiert unterwegs.",
     "Jede gemessene Einheit zeigt über den alpha-Wert, bei welcher Leistung du "
     "wirklich an der Schwelle warst. Daraus rechnen die Vorgaben — zunächst über die "
     "Einheiten, die das System an ihrem Namen erkennt."),
    ("marks", "Deine Markierung übernimmt.",
     "Sobald du umgestellt hast, kommen die Watt nur noch aus dem, was du selbst "
     "zugeordnet und gemessen hast. Was du nicht markierst, zählt nicht."),
)


def explain(entry: dict[str, Any], ftp: float | None, curve: dict[str, Any] | None,
            blocks: dict[str, Any] | None,
            ramp: dict[str, Any] | None) -> dict[str, Any] | None:
    """Zahl, Herkunft, Kreislauf, gewertete Einheiten und Rechenweg EINER Einheit.

    Aus der schon gerechneten Einheit (`scaled`) und den Reihen, aus denen sie
    rechnete - keine zweite Rechnung, nur ihr Nachweis. Der Stufentest hat seine
    eigene Herleitung (`derivation`) und bekommt keine zweite.
    """
    if entry.get("ramp_protocol") or not entry.get("blocks_w"):
        return None
    src = entry.get("watt_source")
    # Dieselbe Familienbestimmung wie `scaled`: das Feld `family` setzt erst
    # `suggest`, und ohne Rueckfall laese der Nachweis eine leere Reihe.
    fam = entry.get("family") or _family_of(entry.get("key"))
    window = entry.get("hr_window") or None
    units: list[dict[str, Any]] = []
    steps: list[str] = []
    units_note = ""
    if src == "blocks":
        box = ((blocks or {}).get("families") or {}).get(fam) or {}
        sel = (blocks or {}).get("selection") or {}
        stage = "marks" if sel.get("from_marks") else "alpha"
        bs = entry.get("block_source") or {}
        watts = bs.get("watts")
        origin = f"aus deiner Blockmessung, {sel.get('label') or ''}".rstrip(", ")
        units = [{"activity_id": p.get("activity_id"), "date": p.get("date"),
                  "name": p.get("name"),
                  "detail": f"{p.get('median_watts')} W bei alpha {p.get('median_alpha')}"}
                 for p in reversed(box.get("points") or [])]
        units_count = box.get("sessions") or len(units)
        steps.append(f"Vorgabe {watts} W = Median der Blockleistung in der letzten Einheit "
                     f"({bs.get('date')}, {bs.get('n_blocks')} Blöcke, alpha {bs.get('alpha')}).")
        hs = entry.get("hr_source") or {}
        if hs.get("n"):
            steps.append(f"Pulsfenster {hs.get('low')}–{hs.get('high')} bpm = Median der "
                         f"Einheitspulse {hs.get('median')} bpm ± {BLOCK_HR_WINDOW_SD_FACTOR:g} × "
                         f"Streuung {hs.get('sd')} bpm über {hs.get('n')} Einheiten.")
    elif src == "steering":
        # 0.69.2 (F1): DIE VORGABE ALS QUELLE. Bis 0.69.1 kannte der Nachweis
        # diesen Zweig nicht und fiel in den FTP-Zweig darunter - die Karte trug
        # die Vorgabe (190 W) mit dem Etikett "Rueckfall auf die FTP - nicht
        # gemessen" und zaehlte 0 Einheiten, waehrend die Kachel 190 W aus 6
        # Einheiten sagte (Livebestand 25.09.). Dieselben Reihen wie die Kachel.
        ss = entry.get("steering_source") or {}
        box = ((blocks or {}).get("families") or {}).get(fam) or {}
        sel = (blocks or {}).get("selection") or {}
        stage = "marks" if sel.get("from_marks") else "alpha"
        watts = ss.get("watts")
        origin = (f"deine Vorgabe — Startwert {ss.get('anchor_w')} W vom {ss.get('anchor_date')} "
                  f"plus {ss.get('moves') or 0} gerechnete Schritte"
                  + (f", {sel.get('label')}" if sel.get("label") else ""))
        units = [{"activity_id": p.get("activity_id"), "date": p.get("date"),
                  "name": p.get("name"),
                  "detail": f"{p.get('median_watts')} W bei alpha {p.get('median_alpha')}"}
                 for p in reversed(box.get("points") or [])]
        units_count = ss.get("n_units") if ss.get("n_units") is not None else (box.get("sessions") or len(units))
        steps.append(f"Vorgabe {watts} W = Startwert {ss.get('anchor_w')} W ({ss.get('anchor_date')}) "
                     f"{'+' if (ss.get('moves') or 0) else '±'} {ss.get('moves') or 0} Schritte × {STEERING_STEP_W} W "
                     f"(ein Schritt, wenn genug Einheiten auf derselben Seite des alpha-Korridors liegen).")
        band = ss.get("band") or {}
        if band.get("low") is not None and band.get("high") is not None:
            steps.append(f"Toleranz {band.get('low')}–{band.get('high')} W aus den letzten "
                         f"{band.get('n')} Einheiten (t-Band, zentriert auf die Vorgabe).")
        hb = ss.get("hr_band") or {}
        if hb.get("low") is not None and hb.get("high") is not None:
            steps.append(f"Pulsfenster {hb.get('low')}–{hb.get('high')} bpm aus denselben Einheiten.")
        if ss.get("note_blocks"):
            steps.append(str(ss["note_blocks"]))
    elif src == "ga":
        stage = "marks"
        rows = entry.get("ga_blocks") or []
        g = rows[0] if rows else {}
        watts = g.get("watts")
        origin = "aus der Ermüdungskachel: Ziel und Grenze für diese Dauer (Setzung, Umrechnung aus deinem Stufentest)"
        units = []
        units_count = g.get("n")
        for r in rows:
            a_t = r.get("target_alpha")
            steps.append(
                f"{r.get('label')}: Stunde {r.get('hour')} ({r.get('n')} Fahrten) — gehaltene Last "
                f"{r.get('load_w')} W bei alpha {r.get('alpha')}; Grenze {r.get('limit')} W = Last + "
                f"(alpha − {r.get('limit_alpha')}) × {r.get('mid')} W/alpha"
                + (f"; Ziel {r.get('target')} W = Last + (alpha − {a_t}) × {r.get('mid')} W/alpha." if a_t is not None
                   else "; kein Ziel eingetragen — die Einheit trägt die Grenze.")
                + (" Ab 3 h ungeprüft — Abnahmefahrt offen." if r.get("unverified") else ""))
    elif src == "curve":
        sel = (curve or {}).get("selection") or {}
        stage = "marks" if sel.get("from_marks") else "alpha"
        rows = entry.get("curve_blocks") or []
        watts = rows[0].get("watts") if rows else None
        origin = f"aus deiner Ermüdungskurve, {sel.get('label') or ''}".rstrip(", ")
        units = [{"activity_id": r.get("activity_id"), "date": r.get("date"), "name": r.get("name"),
                  "detail": "Stunden mit Wert: " + ", ".join(str(h) for h in (r.get("hours_with_value") or []))}
                 for r in reversed((curve or {}).get("used") or [])]
        units_count = (curve or {}).get("rides_used") if curve else len(units)
        for r in rows:
            steps.append(f"{r.get('label')}: Schwelle für eine Fahrt von {r.get('hour')} h "
                         f"{r.get('threshold')} W aus {r.get('n')} Fahrten × Anteil "
                         f"{r.get('share')} = {r.get('watts')} W.")
    elif src in ("ramp_hrvt1", "ramp_hrvt2"):
        stage = "marks"
        rs = entry.get("ramp_source") or {}
        watts = round((rs.get("watts") or 0) * (rs.get("share") or 0)) if rs.get("watts") else None
        origin = "aus deinem markierten Stufentest"
        units = [{"activity_id": (ramp or {}).get("activity_id"), "date": rs.get("date"),
                  "name": "Stufentest", "detail": f"{rs.get('watts')} W bei alpha {rs.get('alpha')}"}]
        units_count = 1
        steps.append(f"Vorgabe {watts} W = {rs.get('watts')} W an der Schwelle × Anteil {rs.get('share')}.")
    else:
        stage = "ftp"
        work = [w for t, w in zip(entry.get("blocks") or [], entry.get("blocks_w") or [])
                if t[1] == max(b[1] for b in entry.get("blocks") or [(0, 0)])]
        watts = work[0][1] if work else None
        ss = entry.get("steering_source") or {}
        if ss.get("watts"):
            # 0.69.2 (F1): es GIBT eine Vorgabe - sie gilt fuer Arbeitsbloecke
            # (jede Blockzahl, 0.70.0), und diese Form (Saetze eines 30/30, 30/15) bekommt sie
            # nicht (Entscheidung 0.61.0, "Etiketten ehrlich"). Die Karte sagt
            # das, statt "nicht gemessen" - die Kachel daneben sagt ja das
            # Gegenteil.
            origin = (f"Rückfall auf die FTP — deine Vorgabe ({ss['watts']} W aus "
                      f"{ss.get('n_units') or 0} Einheiten) gilt für Arbeitsblöcke (Block 1, 2, 3 …); "
                      f"diese Form bekommt sie nicht")
            units_count = 0
            units_note = str(ss.get("note_blocks") or "")
        else:
            origin = "Rückfall auf die FTP — nicht gemessen"
            units_count = 0
            units_note = "Keine: die FTP ist eine Eintragung, und für diese Einheit trägt noch keine Messung."
        pct = max((b[1] for b in entry.get("blocks") or []), default=None)
        # Die FTP wird UEBERGEBEN, nicht aus gerundeten Watt zurueckgerechnet:
        # 108 W / 50 % ergaebe „FTP 216 W" bei einer FTP von 215.
        steps.append(f"Vorgabe {watts} W = FTP {ftp:g} W × {pct} % der Vorlage."
                     if ftp else f"Vorgabe {watts} W aus {pct} % der Vorlage.")
    return {
        "headline": {"watts": watts,
                     "hr_low": window[0] if window else None,
                     "hr_high": window[1] if window else None},
        "origin": origin,
        "stage": stage,
        "cycle": [{"key": k, "title": t, "text": x, "here": k == stage} for k, t, x in CYCLE],
        "units": units,
        "units_count": units_count,
        "units_note": units_note,
        "steps": steps,
    }
