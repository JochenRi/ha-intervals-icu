"""Simulation against recorded live payloads. Run: python3 tests/test_derive.py"""

import sys
from datetime import date, datetime
from pathlib import Path

import inspect  # noqa: E402
import coldcache  # noqa: F401  - MUSS vor jedem Bauteil-Import stehen (§9)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"))

import derive  # noqa: E402
from fixtures import ATHLETE, EVENTS, WELLNESS  # noqa: E402

failures = []
CHECKS = 0


def check(label, got, expected):
    global CHECKS
    CHECKS += 1
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {got!r}" + ("" if ok else f"  (erwartet {expected!r})"))
    if not ok:
        failures.append(label)


latest = derive.latest_values(WELLNESS)

# --- last known value per field, with its date -------------------------------
check("restingHR", latest["restingHR"], (50, "2026-09-10"))
check("hrv", latest["hrv"], (63.0, "2026-09-10"))
check("sleepSecs", latest["sleepSecs"], (26820, "2026-09-10"))
check("sleepScore", latest["sleepScore"], (84.0, "2026-09-10"))
check("steps", latest["steps"], (28, "2026-09-10"))
# VO2max only arrives on qualifying training days -> carried forward from 09-04
check("vo2max faellt auf letzten Trainingstag zurueck", latest["vo2max"], (49.0, "2026-09-04"))
check("ctl", latest["ctl"], (33.550095, "2026-09-10"))

# --- fields that never carry data must not become sensors --------------------
keys = derive.available_keys(WELLNESS)
check("spO2 nicht vorhanden", "spO2" in keys, False)
check("readiness nicht vorhanden", "readiness" in keys, False)
check("weight nicht vorhanden", "weight" in keys, False)
check("hrv vorhanden", "hrv" in keys, True)

# --- temp flags ---------------------------------------------------------------
check("tempRestingHR am 10.09.", derive.temp_flags(WELLNESS, "restingHR"), False)
check("temp flag fuer weight ohne Wert", derive.temp_flags(WELLNESS, "weight"), None)

# --- per sport estimates ------------------------------------------------------
info = derive.sport_info(WELLNESS)
check("eFTP Ride", round(info["Ride"]["eftp"], 1), 191.8)
check("Pmax Ride", round(info["Ride"]["pMax"]), 887)

# --- athlete sport settings ---------------------------------------------------
settings = derive.sport_settings(ATHLETE)
check("Reihenfolge Sportarten", [derive.sport_label(s) for s in settings],
      ["Ride", "Run", "Swim", "Other"])
check("FTP Ride", settings[0]["ftp"], 215)
check("FTP Run leer", settings[1]["ftp"], None)
check("maxHF Ride", settings[0]["max_hr"], 199)

# --- calendar ------------------------------------------------------------------
events = derive.planned_events(EVENTS)
check("Anzahl Termine", len(events), 4)
check("erster Termin ganztaegig", events[0]["all_day"], True)
check("Start als date", events[0]["start"], date(2026, 9, 4))
check("Ende exklusiv (Folgetag)", events[0]["end"], date(2026, 9, 5))
check("04.09. als absolviert erkannt", events[0]["completed"], True)
check("11.09. offen", events[1]["completed"], False)

nxt = derive.next_event(EVENTS, date(2026, 9, 10))
check("naechstes Workout", nxt["summary"], "SweetSpot Erhalt 1x20")
check("naechstes Workout Datum", nxt["start"], date(2026, 9, 11))
check("naechstes Workout Last", nxt["load"], 47)
# the 04.09. session is already done -> must not be offered as "next"
check("absolvierte Einheit uebersprungen", nxt["uid"], "134903156")

# --- best mean power over a moving-time axis (docs/ausbau.md J1/K1) -----------
# The measurement that anchors the whole protocol. J1 showed what goes wrong
# when a maximum is taken over more material than the value it is compared
# with, so every check here is about the WINDOW, not about the arithmetic.


def _ride(steps):
    """steps = [(step_seconds, watts, count), ...] -> a stream dict."""
    time_ch, watts_ch, t = [0], [0], 0
    for step, watts, count in steps:
        for _ in range(count):
            t += step
            time_ch.append(t)
            watts_ch.append(watts)
    return {"time": time_ch, "watts": watts_ch}


# 30 min at 150 W with a 5 min block at 300 W in the middle, 10 s samples
flat = _ride([(10, 150, 60), (10, 300, 30), (10, 150, 90)])
check("bestes 5-min-Mittel findet den 300-W-Block",
      round(derive.best_mean_watts(flat, 300)), 300)
check("bestes 20-min-Mittel mittelt den Block ein",
      round(derive.best_mean_watts(flat, 1200)), 188)
# A window longer than the ride has no value - NOT the value of a shorter one.
# This is J1 Befund 2 as a unit test: a maximum over less material is a
# different number, so an absent window must be absent.
check("Fenster laenger als die Fahrt gibt None",
      derive.best_mean_watts(flat, 3 * 3600), None)

# The same 300 W block, but split by a 20-minute stop. On a SAMPLE-counting
# axis both halves would join into one 5-minute window; on a moving-time axis
# the pause breaks the run and no 5-minute window exists.
paused = _ride([(10, 300, 15), (1200, 0, 1), (10, 300, 15)])
check("Pause ueber 60 s bricht das Fenster",
      derive.best_mean_watts(paused, 300), None)
check("die Haelften bleiben je fuer sich messbar",
      round(derive.best_mean_watts(paused, 150)), 300)

# Thinned streams carry uneven steps. The mean is weighted by the DURATION a
# sample stands for, not by the number of samples. Here two samples stand for
# 10 s each at 100 W and one stands for 40 s at 200 W:
#   duration-weighted (10*100 + 10*100 + 40*200) / 60 = 167
#   sample-counting   (100 + 100 + 200) / 3          = 133
# The two answers differ, which is what makes this a test rather than a
# restatement - on an evenly sampled ride both agree and nothing is proven.
uneven = {"time": [0, 10, 20, 60], "watts": [0, 100, 100, 200]}
check("Mittel ist dauergewichtet, nicht stichprobengewichtet",
      round(derive.best_mean_watts(uneven, 60)), 167)

check("ohne Leistungsstrom kein Wert", derive.best_mean_watts({"time": [0, 1]}, 60), None)
check("ohne Zeitachse kein Wert", derive.best_mean_watts({"watts": [1, 2]}, 60), None)
check("nicht-dict gibt None", derive.best_mean_watts(None, 60), None)

m = derive.test_measures(flat, 5, 20)
check("test_measures liefert p5", round(m["p5"]), 300)
check("test_measures liefert p20", round(m["p20"]), 188)
check("test_measures ohne Grund bei vollstaendiger Messung", m["reason"], None)

short = derive.test_measures(_ride([(10, 200, 30)]), 5, 20)
check("zu kurze Fahrt: kein p20", short["p20"], None)
# Fehlerklasse 4: was nicht passiert ist, muss dastehen.
check("zu kurze Fahrt nennt den Grund", "20-Minuten-Abschnitt" in (short["reason"] or ""), True)
nopow = derive.test_measures({"time": [0, 1, 2]}, 5, 20)
check("ohne Leistungsstrom nennt test_measures den Grund",
      "Leistungsstrom" in (nopow["reason"] or ""), True)

print()
# ---------------------------------------------------------------------------
# DIE PUNKTSCHWELLE ZAEHLT SEKUNDEN (0.64.2). Das ist keine Auslegung, sondern
# am Code belegbar: `dfa_hours` laeuft ueber die Stromstellen, sammelt je
# Stelle EINEN Wert, und `sample_secs` steht auf 1 - beide Aufrufer lassen die
# Vorgabe stehen. Eine volle Stunde hat also rund 3.600.
_takt = derive.dfa_hours.__defaults__
check("Schwelle: sample_secs steht auf einer Sekunde",
      inspect.signature(derive.dfa_hours).parameters["sample_secs"].default, 1)
check("Schwelle: eine Stunde sind 3.600 Stellen",
      inspect.signature(derive.dfa_hours).parameters["hour_secs"].default, 3600)
# EINE Stelle je Sekunde, nachgewiesen am Zaehler: ein Strom aus 3.600 gleichen
# Werten bei fester Last ergibt rund 3.600 Punkte im Lastfenster.
_konst = derive.dfa_hours([1.2] * 3600, [150.0] * 3600, [130] * 3600)
check("Schwelle: der Zaehler zaehlt Stellen, nicht Fenster",
      _konst[0]["load_n"], 3600)
# DIE SCHWELLE IST AUS DEM MESSWERT ABGELEITET, nicht gesetzt: sie ist die
# Fensterbreite von alpha. Darunter liegt keine vollstaendige Messung vor.
check("Schwelle: sie ist die Fensterbreite von alpha",
      derive.DFA_LOAD_MIN_POINTS, derive.DFA_WATT_WINDOW_S)
# GEGENPROBE, gezaehlt: knapp darunter gibt es KEINE Zahl, knapp darueber eine.
# Gebaut so, dass die gehaltene Last (der Median der Fahrt) auf 150 W liegt und
# GENAU `n` Stellen im Fenster darum liegen - der Rest weit darunter und
# darueber, zu gleichen Teilen.
def _last_mit(n):
    rest = 3600 - n
    return [100.0] * (rest // 2) + [150.0] * n + [200.0] * (rest - rest // 2)
_wenig = derive.dfa_hours([1.2] * 3600, _last_mit(derive.DFA_LOAD_MIN_POINTS - 1),
                          [130] * 3600)
check("Schwelle: knapp darunter gibt es keine Ablesestelle",
      (_wenig[0]["load_w"], _wenig[0]["load_n"], _wenig[0]["load_alpha"]),
      (150.0, derive.DFA_LOAD_MIN_POINTS - 1, None))
_genug = derive.dfa_hours([1.2] * 3600, _last_mit(derive.DFA_LOAD_MIN_POINTS),
                          [130] * 3600)
check("Schwelle Gegenprobe: knapp darueber gibt es eine",
      (_genug[0]["load_w"], _genug[0]["load_n"], _genug[0]["load_alpha"]),
      (150.0, derive.DFA_LOAD_MIN_POINTS, 1.2))


print(f"test_derive: {CHECKS} Prüfungen, {len(failures)} Fehler")
print("FEHLER:", failures if failures else "keine")
sys.exit(1 if failures else 0)
