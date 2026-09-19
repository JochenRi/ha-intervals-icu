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

# --- Die Maskierung (docs/ausbau.md P4) ---------------------------------------
# MASKIEREN, NICHT ZUSAMMENSCHIEBEN. Die Fixture ist genau darauf gebaut: zwei
# Stunden, und die markierten Teile liegen so, dass ein Zusammenschieben ein
# ANDERES Ergebnis liefert als eine Maskierung. Waere die Fahrt gleichfoermig,
# bestuende der falsche Weg jede Pruefung (Lehre 2 aus Paket A).
#
# Der Zusammenhang ist in beiden Abschnitten exakt linear, damit die Ablesung
# eine PINNBARE Zahl ist und keine Naeherung:
#   Grundlage  Watt = 300 - 200*alpha  ->  bei 0,75:  150 W
#   Tempo      Watt = 400 - 200*alpha  ->  bei 0,75:  250 W
# Die acht alpha-Werte teilen 1800 glatt, also traegt jeder Kuebel beide
# Abschnitte im selben Verhaeltnis - die Mischung liegt damit ebenfalls exakt
# auf einer Geraden (350 - 200*alpha -> 200 W).
ALPHAS = [0.60, 0.64, 0.68, 0.72, 0.76, 0.80, 0.84, 0.88]


def _h(rows, index):
    """Eine Stundenzeile, oder ein leeres Dict.

    NICHT `rows[index]`: die schaerfste Mutation hier ist das
    ZUSAMMENSCHIEBEN, und die laesst die Liste KUERZER werden. Mit einem
    Indexzugriff stuerzt der Lauf an dieser Stelle ab, ueberspringt alles
    Folgende und meldet am Ende "0 Fehler" - die Mutation kaeme durch
    (§9, erste Bauregel).
    """
    return rows[index] if isinstance(rows, list) and len(rows) > index else {}


def _leg(n, offset):
    a = [ALPHAS[i % len(ALPHAS)] for i in range(n)]
    return a, [offset - 200 * v for v in a]


_ta, _tw = _leg(1800, 400)          # Stunde 1, erste Haelfte: Tempo
_ba, _bw = _leg(1800, 300)          # Stunde 1, zweite Haelfte: Grundlage
_ha, _hw = _leg(3600, 300)          # Stunde 2: Grundlage
RIDE_A = _ta + _ba + _ha
RIDE_W = _tw + _bw + _hw
MARKED = [(1800, 7200)]             # nur die Grundlagenteile sind angehakt

ganz = derive.dfa_hours(RIDE_A, RIDE_W)
mask = derive.dfa_hours(RIDE_A, RIDE_W, keep=MARKED)

check("Maske: die Achse bleibt die Fahrtzeit, zwei Stunden", len(mask), len(ganz))
check("Maske: unmaskiert liest Stunde 1 die MISCHUNG", _h(ganz, 0).get("p075"), 200.0)
check("Maske: maskiert liest Stunde 1 nur die Grundlage", _h(mask, 0).get("p075"), 150.0)
check("Maske: Stunde 2 war ohnehin ganz markiert und bleibt gleich",
      _h(mask, 1).get("p075"), _h(ganz, 1).get("p075"))
check("Maske: die ausgeschlossene Haelfte steht in excluded", _h(mask, 0).get("excluded"), 1800)
check("Maske: und NICHT in dropped", _h(mask, 0).get("dropped"), _h(ganz, 0).get("dropped"))
check("Maske: die zugelassenen Punkte sind genau die markierten",
      _h(mask, 0).get("points"), 1800)

# KEIN ZUSAMMENSCHIEBEN: nur Stunde 2 markiert. Wer die markierten Stellen
# aneinanderreiht, liest sie als "Stunde 1" - dann steht der Wert in Zeile 0.
# Er gehoert in Zeile 1, weil die erste Stunde stattgefunden hat und muede
# gemacht hat.
spaet = derive.dfa_hours(RIDE_A, RIDE_W, keep=[(3600, 7200)])
check("Kein Zusammenschieben: Stunde 1 traegt keinen Wert", _h(spaet, 0).get("p075"), None)
check("Kein Zusammenschieben: der Wert steht in Stunde 2", _h(spaet, 1).get("p075"), 150.0)
check("Kein Zusammenschieben: Stunde 1 bleibt in der Liste stehen",
      (len(spaet), _h(spaet, 0).get("hour"), _h(spaet, 1).get("hour")), (2, 1, 2))
check("Kein Zusammenschieben: die leere Stunde sagt, dass sie ausgeschlossen war",
      _h(spaet, 0).get("excluded"), 3600)

# Eine leere Stunde hat NICHTS verloren - sie hatte nichts. 0,0 % waere die
# Beschriftung perfekter Daten.
check("Leeres Fenster: dropped_share ist nichts, nicht null",
      _h(spaet, 0).get("dropped_share"), None)
check("Gegenprobe: bei zugelassenen Punkten ist es eine Zahl",
      isinstance(_h(spaet, 1).get("dropped_share"), float), True)

# Ausgeschlossene Artefakte duerfen den Nenner nicht fuellen: `dropped_share`
# sagt, was die MESSUNG verloren hat, nicht was der Athlet weggelassen hat.
KAPUTT = [None, None] + [0.7] * 8
kw = [150.0] * 10
check("Ausschluss vor Gueltigkeit: kaputte Stellen ausserhalb zaehlen nicht als dropped",
      (_h(derive.dfa_hours(KAPUTT, kw, keep=[(5, 10)]), 0).get("dropped"),
       _h(derive.dfa_hours(KAPUTT, kw, keep=[(5, 10)]), 0).get("excluded")), (0, 5))
check("Gegenprobe ohne Maske: dieselben Stellen zaehlen sehr wohl als dropped",
      _h(derive.dfa_hours(KAPUTT, kw), 0).get("dropped"), 2)

# keep=None und keep=[] sind NICHT dasselbe, und die Verwechslung waere still.
check("keep=[] schliesst alles aus, statt alles zuzulassen",
      [(row.get("points"), row.get("excluded")) for row in
       derive.dfa_hours(RIDE_A, RIDE_W, keep=[])], [(0, 3600), (0, 3600)])
check("Eine Maske ueber die ganze Fahrt aendert nichts",
      derive.dfa_hours(RIDE_A, RIDE_W, keep=[(0, 7200)]), ganz)
check("Ueberhaengende Grenzen werden geklemmt, nicht gemeldet",
      derive.dfa_hours(RIDE_A, RIDE_W, keep=[(-50, 999999)]), ganz)
check("Unbrauchbare Bereichsangaben fallen weg, ohne den Lauf zu werfen",
      _h(derive.dfa_hours(RIDE_A, RIDE_W, keep=[("x", 5), (1800, 7200), None]), 0).get("p075"),
      150.0)

# KEIN ALGORITHMUS-BUMP: der Importweg ruft ohne `keep`, und was er schreibt,
# muss Wert fuer Wert dasselbe sein wie vor der Maskierung. Das Feld
# `excluded` kommt additiv dazu - die Zeilenform wird deshalb festgehalten,
# damit ein versehentlich umbenanntes oder zusaetzliches Feld auffaellt.
check("Kein Bump: die Zeilenform des Importwegs, Feld fuer Feld",
      sorted(_h(ganz, 0).keys()),
      sorted(["hour", "points", "dropped", "excluded", "dropped_share",
              "dynamic_share", "bins", "p075", "alpha_min", "alpha_max",
              "p050", "low_points", "low_dropped", "low_dropped_share",
              "hr075", "slope", "r2",
              # ADDITIV (Ermuedungsrechnung v2): die Ablesestelle an der
              # eigenen gehaltenen Last. Sie steht IMMER da - auch mit
              # ausgeschaltetem Paarungsfenster, weil sie nichts an den
              # bestehenden Werten aendert und der Schalter vor dem
              # Versionszaehler steht.
              "load_w", "load_n", "load_alpha"]))
check("Kein Bump: excluded ist ohne Maske null und steht trotzdem da",
      (_h(ganz, 0).get("excluded"), _h(ganz, 1).get("excluded")), (0, 0))


# ---------------------------------------------------------------------------
# ERMUEDUNGSRECHNUNG v2: die 120-s-Paarung und die Ablesestelle.
# Der Schalter steht VOR dem Versionszaehler: `watt_window_s=0` (Vorgabe) muss
# Wert fuer Wert dasselbe liefern wie vor dem Einbau.
_v2_aus = derive.dfa_hours(RIDE_A, RIDE_W)
_v2_an = derive.dfa_hours(RIDE_A, RIDE_W, watt_window_s=derive.DFA_WATT_WINDOW_S)
check("v2: Schalter aus laesst jede bestehende Zahl unveraendert",
      [{k: v for k, v in row.items() if k not in ("load_w", "load_n", "load_alpha")}
       for row in _v2_aus],
      [{k: v for k, v in row.items() if k not in ("load_w", "load_n", "load_alpha")}
       for row in ganz])
check("v2: die Fensterbreite steht auf Andriolos 120 s",
      derive.DFA_WATT_WINDOW_S, 120)
check("v2: das Lastfenster ist eine gesetzte Groesse und steht bei +/- 5 W",
      derive.DFA_LOAD_BAND_W, 5.0)
check("v2: unter 20 Punkten im Lastfenster gibt es keinen Wert",
      derive.DFA_LOAD_MIN_POINTS, 20)
# Dass der Schalter wirkt, wird dort geprueft, wo der Mechanismus existiert:
# an einem Strom MIT Antritt. Auf einem glatten Strom darf er nichts tun - das
# ist die Gegenprobe und gehoert mitgeprueft, sonst misst der Test nur Rauschen.
_spitz_a = [1.30 - 0.0012 * i for i in range(600)]
_spitz_w = [260.0 if 250 <= i < 350 else 120.0 for i in range(600)]
_sp_aus = derive.dfa_hours(_spitz_a, _spitz_w, hour_secs=600)[0]
_sp_an = derive.dfa_hours(_spitz_a, _spitz_w, hour_secs=600, watt_window_s=120)[0]
check("v2: mit Antritt verschiebt die Paarung die Wattachse",
      _sp_an.get("p075") != _sp_aus.get("p075"), True)
_glatt_a = [0.70 + 0.002 * i for i in range(600)]
_glatt_w = [150.0] * 600
_gl_aus = derive.dfa_hours(_glatt_a, _glatt_w, hour_secs=600)[0]
_gl_an = derive.dfa_hours(_glatt_a, _glatt_w, hour_secs=600, watt_window_s=120)[0]
check("v2: GEGENPROBE - ohne Schwankung aendert die Paarung nichts",
      (_gl_an.get("p075"), _gl_an.get("slope")),
      (_gl_aus.get("p075"), _gl_aus.get("slope")))

# DAS MITTEL SELBST, an einer Hand voll Zahlen nachgerechnet.
check("v2: nachlaufendes Mittel ueber drei Stellen",
      derive.trailing_mean([3, 6, 9, 12], 3), [3.0, 4.5, 6.0, 9.0])
check("v2: Nullwerte zaehlen nicht in den Mittelwert",
      derive.trailing_mean([10, 0, 20], 3), [10.0, 10.0, 15.0])
check("v2: ohne Fenster bleibt die Rohachse stehen",
      derive.trailing_mean([10, 0, 20], 1), [10.0, 0.0, 20.0])
check("v2: ein leerer Strom liefert eine leere Achse",
      derive.trailing_mean([], 3), [])

# DIE VERWERFREGEL BLEIBT AM ROHWERT: eine reine Rollphase darf nicht als
# gefahren zaehlen, nur weil die Nachbarsekunden getreten haben.
# Rollphasen MITTEN im Tritt: dort ist der Rohwert 0, das 120-s-Mittel aber
# positiv. Genau hier trennt sich die Verwerfregel am Rohwert von der am
# Mittel - eine Rollsekunde darf nicht als gefahren zaehlen, nur weil die
# Nachbarsekunden getreten haben.
_roll_a = [0.8] * 600
_roll_w = [0.0 if i % 3 == 0 else 150.0 for i in range(600)]
_roll = derive.dfa_hours(_roll_a, _roll_w, hour_secs=600,
                         watt_window_s=derive.DFA_WATT_WINDOW_S)
check("v2: Rollphasen zaehlen weiter als verworfen, nicht als gefahren",
      _roll[0]["dropped"], 200)
check("v2: und sie stehen nicht in den Messpunkten",
      _roll[0]["points"], 400)

# RANDFAELLE: kein Strom, ein einziger Punkt, alles ausmaskiert.
check("v2: ohne alpha-Strom bleibt es bei einer leeren Liste",
      derive.dfa_hours(None, RIDE_W, watt_window_s=120), [])
check("v2: eine vollstaendig ausmaskierte Fahrt hat keine Ablesestelle",
      [row.get("load_alpha") for row in
       derive.dfa_hours(RIDE_A, RIDE_W, keep=[], watt_window_s=120)], [None, None])
check("v2: eine einzige Stelle liefert keinen Wert aus dem Lastfenster",
      derive.dfa_hours([0.9], [150.0], hour_secs=600,
                       watt_window_s=120)[0]["load_alpha"], None)


print()
print(f"test_dfa: {CHECKS} Prüfungen, {len(failures)} Fehler")
print("FEHLER:", failures if failures else "keine")
sys.exit(1 if failures else 0)
