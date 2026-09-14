"""Checks for the DFA alpha-1 summary."""

import random
import sys
from pathlib import Path

import coldcache  # noqa: F401  - MUSS vor jedem Bauteil-Import stehen (§9)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"))
import derive  # noqa: E402

failures = []
CHECKS = 0


def check(label, got, expected):
    global CHECKS
    CHECKS += 1
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {got!r}" + ("" if ok else f"  (erwartet {expected!r})"))
    if not ok:
        failures.append(label)


# known-answer test: 100 s aerobic, 200 s transition, 300 s anaerobic
dfa = [1.2] * 100 + [0.6] * 200 + [0.3] * 300
summary = derive.dfa_summary(dfa)
check("Sekunden aerob", summary["secs_aerobic"], 100)
check("Sekunden Uebergang", summary["secs_transition"], 200)
check("Sekunden anaerob", summary["secs_anaerobic"], 300)
check("Mittelwert", summary["mean"], round((1.2 * 100 + 0.6 * 200 + 0.3 * 300) / 600, 3))

# band edges belong to the transition, not to the neighbours
edges = derive.dfa_summary([0.75, 0.5, 0.7501, 0.4999])
check("0,75 zaehlt als Uebergang", edges["secs_transition"], 2)
check("knapp darueber zaehlt aerob", edges["secs_aerobic"], 1)
check("knapp darunter zaehlt anaerob", edges["secs_anaerobic"], 1)

# thinned stream: every 20th sample must still yield real durations
thinned = derive.dfa_summary([1.2] * 5 + [0.3] * 5, sample_secs=20)
check("ausgeduennter Stream skaliert", thinned["secs_aerobic"], 100)

# gaps, artefacts and text must not break anything
dirty = derive.dfa_summary([None, 1.0, "x", -3.0, 9.9, 0.4])
check("Luecken und Ausreisser verworfen", dirty["samples"], 2)

# threshold read-off: only samples between 0.70 and 0.80 count
dfa2 = [1.3, 0.78, 0.72, 0.30]
hr = [120, 150, 152, 175]
watts = [100, 190, 194, 260]
th = derive.dfa_summary(dfa2, hr, watts)
check("HF an der Schwelle", th["hr_at_threshold"], 151.0)
check("Watt an der Schwelle", th["power_at_threshold"], 192.0)
check("Stichproben Schwelle HF", th["hr_windows"], 2)
check("Stichproben Schwelle Watt", th["power_windows"], 2)

# --- die Belegungszahl gehoert zu IHREM Wert (PROJEKTSTAND §7, 0.45.0) --------
# Bis 0.44.0 stand hier EIN Feld: `len(hr_window) or len(watt_window)`. Faellt
# der Gurt aus, meldete es die WATT-Belegung als Belegung der Herzfrequenz.
gurt_aus = derive.dfa_summary([0.78, 0.72], [0, 0], [190, 194])
check("Gurt aus: keine HF abgelesen", gurt_aus["hr_at_threshold"], None)
check("Gurt aus: HF-Belegung ist null", gurt_aus["hr_windows"], 0)
check("Gurt aus: Watt-Belegung steht fuer sich", gurt_aus["power_windows"], 2)
# Die Gegenprobe zur alten Bauart, GEZAEHLT UND BENANNT: die alte Formel haette
# hier 2 geliefert - eine Zwei, die zu keinem Wert gehoerte.
check("Gegenprobe: die alte or-Formel haette gelogen",
      gurt_aus["hr_windows"] or gurt_aus["power_windows"], 2)
check("Gegenprobe: das getrennte Feld luegt nicht", gurt_aus["hr_windows"], 0)

# --- threshold_verdict: EINE Stelle fuer alle fuenf Leser ---------------------
from const import THRESHOLD_MIN_HR, THRESHOLD_MIN_POWER, THRESHOLD_MIN_WINDOWS  # noqa: E402

genug = THRESHOLD_MIN_WINDOWS
ausfall = derive.threshold_verdict(
    {"hr_at_threshold": 0.0, "power_at_threshold": 163.0,
     "hr_windows": 24, "power_windows": 24})
check("Ausfall 06.06.: HF unbrauchbar", ausfall["hr_usable"], False)
check("Ausfall 06.06.: als Ausfall benannt", ausfall["reason"], "hr_implausible")
check("Ausfall 06.06.: ist ein Ausfall, kein Mangel", ausfall["failure"], True)
check("Ausfall 06.06.: die Leistung bleibt brauchbar", ausfall["power_usable"], True)

knapp = derive.threshold_verdict(
    {"hr_at_threshold": 150.0, "hr_windows": genug - 1, "power_windows": 0})
check("ein Fenster zu wenig: kein Median", knapp["usable"], False)
check("ein Fenster zu wenig: benannt", knapp["reason"], "too_few_windows")
check("ein Fenster zu wenig: der Wert bleibt sichtbar", knapp["hr"], 150.0)
reicht = derive.threshold_verdict(
    {"hr_at_threshold": 150.0, "hr_windows": genug, "power_windows": 0})
check("genau an der Grenze: brauchbar", reicht["usable"], True)

# Die Grenze ist eine Konstante, kein Literal - ein Test, der 10 schreibt,
# besteht auch dann noch, wenn die Konstante auf 20 geht.
check("HF knapp unter der Mindestgrenze faellt",
      derive.threshold_verdict({"hr_at_threshold": THRESHOLD_MIN_HR - 0.1,
                                "hr_windows": 99})["hr_usable"], False)
check("HF genau auf der Mindestgrenze bleibt",
      derive.threshold_verdict({"hr_at_threshold": THRESHOLD_MIN_HR,
                                "hr_windows": 99})["hr_usable"], True)
check("Leistung unter der Mindestgrenze faellt",
      derive.threshold_verdict({"power_at_threshold": THRESHOLD_MIN_POWER - 0.1,
                                "power_windows": 99})["power_usable"], False)
check("gar keine Ablesung wird als solche benannt",
      derive.threshold_verdict({})["reason"], "no_reading")
check("kein Summary stuerzt nicht ab", derive.threshold_verdict(None)["usable"], False)

# warmup can be skipped
check("Aufwaermen uebersprungen",
      derive.dfa_summary([1.5] * 600 + [0.4] * 100, skip_secs=600)["secs_anaerobic"], 100)

# empty input stays empty instead of raising
check("leerer Stream", derive.dfa_summary([]), None)
check("nur Luecken", derive.dfa_summary([None, None]), None)

# stream list -> dict
check("Streams nach Name",
      sorted(derive.streams_to_dict([{"type": "dfa_a1", "data": [1]}, {"type": "watts", "data": [2]}])),
      ["dfa_a1", "watts"])

# realistic session: 1 h easy, 1 h transition, 1 h hard
random.seed(7)
real = ([round(random.uniform(0.9, 1.4), 4) for _ in range(3600)]
        + [round(random.uniform(0.5, 0.75), 4) for _ in range(3600)]
        + [round(random.uniform(0.15, 0.49), 4) for _ in range(3600)])
big = derive.dfa_summary(real)
check("Gesamtdauer erhalten",
      big["secs_aerobic"] + big["secs_transition"] + big["secs_anaerobic"], 10800)

# --- quirks found in real streams --------------------------------------------
# Intervals writes dfa_a1 = 0.0 before the algorithm has settled. Counting it
# as a measurement would inflate the anaerobic time of every session.
artefact = derive.dfa_summary([0.0, 0.0, 1.2, 0.3])
check("führende Nullen verworfen", artefact["samples"], 2)
check("Nullen zaehlen nicht als anaerob", artefact["secs_anaerobic"], 1)

# Coasting (0 W) must not count towards the threshold power.
coast = derive.dfa_summary([0.72, 0.74, 0.73], [150, 150, 150], [0, 200, 210])
check("Rollen (0 W) fliesst nicht ein", coast["power_at_threshold"], 205.0)
check("HF bleibt vollstaendig", coast["hr_at_threshold"], 150.0)

# --- dropped heart rate signal ------------------------------------------------
# Seen in the panel: one session plunged to a threshold HR near zero because
# the strap dropped out and wrote zeros into the stream.
drop = derive.dfa_summary([0.72, 0.73, 0.74], [0, 148, 152], [0, 200, 210])
check("Puls-Aussetzer fliesst nicht ein", drop["hr_at_threshold"], 150.0)
check("HF-Belegung zaehlt nur gueltige Werte", drop["hr_windows"], 2)

allzero = derive.dfa_summary([0.72, 0.73], [0, 0], None)
check("nur Aussetzer ergibt keinen Wert", allzero["hr_at_threshold"], None)
check("Baender bleiben trotzdem gezaehlt", allzero["secs_transition"], 2)

print()
print(f"test_dfa: {CHECKS} Prüfungen, {len(failures)} Fehler")
print("FEHLER:", failures if failures else "keine")
sys.exit(1 if failures else 0)
