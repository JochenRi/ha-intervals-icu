"""Checks for the training analytics, with known-answer tests where possible."""

import math
import sys
from datetime import date, timedelta
from pathlib import Path

COMP = Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"
import coldcache  # noqa: F401  - MUSS vor jedem Bauteil-Import stehen (§9)
sys.path.insert(0, str(COMP))
import analytics  # noqa: E402
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


# --- Friel form zones ----------------------------------------------------------
check("Form +25 = Uebergang", analytics.form_zone(25), "transition")
check("Form +15 = Frisch", analytics.form_zone(15), "fresh")
check("Form 0 = Grauzone", analytics.form_zone(0), "grey")
check("Form -15 = Optimal", analytics.form_zone(-15), "optimal")
check("Form -35 = Hohes Risiko", analytics.form_zone(-35), "high_risk")
check("Grenze -30 gehoert zu Hohes Risiko nicht mehr", analytics.form_zone(-30), "optimal")
check("Form ohne Wert", analytics.form_zone(None), None)
check("Form in Prozent der Fitness", analytics.form_percent(40, 30), 25.0)
check("Form Prozent ohne Fitness", analytics.form_percent(0, 10), None)

# --- daily load, gaps filled ----------------------------------------------------
data = {"wellness": {
    "2026-01-01": {"ctlLoad": 100.0, "hrv": 50},
    "2026-01-03": {"ctlLoad": 50.0, "hrv": 55},
}, "activities": {}, "dfa": {}}
loads = analytics.daily_load(data)
check("Luecke aufgefuellt", [point["load"] for point in loads], [100.0, 0.0, 50.0])

# --- Foster monotony ------------------------------------------------------------
# A week of seven identical days has no spread at all -> no monotony value
flat = {"wellness": {f"2026-01-{day:02d}": {"ctlLoad": 60.0} for day in range(5, 12)},
        "activities": {}, "dfa": {}}
week = analytics.weekly_summary(flat)[0]
check("Wochenlast", week["load"], 420.0)
check("sieben Trainingstage", week["days_trained"], 7)
check("keine Streuung, keine Monotonie", week["monotony"], None)

# 6 days at 60 plus one rest day: mean 51.4, sd 21.0 -> monotony 2.45
mixed = {"wellness": {**{f"2026-01-{day:02d}": {"ctlLoad": 60.0} for day in range(5, 11)},
                      "2026-01-11": {"ctlLoad": 0.0}}, "activities": {}, "dfa": {}}
week = analytics.weekly_summary(mixed)[0]
check("Monotonie mit einem Ruhetag", week["monotony"], 2.45)
check("Strain = Last x Monotonie", week["strain"], round(360.0 * 2.45, 0))

# --- ACWR ------------------------------------------------------------------------
steady = {"wellness": {}, "activities": {}, "dfa": {}}
start = date(2026, 1, 1)
for index in range(40):
    steady["wellness"][(start + timedelta(days=index)).isoformat()] = {"ctlLoad": 50.0}
_wr0 = getattr(analytics, "window_ratio", None)
_steady_last = (start + timedelta(days=39)).isoformat()
check("unter 28 Tagen im Bestand kein Verhaeltnis (load_budget None)",
      _wr0({"wellness": {k: v for k, v in list(steady["wellness"].items())[:20]}, "activities": {}, "dfa": {}},
           (start + timedelta(days=19)).isoformat()) if callable(_wr0) else "FEHLT", None)
check("gleichmaessige Last ergibt 1.0", _wr0(steady, _steady_last) if callable(_wr0) else "FEHLT", 1.0)

spike = dict(steady["wellness"])
for index in range(33, 40):
    spike[(start + timedelta(days=index)).isoformat()] = {"ctlLoad": 150.0}
_jump = _wr0({"wellness": spike, "activities": {}, "dfa": {}}, _steady_last) if callable(_wr0) else None
check("Belastungssprung hebt das Verhaeltnis ueber die Risikoschwelle",
      _jump is not None and _jump > analytics.ACWR_RISK, True)

# --- three zone collapse ----------------------------------------------------------
check("5-Zonen-Modell: 1-2 / 3 / 4-5",
      [round(value) for value in analytics._three_zone([600, 600, 300, 300, 200])], [60, 15, 25])
check("7-Zonen-Modell: 1-3 / 4 / 5-7",
      [round(value) for value in analytics._three_zone([300, 300, 300, 100, 50, 30, 20])], [82, 9, 9])
check("leere Zonen", analytics._three_zone([0, 0, 0]), None)
check("keine Zonen", analytics._three_zone(None), None)

# --- intensity distribution over real-ish activities --------------------------------
today = date.today()
acts = {}
for index in range(10):
    acts[f"a{index}"] = {
        "start_date_local": (today - timedelta(days=index)).isoformat() + "T09:00:00",
        "moving_time": 3600,
        "icu_hr_zone_times": [3000, 300, 200, 100, 0, 0, 0],
        "type": "Ride",
    }
dist = analytics.intensity_distribution({"wellness": {}, "activities": acts, "dfa": {}})
check("Verteilung ueber 10 Einheiten", dist["sessions"], 10)
check("Summe ergibt 100 Prozent", round(dist["low"] + dist["middle"] + dist["high"]), 100)
check("Grundlage dominiert", dist["low"] > 90, True)

# --- DFA distribution ----------------------------------------------------------------
dfa = {f"a{index}": {"secs_aerobic": 3000, "secs_transition": 400, "secs_anaerobic": 200}
       for index in range(10)}
measured = analytics.dfa_distribution({"wellness": {}, "activities": acts, "dfa": dfa})
check("DFA-Verteilung aerob", measured["aerobic"], 83.3)
check("DFA-Verteilung anaerob", measured["anaerobic"], 5.6)

# --- decoupling ------------------------------------------------------------------------
# "Steady endurance session" is now enforced, not promised. Until 0.39.0 this
# filtered on duration alone while its docstring claimed otherwise - so the
# chart and the durability tile next to it could draw from two different
# populations without anything saying so. One rejected case per criterion.
acts["short"] = {"start_date_local": "2026-09-01T09:00:00", "moving_time": 1200,
                 "decoupling": 12.0, "type": "Ride", "icu_intensity": 60,
                 "icu_average_watts": 120, "icu_weighted_avg_watts": 122}
acts["long"] = {"start_date_local": "2026-09-02T09:00:00", "moving_time": 7200,
                "decoupling": 3.4, "type": "Ride", "icu_training_load": 120,
                "icu_intensity": 60, "icu_average_watts": 120,
                "icu_weighted_avg_watts": 122}
acts["wellig"] = {"start_date_local": "2026-09-03T09:00:00", "moving_time": 7200,
                  "decoupling": 9.9, "type": "Ride", "icu_intensity": 60,
                  "icu_average_watts": 120, "icu_weighted_avg_watts": 160}
acts["rolle"] = {"start_date_local": "2026-09-04T09:00:00", "moving_time": 7200,
                 "decoupling": 8.8, "type": "VirtualRide", "icu_intensity": 60,
                 "icu_average_watts": 120, "icu_weighted_avg_watts": 122}
acts["hart"] = {"start_date_local": "2026-09-05T09:00:00", "moving_time": 7200,
                "decoupling": 7.7, "type": "Ride", "icu_intensity": 95,
                "icu_average_watts": 120, "icu_weighted_avg_watts": 122}
dec = analytics.decoupling_series({"wellness": {}, "activities": acts, "dfa": {}})
check("kurze Einheit fliegt raus", [item["decoupling"] for item in dec], [3.4])
# Fixture-Beweis: jede der drei neuen Zeilen wird von GENAU EINEM Kriterium
# gehalten - ohne diesen Nachweis könnte eine einzige Bedingung alle drei
# erledigen und die Prüfung sähe trotzdem grün aus.
check("Fixture-Beweis: wellige Einheit scheitert an der Gleichmäßigkeit",
      derive.steady_endurance_reason(acts["wellig"]), "variable")
check("Fixture-Beweis: Rollenfahrt scheitert an der Umgebung",
      derive.steady_endurance_reason(acts["rolle"]), "indoor")
check("Fixture-Beweis: harte Einheit scheitert an der Intensität",
      derive.steady_endurance_reason(acts["hart"]), "intense")
check("Fixture-Beweis: die ruhige Langfahrt kommt durch",
      derive.steady_endurance_reason(acts["long"]), None)

# --- HRV against the smallest worthwhile change -------------------------------------------
# S1 (0.69.0, Entscheidung 25.09., Wahl 1): EINE HRV-Basislinie fuer Ampel, Trainer
# und Signale - `baseline.norm_band`, 60 Naechte VOR dem beurteilten Tag, gewichtet
# ueber die Tagesetiketten. Bis 0.68.0 rechnete hrv_status eine eigene: Mittel und
# Streuung der letzten 60 ROLLWERTE einschliesslich heute, ungewichtet. Die alten
# Waechter (flache Reihe "normal", SWC 0) froren diesen zweiten Rechenweg ein;
# das eine Band verwirft eine flache Reihe (Streuung 0) wie der Trainer -
# nachgezogen wie bei F1.6.
import baseline  # noqa: E402
import coach  # noqa: E402
hrv_days = {}
for index in range(90):
    day = (today - timedelta(days=89 - index)).isoformat()
    hrv_days[day] = {"hrv": 50.0 + ((index * 7) % 5 - 2) * 1.0}
_hd = {"wellness": hrv_days, "activities": {}, "dfa": {}}
status = analytics.hrv_status(_hd)
check("stabile HRV gilt als normal", status["state"], "normal")
check("S1: das Band ist das des Trainers (Basislinie = ln des coach-Bands)",
      abs(status["baseline"] - math.log(coach.today(_hd)["bands"]["hrv"]["baseline"])) < 0.001, True)
check("S1: SWC = 0,5 x Streuung der Naechte davor", abs(status["swc"] - 0.5 * status["spread"]) < 1e-3, True)
check("S1: flache Reihe -> kein Band, kein Status (wie der Trainer)",
      analytics.hrv_status({"wellness": {(today - timedelta(days=89 - i)).isoformat(): {"hrv": 50.0} for i in range(90)},
                            "activities": {}, "dfa": {}}), None)

for index in range(80, 90):
    day = (today - timedelta(days=89 - index)).isoformat()
    hrv_days[day] = {"hrv": 30.0}
dropped = analytics.hrv_status({"wellness": hrv_days, "activities": {}, "dfa": {}})
check("HRV-Einbruch wird erkannt", dropped["state"], "below")
check("Hinweis zur Messmethode mitgeliefert", "overnight" in dropped["note"], True)
check("zu wenig Daten ergibt nichts",
      analytics.hrv_status({"wellness": {"2026-01-01": {"hrv": 50}}, "activities": {}, "dfa": {}}), None)

# GEWICHTET: 20 Nachtschicht-Naechte (Gewicht 0) bei 42 ms druecken die
# ungewichtete Basislinie (~47); gewichtet liegt sie bei ~50 und die letzten sieben
# Tage bei 46 sind ein Einbruch - ungewichtet nicht. Ampel-Komponente und Trainer muessen dasselbe sehen.
def _ctx(labels):
    w, ctx = {}, {}
    for i in range(120):
        d = (today - timedelta(days=119 - i)).isoformat()
        wob = ((i * 7) % 5 - 2) * 1.0
        hrv = 50.0 + wob
        if 80 <= i <= 99:
            hrv = 42.0 + wob
            if labels:
                ctx[d] = {"tag": "nachtschicht", "weight": 0.0, "note": "", "set_at": ""}
        if i >= 113:
            hrv = 46.0
        w[d] = {"id": d, "hrv": hrv, "restingHR": 56.0 - wob * 0.2, "sleepSecs": 27000}
    return {"wellness": w, "activities": {}, "dfa": {}, "day_context": ctx}
_gw, _ug = analytics.hrv_status(_ctx(True)), analytics.hrv_status(_ctx(False))
check("S1 Fixture: Etiketten aendern die Basislinie", _gw["baseline"] != _ug["baseline"], True)
check("S1: gewichtet meldet sich als gewichtet", (_gw.get("weighted"), _ug.get("weighted")), (True, False))
check("S1: gewichtet sieht den Einbruch, ungewichtet nicht", (_gw["state"], _ug["state"]), ("below", "normal"))
_rg = {c["id"]: c for c in analytics.readiness(_ctx(True))["components"]}["hrv"]
_ru = {c["id"]: c for c in analytics.readiness(_ctx(False))["components"]}["hrv"]
check("S1 Ampel: gewichtet amber/rot, ungewichtet gruen", (_rg["state"] in ("amber", "red"), _ru["state"]), (True, "green"))
check("S1 Ampel: die Komponente sagt, dass sie gewichtet rechnet", "gewichtet" in _rg["source"] and _rg.get("weighted") is True, True)
check("S1 Ampel: die Zahlen sind die des Trainers",
      abs(_rg["reference"] - math.log(coach.today(_ctx(True))["bands"]["hrv"]["baseline"])) < 0.001, True)
check("S1 Ampel: die Vorbemerkung nennt die Gewichtung und die Etiketten",
      "gewichtet" in str(analytics.readiness(_ctx(True)).get("context_note")) and "20" in str(analytics.readiness(_ctx(True)).get("context_note")), True)
check("S1 Ampel: ohne Etiketten keine Vorbemerkung", analytics.readiness(_ctx(False)).get("context_note"), None)
# Ebene 3 bleibt fuer die LAST: Budget und ACWR lesen keine Gewichte
check("S1: das Lastbudget bleibt kontextfrei",
      analytics.load_budget(_ctx(True), "green", today.isoformat()) == analytics.load_budget(_ctx(False), "green", today.isoformat()), True)

# --- zone times come in two shapes ------------------------------------------------
# Heart rate zone times are a plain list of seconds; power zone times arrive as
# objects per zone. 0.5.0 assumed the first shape and took the whole panel down
# with "float() argument must be ... not 'dict'".
objects = [
    {"id": "Z1", "secs": 600}, {"id": "Z2", "secs": 600}, {"id": "Z3", "secs": 300},
    {"id": "Z4", "secs": 300}, {"id": "Z5", "secs": 200},
]
check("Objektform wird gelesen",
      [round(value) for value in analytics._three_zone(objects)], [60, 15, 25])
check("gemischt und unbrauchbar wird nicht zum Absturz",
      analytics._three_zone([{"id": "Z1"}, "abc", None]), None)
check("Objektform ohne Sekunden", analytics._seconds({"id": "Z1"}), 0.0)
check("Zahl bleibt Zahl", analytics._seconds(1200), 1200.0)
check("Text mit Zahl", analytics._seconds("90"), 90.0)
check("Zonen als Objekt statt Liste", analytics._three_zone({"a": 1}), None)

# a single broken section must not take the whole payload down
broken = {"wellness": {"2026-09-10": {"ctl": 30, "atl": 20, "ctlLoad": 40}},
          "activities": {"x": {"start_date_local": "2026-09-10T09:00:00",
                               "moving_time": 3600, "icu_zone_times": "kaputt"}},
          "dfa": {}}
whole = analytics.summary(broken)
check("Gesamtauswertung ueberlebt einen kaputten Datensatz", isinstance(whole, dict), True)
check("Form trotzdem berechnet", whole["form"], 10)
check("kaputter Abschnitt bleibt leer", whole["intensity"], None)

# --- monotony needs at least three training days ---------------------------------
# Seen in the panel: a week with one session scored 0.58, which reads like
# "very varied" when it simply means the zeros dominate the spread.
one_day = {"wellness": {**{f"2026-02-{day:02d}": {"ctlLoad": 0.0} for day in range(2, 8)},
                        "2026-02-08": {"ctlLoad": 9.0}}, "activities": {}, "dfa": {}}
check("eine Einheit ergibt keine Monotonie", analytics.weekly_summary(one_day)[0]["monotony"], None)
three = {"wellness": {**{f"2026-02-{day:02d}": {"ctlLoad": 0.0} for day in range(2, 6)},
                      **{f"2026-02-{day:02d}": {"ctlLoad": 60.0} for day in range(6, 9)}},
         "activities": {}, "dfa": {}}
check("ab drei Einheiten wird gerechnet", analytics.weekly_summary(three)[0]["monotony"] is not None, True)

# --- decoupling: negative is not a warning -----------------------------------------
check("negative Entkopplung ist kein Warnsignal", analytics.decoupling_verdict(-15.5), "none")
check("kleine Entkopplung ist gut", analytics.decoupling_verdict(3.4), "good")
check("hohe Entkopplung faellt auf", analytics.decoupling_verdict(10.6), "high")

# --- readiness ------------------------------------------------------------------------
base = {"wellness": {}, "activities": {}, "dfa": {}}
for index in range(60):
    day = (today - timedelta(days=59 - index)).isoformat()
    base["wellness"][day] = {"hrv": 50.0, "restingHR": 52.0, "sleepSecs": 27000,
                             "ctlLoad": 60.0 if index % 2 else 0.0, "ctl": 35.0, "atl": 30.0}
good = analytics.readiness(base)
check("Ampel gruen bei unauffaelligen Werten", good["overall"], "green")
check("alle Signale vorhanden",
      sorted(item["id"] for item in good["components"]),
      ["acwr", "form", "hrv", "monotony", "rhr", "sleep", "subjective"])
check("Grenzen der Kombination benannt", "nicht unabhängig validiert" in good["note"], True)

# budget: the load allowed today follows straight from the ratio definition
# 0.73.1 umgestellt: readiness traegt kein Budget mehr (die Farbe kommt aus dem
# Zustand, coach.BUDGET_LIGHT); die Formel selbst wird hier direkt geprueft.
budget = analytics.load_budget(base, "green")
loads = [point["load"] for point in analytics.daily_load(base)]
expected = round(7 * (sum(loads[-28:]) / 28) * analytics.ACWR_HIGH - sum(loads[-6:]))
check("Lastbudget folgt der Definition", budget["recommended"], expected)
check("Budget kennt den Korridorrand", budget["corridor_top"], expected)
check("striktere Vorgabe bei roter Ampel",
      analytics.load_budget(base, "red")["recommended"] < budget["recommended"], True)

# a drop in HRV plus a raised resting heart rate must show up
stressed = {"wellness": dict(base["wellness"]), "activities": {}, "dfa": {}}
for index in range(3):
    day = (today - timedelta(days=index)).isoformat()
    stressed["wellness"][day] = {**stressed["wellness"][day], "hrv": 26.0, "restingHR": 63.0,
                                 "sleepSecs": 14000}
alarm = analytics.readiness(stressed)
check("Einbruch faerbt die Ampel", alarm["overall"], "red")
states = {item["id"]: item["state"] for item in alarm["components"]}
check("HRV meldet", states["hrv"] in ("amber", "red"), True)
check("Ruhepuls meldet", states["rhr"] in ("amber", "red"), True)
check("Schlaf meldet", states["sleep"] in ("amber", "red"), True)
# 0.73.1 umgestellt: vorher "Budget schrumpft mit der Ampel" (readiness.overall -> Faktor).
# Die Ampel faerbt nur noch sich selbst; der Faktor je Farbe bleibt (Formel unveraendert).
check("readiness traegt kein Budget mehr (0.73.1)", "budget" in alarm, False)
check("Faktor rot bleibt kleiner als gruen (Formel unveraendert)",
      analytics.load_budget(stressed, "red")["recommended"] < analytics.load_budget(stressed, "green")["recommended"], True)

# without any data the light says so instead of inventing a verdict
check("ohne Daten keine Aussage",
      analytics.readiness({"wellness": {}, "activities": {}, "dfa": {}})["overall"], "unknown")

# --- calendar grid ------------------------------------------------------------------
cal_data = {"wellness": {}, "activities": {}, "dfa": {}}
for index in range(40):
    day = (today - timedelta(days=39 - index)).isoformat()
    cal_data["wellness"][day] = {"ctl": 30.0 + index * 0.1, "atl": 28.0,
                                 "ctlLoad": 60.0 if index % 3 == 0 else 0.0,
                                 "sleepSecs": 27000, "hrv": 55.0, "restingHR": 51,
                                 "steps": 8000, "sleepScore": 82.0}
cal_data["activities"]["i1"] = {
    "start_date_local": today.isoformat() + "T09:00:00", "type": "VirtualRide",
    "name": "SweetSpot 2x20", "moving_time": 4200, "distance": 0.0,
    "icu_training_load": 83, "average_heartrate": 149, "icu_average_watts": 168,
    "icu_zone_times": [{"id": "Z1", "secs": 600}, {"id": "Z2", "secs": 1200},
                       {"id": "Z3", "secs": 2400}, {"id": "Z4", "secs": 0}, {"id": "Z5", "secs": 0}],
    "decoupling": 6.3,
}
cal_data["dfa"]["i1"] = {"secs_aerobic": 3000, "secs_transition": 900, "secs_anaerobic": 300,
                         "hr_at_threshold": 168.0, "hr_windows": 486, "power_windows": 486}
events = [{"start_date_local": (today + timedelta(days=1)).isoformat() + "T00:00:00",
           "name": "volumen", "type": "Ride", "icu_training_load": 45, "moving_time": 3600,
           "description": "DFa über 0,8", "paired_activity_id": None, "hide_from_athlete": False}]

grid = analytics.calendar_days(cal_data, events, weeks=4)
check("Raster beginnt an einem Montag",
      date.fromisoformat(grid["days"][0]["date"]).weekday(), 0)
check("Raster reicht in die Zukunft", grid["days"][-1]["future"], True)
check("heute ist markiert", sum(1 for day in grid["days"] if day["today"]), 1)

heute = next(day for day in grid["days"] if day["today"])
check("Aktivität am Tag einsortiert", heute["activities"][0]["name"], "SweetSpot 2x20")
check("Sportart gruppiert", heute["activities"][0]["group"], "ride")
check("Sportart benannt", heute["activities"][0]["sport"], "Rad (Rolle)")
check("Zonen als Dreiteilung", [round(v) for v in heute["activities"][0]["zones"]], [43, 57, 0])
check("DFA-Anteile am Tag", heute["activities"][0]["dfa"], [71, 21, 7])
check("Wellness am Tag", [heute["sleep_hours"], heute["hrv"], heute["resting_hr"]], [7.5, 55.0, 51])

morgen = next(day for day in grid["days"] if day["date"] == (today + timedelta(days=1)).isoformat())
check("geplante Einheit einsortiert", morgen["planned"][0]["name"], "volumen")
check("geplant und noch offen", morgen["planned"][0]["done"], False)

woche = next(item for item in grid["weeks"] if item["week"] == analytics._week_key(today.isoformat()))
# 0.67.2 (S2): die Wochenlast ist die Summe der TAGESLASTEN des Erzeugers
# (ctlLoad, hier 60 an jedem dritten Tag), nicht mehr die Aktivitaetssumme (83)
# neben Tageszellen aus ctlLoad. Der Erzeuger steht in analytics.load_by_day.
_tage = analytics.load_by_day(cal_data)
_soll = sum(v for d, v in _tage.items() if analytics._week_key(d) == woche["week"])
check("Wochenlast summiert (aus dem einen Erzeuger)", woche["load"], _soll)
check("Wochenlast summiert: Fixture-Beweis - Aktivitaetssumme und Tageslast sind verschieden", _soll != 83, True)
check("Wochenstunden", woche["hours"], 1.2)
check("geplante Last der Woche zählt getrennt", woche["planned_load"] >= 0, True)
check("Wochen chronologisch", [item["week"] for item in grid["weeks"]] ==
      sorted(item["week"] for item in grid["weeks"]), True)
check("Bezugsgrößen für die Balken vorhanden",
      grid["max_week_load"] > 0 and grid["max_day_load"] > 0, True)

# an empty archive must still produce a usable grid
leer = analytics.calendar_days({"wellness": {}, "activities": {}, "dfa": {}}, [], weeks=2)
check("leeres Raster hat trotzdem Tage", len(leer["days"]) > 14, True)
check("leeres Raster ohne Wochenlast", leer["max_week_load"], 0)

# --- Ebene 3 (Paket B3): die Last kennt keine Etiketten -------------------------
# Ein Nachtschicht-Etikett macht die GEMESSENE Trainingslast nicht kleiner.
# Verhaltens-Wächter: identische Archive mit und ohne Etiketten müssen in
# ACWR, Monotonie, Lastbudget und daily_load dasselbe ergeben.
# S1 (0.69.0, Entscheidung 25.09.): die HRV-Rechnung von analytics (hrv_status,
# Ampel-Komponente) liest die Gewichte jetzt - ueber baseline.py, denselben
# Erzeuger wie der Trainer. Bis 0.68.0 stand sie hier in der Liste der
# kontextfreien Funktionen; der Waechter zieht nach. Das Budget der Ampel
# bleibt kontextfrei, auch wenn die Ampelfarbe sich durch die Gewichtung
# aendert (readiness liest die Farbe, load_budget die Last).
import json as _json
from datetime import date as _date, timedelta as _td

_T = _date(2026, 9, 11)
_lvl3 = {"wellness": {}, "activities": {}, "dfa": {}}
for _i in range(90):
    _d = (_T - _td(days=89 - _i)).isoformat()
    _lvl3["wellness"][_d] = {"ctlLoad": 60.0 if _i % 3 else 0.0,
                             "hrv": 50 + (_i * 7) % 5 - 2,
                             "restingHR": 56, "sleepSecs": 27000,
                             "ctl": 30, "atl": 28}
_lvl3_ctx = _json.loads(_json.dumps(_lvl3))
_lvl3_ctx["day_context"] = {
    (_T - _td(days=_o)).isoformat(): {"tag": "nachtschicht", "weight": 0.0,
                                      "note": "", "set_at": ""}
    for _o in range(1, 25)}

for _name in ("daily_load", "weekly_summary"):
    _fn = getattr(analytics, _name)
    check(f"Ebene 3: {_name} ignoriert Etiketten",
          _json.dumps(_fn(_lvl3), sort_keys=True, default=str)
          == _json.dumps(_fn(_lvl3_ctx), sort_keys=True, default=str), True)
if callable(getattr(analytics, "window_ratio", None)):
    _lvl3_day = sorted(_lvl3["wellness"])[-1]
    check("Ebene 3: window_ratio ignoriert Etiketten",
          analytics.window_ratio(_lvl3, _lvl3_day) == analytics.window_ratio(_lvl3_ctx, _lvl3_day), True)
else:
    check("Ebene 3: window_ratio fehlt", "FEHLT", "da")
for _state in ("green", "amber", "red"):
    check(f"Ebene 3: load_budget ignoriert Etiketten ({_state})",
          analytics.load_budget(_lvl3, _state) == analytics.load_budget(_lvl3_ctx, _state), True)
# S1-Gegenprobe: die HRV-Seite liest die Etiketten (sonst waere die Gewichtung tot)
check("S1: hrv_status liest die Etiketten",
      analytics.hrv_status(_lvl3)["baseline"] != analytics.hrv_status(_lvl3_ctx)["baseline"]
      or analytics.hrv_status(_lvl3)["weighted"] != analytics.hrv_status(_lvl3_ctx)["weighted"], True)

# Quelltext-Wächter: die Mauer steht im Code, nicht in der Absicht.
# analytics.py liest day_context seit S1 nur ueber baseline.py (HRV), nie direkt.
for _mod in ("analytics.py", "plan.py", "workouts.py"):
    _src = (COMP / _mod).read_text(encoding="utf-8")
    check(f"Ebene 3: {_mod} liest day_context nicht",
          "day_context" in _src, False)

print()

# --- week_done: ridden against planned, and NOTHING paired (ausbau.md I2) ------
# The trap the specification names: the plan says "SweetSpot 2x20, 1.2 h" and
# "Grundlage 1.2 h", and a 1.2-hour ride in the archive fits BOTH. A view that
# picks one is claiming something the data does not carry. So the fixture makes
# that ambiguity explicit and the test asserts that nothing decides it.
AMBIGUOUS = {
    "activities": {
        "r1": {"id": "r1", "start_date_local": "2026-09-08T09:00:00", "type": "Ride",
               "name": "Feierabendrunde", "moving_time": 4320, "icu_training_load": 70,
               "icu_intensity": 68},
        # same duration, same day-shape: would fit the quality slot as well as
        # the base ride of the same week
        "r2": {"id": "r2", "start_date_local": "2026-09-10T09:00:00", "type": "Ride",
               "name": "Runde zwei", "moving_time": 4320, "icu_training_load": 72,
               "icu_intensity": 69},
        # outside the week - must not be counted
        "r0": {"id": "r0", "start_date_local": "2026-09-06T09:00:00", "type": "Ride",
               "name": "Sonntag davor", "moving_time": 7200, "icu_training_load": 120},
        "r9": {"id": "r9", "start_date_local": "2026-09-14T09:00:00", "type": "Ride",
               "name": "Montag danach", "moving_time": 7200, "icu_training_load": 130},
    },
    "wellness": {}, "dfa": {},
}
week = analytics.week_done(AMBIGUOUS, "2026-09-07", today="2026-09-11")
check("Woche: Einheiten der Kalenderwoche", week["sessions"], 2)
check("Woche: Last der Kalenderwoche", week["load"], 142)
check("Woche: Stunden der Kalenderwoche", week["hours"], 2.4)
check("Woche: Fenster beginnt Montag", week["start"], "2026-09-07")
check("Woche: Fenster endet Sonntag", week["end"], "2026-09-13")
check("Woche: Resttage", week["days_left"], 2)
names = [item["name"] for item in week["activities"]]
check("Woche: Fahrt davor bleibt draussen", "Sonntag davor" in names, False)
check("Woche: Fahrt danach bleibt draussen", "Montag danach" in names, False)

# the pairing: it must not exist, and the payload must SAY that it does not
check("Woche: keine Zuordnung behauptet", week["paired"], False)
for forbidden in ("workout", "role", "matched", "session", "plan_session"):
    check(f"Woche: keine Fahrt traegt '{forbidden}'",
          any(forbidden in item for item in week["activities"]), False)
check("Woche: Grenze der Zuordnung steht dran", "entscheidest du" in week["note"], True)

# a week with nothing in it says zero, it does not vanish
empty = analytics.week_done(AMBIGUOUS, "2026-08-03", today="2026-09-11")
check("Woche: leere Woche zaehlt null Einheiten", empty["sessions"], 0)
check("Woche: leere Woche zaehlt null Last", empty["load"], 0)
check("Woche: vergangene Woche ohne Resttage", empty["days_left"], None)


# --- F2.10 · BUDGET = Gesamtlast des Tages, nicht Restlast (Entscheidung 24.09.) ---
# `load_budget` zog `loads[-6:]` ab; liegt der letzte wellness-Tag auf heute (am
# Livebestand: ja, mit Last 0 bis zum Import), stecken heute und nur FUENF Tage
# davor in der Summe - und nach dem Import schrumpft das Budget um die eigene
# Fahrt. Jetzt: die sechs Tage VOR heute, heute als Verbrauch beziffert.
from datetime import date as _date, timedelta as _td
def _bestand(heute_last):
    d = {"wellness": {}, "activities": {}}
    t0 = _date(2026, 9, 24)
    for i in range(35):
        day = (t0 - _td(days=34 - i)).isoformat()
        d["wellness"][day] = {"ctlLoad": 40.0}
    d["wellness"][t0.isoformat()]["ctlLoad"] = heute_last
    return d
_mit = analytics.load_budget(_bestand(60.0), "green", today="2026-09-24")
_ohne = analytics.load_budget(_bestand(0.0), "green", today="2026-09-24")
check("F2.10 Treffer: die heutige Fahrt zaehlt nicht gegen das Budget", _mit["recommended"], _ohne["recommended"])
check("F2.10 Treffer: der Verbrauch ist beziffert", _mit.get("used_today"), 60.0)
check("F2.10 Gegenprobe: ohne heutige Fahrt Verbrauch 0", _ohne.get("used_today"), 0.0)
check("F2.10 Eigenschaft: die sechs Tage davor sind sechs Tage", _mit["last_six_days"], 240.0)
check("F2.10 Eigenschaft: chronisch ohne heute", _mit["chronic"], 40.0)
# Randfall: kein Eintrag fuer heute (Reihe endet gestern) -> die sechs letzten sind die sechs davor
_gestern = _bestand(0.0); del _gestern["wellness"]["2026-09-24"]
_g = analytics.load_budget(_gestern, "green", today="2026-09-24")
check("F2.10 Randfall ohne heutige Zeile: dieselbe Grenze, Verbrauch 0", (_g["recommended"], _g.get("used_today")), (_ohne["recommended"], 0.0))


# --- F2.9 · Form ABSOLUT, ein Erzeuger fuer Belastung und Ampel (Entscheidung 24.09.) --
# Bis 0.67.3 stufte summary() absolut (+6,8 -> grey) und readiness() relativ
# (+21,5 % -> transition, amber) - dieselbe Tabelle, zwei Eingaben. Bei CTL ~30
# ist relativ dreimal so grob. Jetzt: analytics.form_state(ctl, atl) als der
# eine Erzeuger, beide Reiter lesen ihn, absolut. Rot an 0.67.3.
_f29 = {"wellness": {}, "activities": {}}
for _i in range(35):
    _d = (_date(2026, 9, 24) - _td(days=34 - _i)).isoformat()
    _f29["wellness"][_d] = {"ctl": 31.4, "atl": 24.7, "ctlLoad": 40.0, "hrv": 60.0, "restingHR": 50, "sleepSecs": 25200}
_fs = analytics.form_state(31.4, 24.7)
check("F2.9 Erzeuger: die Form ist absolut +6,7 -> grey", (round(_fs["form"], 1), _fs["zone"]), (6.7, "grey"))
check("F2.9 Erzeuger: relativ steht daneben, entscheidet aber nicht", round(_fs["percent"], 1), 21.3)
_rd = analytics.readiness(_f29)  # 0.73.3 umgestellt: readiness hat keinen Parameter today mehr
_fc = [c for c in _rd["components"] if c["id"] == "form"][0]
check("F2.9 Treffer Ampel: die Form-Komponente stuft absolut (grey -> green)", _fc["state"], "green")
check("F2.9 Treffer Ampel: der Wert ist die absolute Form", _fc.get("value"), 6.7)
_su = analytics.summary(_f29)
check("F2.9 Belastung: dieselbe Zone", _su.get("form_zone"), "grey")
# Gegenprobe: eine Form, die absolut UND relativ in derselben Zone liegt, aendert nichts
check("F2.9 Gegenprobe: -40 absolut ist high_risk wie zuvor", analytics.form_state(30.0, 70.0)["zone"], "high_risk")


# --- 0.73.0 · die Familie einer Fahrt (Skizze §4) und das Fenster (§5) ------------
import workouts as _W73  # noqa: E402
_NOTE = _W73.DEFAULT_NOTE
def _act(day, name, load, typ="Ride", **kw):
    a = {"start_date_local": f"{day}T08:00:00", "name": name, "type": typ,
         "icu_training_load": load, "moving_time": 3600}
    a.update(kw)
    return a
_ev = [
    {"id": 501, "name": "Grundlage 90 min", "description": _NOTE + "\n\n- 90m 65%"},             # Altbestand
    {"id": 502, "name": "Tempo 2×20 min", "description": "x", "external_id": "ha-intervals-icu:tempo_2x20:2026-09-26"},
    {"id": 503, "name": "VO2max 4×4 min", "description": "x", "external_id": "garmin:123"},       # fremd
    {"id": 504, "name": "SweetSpot 2x20", "description": _NOTE + "\n\n..."},                       # umbenannt
    {"id": 505, "name": "Grundlage 90 min", "description": "von Hand angelegt"},                  # ohne Hinweiszeile
    {"id": 506, "name": "x", "description": "x", "external_id": "ha-intervals-icu:gibtsnicht:2026-09-26"},
]
_af = {"activities": {
    "m1": _act("2026-09-20", "SweetSpot 2x...", 90, paired_event_id="501"),
    "m2": _act("2026-09-25", "VO2max-Inter...", 75),
    "p1": _act("2026-09-24", "Runde", 50, paired_event_id="501"),
    "p2": _act("2026-09-24", "Runde", 50, paired_event_id=502),
    "p3": _act("2026-09-24", "Runde", 50, paired_event_id="503"),
    "p4": _act("2026-09-24", "Runde", 50, paired_event_id="504"),
    "p5": _act("2026-09-24", "Runde", 50, paired_event_id="505"),
    "p6": _act("2026-09-24", "Runde", 50, paired_event_id="599"),
    "p7": _act("2026-09-24", "Runde", 50, paired_event_id="506"),
    "c1": _act("2026-09-22", "Rehburg-Loccum", 95, paired_event_id="501", commute=True),
    "r1": _act("2026-09-23", "Lauf", 20, typ="Run"),
    "n1": _act("2026-09-23", "Grundlage 90 min", 30),        # Name = Katalogtitel, aber NICHT gepaart
}, "section_marks": {
    "m1": {"marks": {"sweetspot": [2, 4]}},
    "m2": {"marks": {"vo2max": [3, 5, 7, 9], "sweetspot": [1], "endurance": [11]}},
    "p1": {"marks": {"vo2max": []}},                          # leere Marke = keine Marke
}, "events": _ev}
_fam = getattr(analytics, "activity_family", None)
check("0.73.0 2: analytics.activity_family existiert", callable(_fam), True)
if callable(_fam):
    def _g(aid, **kw): r = _fam(_af, aid, **kw) or {}; return (r.get("group"), r.get("source"))
    check("0.73.0 2 Marken: SweetSpot -> schwelle", _g("m1"), ("schwelle", "marks"))
    check("0.73.0 2 Marken mehrerer Familien: die haerteste gibt die Gruppe", _g("m2"), ("vo2max", "marks"))
    check("0.73.0 2 Marken mehrerer Familien: families nennt alle",
          sorted((_fam(_af, "m2") or {}).get("families") or []), ["endurance", "sweetspot", "vo2max"])
    check("0.73.0 2 Plan Altbestand: Hinweiszeile + Katalogtitel -> grundlage", _g("p1"), ("grundlage", "plan"))
    check("0.73.0 2 Plan external_id -> schwelle (int-ID gegen int-Event)", _g("p2"), ("schwelle", "plan"))
    check("0.73.0 2 fremde external_id -> ohne Zuordnung", _g("p3"), (None, None))
    check("0.73.0 2 Altbestand mit umbenanntem Titel -> ohne Zuordnung", _g("p4"), (None, None))
    check("0.73.0 2 Katalogtitel ohne Hinweiszeile -> ohne Zuordnung", _g("p5"), (None, None))
    check("0.73.0 2 paired_event_id ins Leere -> ohne Zuordnung", _g("p6"), (None, None))
    check("0.73.0 2 eigene external_id mit unbekanntem Schluessel -> ohne Zuordnung", _g("p7"), (None, None))
    check("0.73.0 2 gepaarte Pendelfahrt -> nie ueber den Plan", _g("c1"), (None, None))
    check("0.73.0 2 Pendelfahrt: commute steht im Ergebnis", (_fam(_af, "c1") or {}).get("commute"), True)
    _r1 = _fam(_af, "r1") or {}
    check("0.73.0 2 andere Sportart -> other mit Sportwort", (_r1.get("group"), _r1.get("source"), _r1.get("sport")), ("other", "sport", "Lauf"))
    check("0.73.0 2 kein Namensvergleich: Katalogtitel als Aktivitaetsname ungepaart -> ohne Zuordnung", _g("n1"), (None, None))
    check("0.73.0 2 unbekannte Aktivitaet -> None", _fam(_af, "gibtsnicht"), None)
    # Marken + Paarung widersprechen: die Marken gewinnen
    _mp = {**_af, "activities": {**_af["activities"], "mp": _act("2026-09-24", "x", 50, paired_event_id="502")},
           "section_marks": {**_af["section_marks"], "mp": {"marks": {"endurance": [1]}}}}
    check("0.73.0 2 Marken vor Plan", (_fam(_mp, "mp") or {}).get("group"), "grundlage")
    # Pendelfahrt MIT Marken: die Marken gelten (nur der Plan ist gesperrt)
    _cm = {**_af, "section_marks": {**_af["section_marks"], "c1": {"marks": {"vo2max": [1]}}}}
    check("0.73.0 2 Pendelfahrt mit Marken: Marken gelten", (_fam(_cm, "c1") or {}).get("group"), "vo2max")
    # Events als eigener Parameter (Koordinator-Daten, nicht Archiv)
    _noev = {k: v for k, v in _af.items() if k != "events"}
    check("0.73.0 2 ohne Events im Archiv: kein Plan", (_fam(_noev, "p2") or {}).get("group"), None)
    check("0.73.0 2 Events als Parameter", (_fam(_noev, "p2", events=_ev) or {}).get("group"), "schwelle")
    # Leseweg: activity_family schreibt nichts
    import copy as _copy73
    _before = _copy73.deepcopy(_af)
    for _aid in list(_af["activities"]):
        _fam(_af, _aid)
    check("0.73.0 2 activity_family schreibt nichts", _af == _before, True)
    # blocks.family_of und Zonen werden NICHT gelesen (Quelltext)
    import inspect as _insp73
    _src = _insp73.getsource(_fam).split('"""')[2]  # ohne Docstring: der Code
    check("0.73.0 2 kein Namens-Rateweg (family_of)", "family_of" in _src, False)
    check("0.73.0 2 keine Zonen / kein WORK-Etikett", any(x in _src for x in ("icu_zone_times", "icu_intervals", "WORK")), False)

# Fenster: 35 Tage, ganzzahlige Lasten, heute 26.09.
def _fenster(heute_last=40.0, luecke=False):
    d = {"wellness": {}, "activities": {}, "section_marks": {}, "events": list(_ev)}
    t0 = _date(2026, 9, 26)
    for i in range(35):
        day = (t0 - _td(days=34 - i)).isoformat()
        d["wellness"][day] = {"ctlLoad": 30.0}
    for day, v in {"2026-09-19": 50.0, "2026-09-20": 90.0, "2026-09-21": 0.0, "2026-09-22": 95.0,
                   "2026-09-23": 60.0, "2026-09-24": 0.0, "2026-09-25": 75.0, "2026-09-26": heute_last}.items():
        d["wellness"][day] = {"ctlLoad": v}
    d["activities"] = {
        "a19": _act("2026-09-19", "vor dem Fenster", 50),
        "a20": _act("2026-09-20", "SweetSpot 2x...", 90),
        "a22": _act("2026-09-22", "Rehburg-Loccum", 95, paired_event_id="501", commute=True),
        "a23b": {**_act("2026-09-23", "Lauf", 20, typ="Run"), "start_date_local": "2026-09-23T18:00:00"},
        "a23a": _act("2026-09-23", "Grundlage", 30),
        "a25": _act("2026-09-25", "VO2max-Inter...", 75),
    }
    if heute_last:
        d["activities"]["a26"] = _act("2026-09-26", None, heute_last, paired_event_id="502")
    d["section_marks"] = {"a20": {"marks": {"sweetspot": [1]}}, "a23a": {"marks": {"endurance": [1]}},
                          "a25": {"marks": {"vo2max": [1, 2]}}}
    if luecke:
        del d["wellness"]["2026-09-21"]
    return d
_fb = analytics.load_budget(_fenster(), "green", today="2026-09-26")
check("0.73.0 3 Fenster: Start/Ende", (_fb.get("window_start"), _fb.get("window_end")), ("2026-09-20", "2026-09-26"))
check("0.73.0 3 Fenster: Last = sechs Tage davor + heute", _fb.get("window_load"), 320.0 + 40.0)
check("0.73.0 3 Fenster: erlaubt = 7 x chronisch x Ziel", _fb.get("window_allowed"), round(7 * _fb["chronic"] * 1.3))
check("0.73.0 3 Fenster: erlaubt - sechs Tage = recommended (gleiche Rechnung)",
      _fb.get("window_allowed", 0) - _fb["last_six_days"], _fb["recommended"])
check("0.73.0 3 Fenster: frei = erlaubt - Fensterlast (= recommended - heute)",
      _fb.get("window_free"), max(0, _fb.get("window_allowed", 0) - _fb.get("window_load", 0)))
check("0.73.0 3 Fenster: frei = recommended - used_today", _fb.get("window_free"), max(0, _fb["recommended"] - 40))
_c = _fb["chronic"]
check("0.73.0 3 Baender x0,8/1,0/1,3/1,5", _fb.get("window_bands"),
      {"low": round(7 * _c * 0.8), "steady": round(7 * _c * 1.0), "top": round(7 * _c * 1.3), "risk": round(7 * _c * 1.5)})
# 0.73.1 umgestellt (2.3): drops_next = aeltester Fenstertag MIT Last, dazu leaves_on
check("0.73.0/0.73.1 3 der aelteste Fenstertag mit Last und wann er geht", _fb.get("drops_next"),
      {"date": "2026-09-20", "load": 90.0, "leaves_on": "2026-09-27"})
# 0.73.1 · 2.3: Tage mit 0 werden uebersprungen
_z = _fenster(); _z["wellness"]["2026-09-20"] = {"ctlLoad": 0.0}
check("0.73.1 2.3 drops_next ueberspringt den Tag mit 0", analytics.load_budget(_z, "green", today="2026-09-26").get("drops_next"),
      {"date": "2026-09-22", "load": 95.0, "leaves_on": "2026-09-29"})
_n = _fenster(heute_last=0.0)
for _day in ("2026-09-20", "2026-09-22", "2026-09-23", "2026-09-25"):
    _n["wellness"][_day] = {"ctlLoad": 0.0}
check("0.73.1 2.3 keiner mit Last -> None", analytics.load_budget(_n, "green", today="2026-09-26").get("drops_next", "fehlt"), None)
_h = _fenster(); 
for _day in ("2026-09-20", "2026-09-21", "2026-09-22", "2026-09-23", "2026-09-24", "2026-09-25"):
    _h["wellness"][_day] = {"ctlLoad": 0.0}
check("0.73.1 2.3 nur heute mit Last -> heute, geht in 7 Tagen", analytics.load_budget(_h, "green", today="2026-09-26").get("drops_next"),
      {"date": "2026-09-26", "load": 40.0, "leaves_on": "2026-10-03"})
# 0.73.1 · 2.4: der Tag vor dem Fenster (faellt gegenueber dem Fenster von gestern heraus), aus derselben Reihe
check("0.73.1 2.4 window_before = Tag vor window_start mit seiner Last", _fb.get("window_before"), {"date": "2026-09-19", "load": 50.0})
_mb = analytics.load_budget(_fenster(), "green", today="2026-09-27")
check("0.73.1 2.4 Morgen-Fenster: 21.-27., davor der 20. mit 90",
      (_mb.get("window_start"), _mb.get("window_end"), _mb.get("window_before")), ("2026-09-21", "2026-09-27", {"date": "2026-09-20", "load": 90.0}))
_fa = analytics.load_budget(_fenster(), "amber", today="2026-09-26")
_fr = analytics.load_budget(_fenster(), "red", today="2026-09-26")
check("0.73.0 3 Ampel gelb: Zielstrich x1,0", _fa.get("window_allowed"), _fa.get("window_bands", {}).get("steady"))
check("0.73.0 3 Ampel rot: Zielstrich x0,8", _fr.get("window_allowed"), _fr.get("window_bands", {}).get("low"))
check("0.73.0 3 Ampel rot: frei nie negativ", _fr.get("window_free"), 0)
check("0.73.0 3 Rechnung unveraendert: recommended wie ohne Fensterfelder",
      {k: _fb[k] for k in ("chronic", "last_six_days", "target_ratio", "recommended", "used_today", "steady", "corridor_top", "risk_top", "state")},
      {"chronic": round(_c, 1), "last_six_days": 320.0, "target_ratio": 1.3,
       "recommended": max(0, round(7 * _c * 1.3 - 320)), "used_today": 40.0,
       "steady": max(0, round(7 * _c - 320)), "corridor_top": max(0, round(7 * _c * 1.3 - 320)),
       "risk_top": max(0, round(7 * _c * 1.5 - 320)), "state": "green"})
_ws_fn = getattr(analytics, "window_sessions", None)
check("0.73.0 3: analytics.window_sessions existiert", callable(_ws_fn), True)
if callable(_ws_fn):
    _ws = _ws_fn(_fenster(), "2026-09-26")
    _ss = _ws.get("sessions") or []
    check("0.73.0 3 Summe = window_load", round(sum(x["load"] for x in _ss), 1), _fb["window_load"])
    check("0.73.0 3 total = window_load", _ws.get("total"), _fb["window_load"])
    check("0.73.0 3 Reihenfolge: Tag, dann Startzeit; vor dem Fenster fehlt",
          [(x["date"], x.get("name"), x.get("rest", False)) for x in _ss],
          [("2026-09-20", "SweetSpot 2x...", False), ("2026-09-22", "Rehburg-Loccum", False),
           ("2026-09-23", "Grundlage", False), ("2026-09-23", "Lauf", False), ("2026-09-23", None, True),
           ("2026-09-25", "VO2max-Inter...", False), ("2026-09-26", None, False)])
    _rest = [x for x in _ss if x.get("rest")]
    check("0.73.0 3 Rest: ctlLoad 60 > 30 + 20 -> 10 ohne Einheit", [(x["date"], x["load"], x["group"]) for x in _rest], [("2026-09-23", 10.0, None)])
    check("0.73.0 3 Gruppen je Fahrt", [x["group"] for x in _ss], ["schwelle", None, "grundlage", "other", None, "vo2max", "schwelle"])
    check("0.73.0 3 Quelle je Fahrt", [x["source"] for x in _ss], ["marks", None, "marks", "sport", "rest", "marks", "plan"])
    check("0.73.0 3 Pendelfahrt markiert", [x["commute"] for x in _ss], [False, True, False, False, False, False, False])
    check("0.73.0 3 Sportwort", [x["sport"] for x in _ss][:4], ["Rad", "Rad", "Rad", "Lauf"])
    check("0.73.0 3 Summen je Gruppe", _ws.get("groups"),
          {"grundlage": 30.0, "schwelle": 130.0, "vo2max": 75.0, "other": 20.0, "none": 105.0})
    check("0.73.0 3 Summen je Gruppe ergeben total", round(sum((_ws.get("groups") or {}).values()), 1), _ws.get("total"))
    check("0.73.0 3 kein Widerspruch Tageslast/Aktivitaeten", _ws.get("mismatch"), [])
    # zwei Fahrten an einem Tag, heute importiert: beide stehen da (23.) und heute zaehlt
    check("0.73.0 3 heutige Fahrt im Fenster", any(x["date"] == "2026-09-26" and not x.get("rest") for x in _ss), True)
    # Fenster leer
    _leer = _fenster(heute_last=0.0)
    for _day in ("2026-09-20", "2026-09-22", "2026-09-23", "2026-09-25"):
        _leer["wellness"][_day] = {"ctlLoad": 0.0}
    _leer["activities"] = {"a19": _act("2026-09-19", "vor dem Fenster", 50)}
    _wl = _ws_fn(_leer, "2026-09-26")
    check("0.73.0 3 Fenster leer: keine Fahrt, total 0", (_wl.get("sessions"), _wl.get("total")), ([], 0.0))
    # Tageslast kleiner als Aktivitaeten: benannt, nicht versteckt
    _mm = _fenster(); _mm["wellness"]["2026-09-25"] = {"ctlLoad": 60.0}
    _wm = _ws_fn(_mm, "2026-09-26")
    check("0.73.0 3 Randfall ctlLoad < Aktivitaeten: Tag benannt", _wm.get("mismatch"), ["2026-09-25"])
    # Wellness-Luecke: dieselben Tage wie das Budget (Reihe lueckenlos), 21. hat Last 0
    _gap = _fenster(luecke=True)
    _gb = analytics.load_budget(_gap, "green", today="2026-09-26")
    _gw = _ws_fn(_gap, "2026-09-26")
    check("0.73.0 3 Luecke: Summe = window_load", round(sum(x["load"] for x in _gw["sessions"]), 1), _gb["window_load"])
    # weniger als 28 Tage: kein Budget, aber das Fenster (Regel 10: Liste bleibt)
    _kurz = _fenster()
    for _day in sorted(_kurz["wellness"])[:20]:
        del _kurz["wellness"][_day]
    check("0.73.0 3 unter 28 Tagen: kein Budget", analytics.load_budget(_kurz, "green", today="2026-09-26"), None)
    _wk = _ws_fn(_kurz, "2026-09-26")
    check("0.73.0 3 unter 28 Tagen: die Fahrten stehen trotzdem", len(_wk.get("sessions") or []), 7)
    # zweiter Athlet ohne Marken und ohne Events: alles ohne Zuordnung, Rad
    _b = _fenster(); _b["section_marks"] = {}; _b["events"] = []
    _wb = _ws_fn(_b, "2026-09-26")
    check("0.73.0 3 Athlet B: alle Radfahrten ohne Zuordnung",
          sorted({x["group"] for x in _wb["sessions"] if x["sport"] == "Rad"}, key=str), [None])


# --- 0.73.3 · §1 der Satz im Wochenplan, §2 readiness ohne today ---------------
_wd = analytics.week_done(AMBIGUOUS, "2026-09-07", today="2026-09-11")
check("0.73.3 §1: neuer Satz woertlich", _wd["note"],
      "Gefahren gegen vorgesehen — welche Fahrt welche geplante Einheit war, entscheidest du. "
      "Die Familie einer Fahrt kommt aus deinen Marken oder aus der Paarung in intervals.icu; geraten wird nichts.")
check("0.73.3 §1: der alte Satz ist fort", "niemand belegen kann" in _wd["note"] or "kein Etikett" in _wd["note"], False)
check("0.73.3 §1: paired bleibt False", _wd["paired"], False)
import inspect as _insp733
check("0.73.3 §2: readiness ohne Parameter today", list(_insp733.signature(analytics.readiness).parameters), ["data"])

# --- 0.73.4 · E4 §3.2: was to_event schreibt, liest _planned_key zurueck --------
# Fuer JEDEN Schluessel im Katalog samt Stufentest, roh und gerechnet. Der Name
# wird umbenannt und die Hinweiszeile fehlt: tragen darf nur die Kennung, nicht
# der Altbestand-Weg (sonst bestuende die Probe auch ohne Kennung).
_rl_fail = []
for _k, _en in sorted(_W73.BY_KEY.items()):
    for _src in (_en, _W73.scaled(_en, 215.0, 157)):
        _pl = _W73.to_event(_src, "2026-09-27", note=None)
        _ev4 = dict(_pl, id=9001, name="von Johannes umbenannt")
        if analytics._planned_key([_ev4], 9001) != _k:
            _rl_fail.append(_k)
check("0.73.4 §3.2: Rundlauf to_event -> _planned_key fuer jeden Katalogschluessel", _rl_fail, [])
check("0.73.4 §3.2 Fixture: der Stufentest ist im Rundlauf dabei", _W73.RAMP_TEST["key"] in _W73.BY_KEY, True)
# Gegenprobe: dasselbe Event OHNE Kennung faellt bei umbenanntem Titel heraus -
# die Zuordnung oben kommt also wirklich aus dem neuen Feld.
_ohne4 = {k: v for k, v in _W73.to_event(_W73.BY_KEY["vo2_4x4"], "2026-09-27").items() if k != "external_id"}
check("0.73.4 §3.2 Gegenprobe: ohne Kennung und umbenannt -> keine Zuordnung",
      analytics._planned_key([dict(_ohne4, id=1, name="umbenannt")], 1), None)
check("0.73.4 §3.2 Gegenprobe: ohne Kennung, Altbestand (Hinweiszeile + Titel) -> vo2_4x4",
      analytics._planned_key([dict(_ohne4, id=1)], 1), "vo2_4x4")
# durch activity_family: eine umbenannte, gepaarte Fahrt landet in ihrer Familie
_af4 = {"activities": {"e4": _act("2026-09-27", "Morgenrunde", 80, paired_event_id=9001)},
        "section_marks": {}, "events": [dict(_W73.to_event(_W73.BY_KEY["vo2_4x4"], "2026-09-27"),
                                               id=9001, name="umbenannt")]}
if callable(_fam):
    _r4 = _fam(_af4, "e4") or {}
    check("0.73.4 §3.2: umbenanntes eigenes Workout -> vo2max/plan", (_r4.get("group"), _r4.get("source")), ("vo2max", "plan"))

# =============================================================================
# 0.74.0 · BELASTUNGS-REITER NEU (Skizze 0.74.0 §3.1 a-i, §4, §8)
# Rot vor dem Bau: die neuen Funktionen fehlen, `planned` ist unbekannt,
# readiness liest acwr_series, summary traegt acwr/acwr_latest/thresholds.acwr_*.
# Die Bitgenau-Pruefungen (load_budget ohne planned, window_sessions nach dem
# Herausloesen) halten Pruefsummen, die an 0.73.4 (ce9b14b) gezogen wurden.
# =============================================================================
import hashlib as _hl  # noqa: E402
import json as _js  # noqa: E402


def _try(fn, *a, **k):
    try:
        return fn(*a, **k)
    except Exception as exc:  # noqa: BLE001 - rot vor dem Bau
        return f"FEHLT: {type(exc).__name__}: {exc}"


def _sha(obj):
    return _hl.sha256(_js.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


_BL_END = date(2026, 9, 26)          # ein Samstag: KW 39 = 21.-27.09.
_BL_PAT = [0.0, 62.0, 35.0, 0.0, 91.0, 44.0, 118.0]
_BL_FAM = ["endurance", "sweetspot", "vo2max"]


def _bl(n=70, end=_BL_END, marks=True, events=True):
    """Erfundener Bestand (Regel 10): Tageslast = Aktivitaet, ausser an jedem
    zehnten Tag (Rest 10), ein Lauf, und eine alte Fahrt mit Paarung ohne Event."""
    d = {"wellness": {}, "activities": {}, "dfa": {}, "section_marks": {}, "events": []}
    for i in range(n):
        day = (end - timedelta(days=n - 1 - i)).isoformat()
        base = _BL_PAT[i % 7]
        load = base + float(i % 3) if base else 0.0
        d["wellness"][day] = {"ctlLoad": load}
        if not load:
            continue
        ride = load - 10.0 if i % 10 == 0 else load
        key = f"b{i}"
        d["activities"][key] = _act(day, f"Fahrt {i}", ride, typ="Run" if i % 13 == 0 else "Ride",
                                    paired_event_id=("9" + str(i)) if i < 20 else None)
        if marks and i % 13 and i % 4:
            d["section_marks"][key] = {"marks": {_BL_FAM[i % 3]: [1]}}
    if events:
        e = lambda k: (end + timedelta(days=k)).isoformat() + "T09:00:00"  # noqa: E731
        d["events"] = [
            {"id": 1, "category": "WORKOUT", "start_date_local": e(1), "icu_training_load": 70, "name": "geplant"},
            {"id": 2, "category": "WORKOUT", "start_date_local": e(2), "icu_training_load": 0, "name": "ohne Last"},
            {"id": 3, "category": "WORKOUT", "start_date_local": e(3), "icu_training_load": 40, "name": "gepaart",
             "paired_activity_id": "i99"},
            {"id": 4, "category": "WORKOUT", "start_date_local": e(0), "icu_training_load": 55, "name": "heute"},
            {"id": 5, "category": "NOTE", "start_date_local": e(4), "icu_training_load": 30, "name": "Notiz"},
            {"id": 6, "category": "WORKOUT", "start_date_local": e(9), "icu_training_load": 80, "name": "naechste Woche"},
            {"id": 7, "category": "WORKOUT", "start_date_local": e(20), "icu_training_load": 99, "name": "zu weit"},
        ]
    return d


_BD = _bl()
_BEV = _BD["events"]
_dl = {r["date"]: r["load"] for r in analytics.daily_load(_BD)}
_sum = lambda a, b: round(sum(v for k, v in _dl.items() if a <= k <= b), 1)  # noqa: E731

# --- a · load_budget(planned=None) bitgenau wie 0.73.4 ------------------------
_BUD_REF = [analytics.load_budget(_BD, s, t) for s in ("green", "amber", "red", "unknown")
            for t in ("2026-09-20", "2026-09-26", "2026-09-27", "2026-09-30")]
check("0.74.0 a bitgenau: load_budget ohne planned = Pruefsumme 0.73.4", _sha(_BUD_REF), "a14d78674c903d8a")
check("0.74.0 a bitgenau: planned=None ausdruecklich = ohne Parameter",
      [_try(analytics.load_budget, _BD, "green", t, planned=None) for t in ("2026-09-26", "2026-09-30")],
      [analytics.load_budget(_BD, "green", t) for t in ("2026-09-26", "2026-09-30")])
# --- a · planned zaehlt, als waere es gefahren --------------------------------
_p0 = analytics.load_budget(_BD, "green", "2026-09-27")
_p1 = _try(analytics.load_budget, _BD, "green", "2026-09-27", planned={"2026-09-27": 70.0})
check("0.74.0 a planned: geplante Last des Tages ist used_today", (_p1 or {}).get("used_today") if isinstance(_p1, dict) else _p1, 70.0)
check("0.74.0 a planned: window_load waechst um genau die geplante Last",
      round(_p1["window_load"] - _p0["window_load"], 1) if isinstance(_p1, dict) else _p1, 70.0)
check("0.74.0 a planned: window_load = sechs Tage davor + geplant (Known Answer)",
      _p1.get("window_load") if isinstance(_p1, dict) else _p1, round(_sum("2026-09-21", "2026-09-26") + 70.0, 1))
_p3 = _try(analytics.load_budget, _BD, "green", "2026-09-30", planned={})
check("0.74.0 a planned={}: die Reihe laeuft lueckenlos bis zum Tag (Fenster 24.-30.)",
      (_p3.get("window_start"), _p3.get("window_end"), _p3.get("window_load")) if isinstance(_p3, dict) else _p3,
      ("2026-09-24", "2026-09-30", _sum("2026-09-24", "2026-09-26")))
_ch = [(_dl.get((date(2026, 9, 2) + timedelta(days=k)).isoformat(), 0.0)) for k in range(28)]
check("0.74.0 a planned={}: der Schnitt nimmt die 28 Tage davor, kuenftige Tage mit 0",
      _p3.get("chronic") if isinstance(_p3, dict) else _p3, round(sum(_ch) / 28, 1))
_kurz74 = _bl(n=20)
check("0.74.0 a Randfall unter 28 Tagen: auch mit planned kein Budget",
      _try(analytics.load_budget, _kurz74, "green", "2026-10-05", planned={"2026-09-27": 500.0}), None)

# --- b · sessions_between; window_sessions bitgenau ----------------------------
_WS_REF = [analytics.window_sessions(_BD, t, _BEV) for t in ("2026-09-20", "2026-09-26", "2026-09-27", "2026-10-01")] \
    + [analytics.window_sessions(_bl(n=20), "2026-09-26", []), analytics.window_sessions({"wellness": {}}, "2026-09-26")]
check("0.74.0 b bitgenau: window_sessions = Pruefsumme 0.73.4", _sha(_WS_REF), "9ba11225d5fd4471")
_sb = getattr(analytics, "sessions_between", None)
check("0.74.0 b: analytics.sessions_between existiert", callable(_sb), True)
if callable(_sb):
    _w26 = analytics.window_sessions(_BD, "2026-09-26", _BEV)
    check("0.74.0 b: window_sessions = start/end + sessions_between (eine Stelle)",
          {k: v for k, v in _w26.items() if k not in ("start", "end")}, _sb(_BD, "2026-09-20", "2026-09-26", _BEV))
    _wsrc = (COMP / "analytics.py").read_text(encoding="utf-8")
    _wbody = _wsrc[_wsrc.index("def window_sessions("):]
    _wbody = _wbody[:_wbody.index("\ndef ", 10)]
    check("0.74.0 b AST: window_sessions ruft sessions_between und rechnet keine Gruppen selbst",
          ("sessions_between(" in _wbody, "activity_family(" in _wbody), (True, False))

# --- c · weeks_by_group --------------------------------------------------------
_wbg = getattr(analytics, "weeks_by_group", None)
check("0.74.0 c: analytics.weeks_by_group existiert", callable(_wbg), True)
if callable(_wbg):
    _W = _wbg(_BD, _BEV, "2026-09-26")
    check("0.74.0 c: 12 Kalenderwochen, Montag bis Sonntag, laufende zuletzt",
          (len(_W), _W[-1]["week"], _W[-1]["start"], _W[-1]["end"], _W[0]["start"]),
          (12, "2026-W39", "2026-09-21", "2026-09-27", "2026-07-06"))
    _mono = {w["week"]: w["monotony"] for w in analytics.weekly_summary(_BD)}
    check("0.74.0 c: Monotonie aus weekly_summary (ein Erzeuger)",
          [w["monotony"] for w in _W], [_mono.get(w["week"]) for w in _W])
    _bad = []
    for w in _W:
        end_ = min(w["end"], "2026-09-26")
        if round(sum(w["groups"].values()), 1) != _sum(w["start"], end_) or w["total"] != _sum(w["start"], end_):
            _bad.append(w["week"])
    check("0.74.0 c: Summe der Gruppen = Summe daily_load je Woche (Rest in none)", _bad, [])
    check("0.74.0 c: Fixture hat Rest (Tageslast > Fahrt) in den Wochen", any(w["groups"]["none"] > 0 for w in _W), True)
    check("0.74.0 c: Gruppenschluessel", sorted(_W[-1]["groups"]), sorted(["grundlage", "schwelle", "vo2max", "other", "none"]))
    check("0.74.0 c: Laufen landet unter other", sum(w["groups"]["other"] for w in _W) > 0, True)
    check("0.74.0 c: geplant nur laufende Woche, nur nach heute, WORKOUT, Last > 0, ungepaart (70)",
          [w["planned"] for w in _W], [0.0] * 11 + [70.0])
    check("0.74.0 c: gefahrene Summe laufende Woche ohne das geplante",
          _W[-1]["total"], _sum("2026-09-21", "2026-09-26"))
    check("0.74.0 c: laufende Woche benannt", [w["current"] for w in _W], [False] * 11 + [True])
    # gleiche Gruppen wie die Heute-Liste (window_sessions), wo die Tage sich decken
    _gl = analytics.window_sessions(_BD, "2026-09-26", _BEV)
    _sb21 = _sb(_BD, "2026-09-21", "2026-09-26", _BEV)
    _sbw = sum(x["load"] for x in _gl["sessions"] if x["date"] >= "2026-09-21")
    check("0.74.0 c/§5: Summe KW laufend = Summe Heute-Liste ab Montag", _W[-1]["total"], round(_sbw, 1))
    check("0.74.0 c: laufende Woche = sessions_between(Montag, heute)", _W[-1]["groups"], _sb21["groups"])
    # Randfall: Fahrten aelter als 30 Tage - Paarung ohne Event -> nur ueber Marken
    _alt = [x for x in _sb(_BD, "2026-07-18", "2026-08-06", _BEV)["sessions"] if not x["rest"]]
    check("0.74.0 §4 alte gepaarte Fahrt ohne Event: mit Marke zugeordnet, ohne Marke keine Gruppe",
          (any(x["source"] == "marks" for x in _alt), any(x["source"] is None and x["group"] is None for x in _alt)),
          (True, True))
    check("0.74.0 §4 alte gepaarte Fahrt ohne Event: nie source=plan", [x for x in _alt if x["source"] == "plan"], [])
    # Randfall: keine Events
    _W0 = _wbg(_BD, [], "2026-09-26")
    check("0.74.0 §4 keine Events: nichts geplant, gefahren unveraendert",
          ([w["planned"] for w in _W0][-1], _W0[-1]["total"]), (0.0, _W[-1]["total"]))
    # Randfall: Tageslast > Fahrten -> Rest in none; Tageslast < Fahrten -> benannt
    _mmx = _bl(); _mmx["wellness"]["2026-09-24"]["ctlLoad"] = 1.0
    _Wm = _wbg(_mmx, _BEV, "2026-09-26")
    check("0.74.0 §4 Tageslast < Fahrten: Tag benannt, nichts versteckt", _Wm[-1]["mismatch"], ["2026-09-24"])
    # Randfall: zweiter Athlet ohne Marken und Events
    _Bb = _bl(marks=False, events=False)
    _Wb = _wbg(_Bb, _Bb["events"], "2026-09-26")
    check("0.74.0 §4 zweiter Athlet: keine Marke -> Rad nur none, Lauf other, nichts geplant",
          (sum(w["groups"]["grundlage"] + w["groups"]["schwelle"] + w["groups"]["vo2max"] for w in _Wb),
           sum(w["planned"] for w in _Wb)), (0.0, 0.0))
    # Randfall: Jahreswechsel, ISO-Woche 53 (2026 hat 53 Wochen)
    _J = _bl(n=70, end=date(2027, 1, 2))
    _WJ = _wbg(_J, [], "2027-01-02")
    check("0.74.0 §4 Jahreswechsel: KW 53 von 2026, Montag 28.12.", (_WJ[-1]["week"], _WJ[-1]["start"], _WJ[-2]["week"]),
          ("2026-W53", "2026-12-28", "2026-W52"))
    _J2 = _wbg(_bl(n=70, end=date(2027, 1, 5)), [], "2027-01-05")
    check("0.74.0 §4 Jahreswechsel: KW 1 von 2027 nach KW 53", (_J2[-1]["week"], _J2[-2]["week"]), ("2027-W01", "2026-W53"))
    _M = _wbg(_bl(n=70, end=date(2026, 10, 2)), [], "2026-10-02")
    check("0.74.0 §4 Monatswechsel: Woche 28.09.-04.10. eine Woche", (_M[-1]["start"], _M[-1]["end"]), ("2026-09-28", "2026-10-04"))

# --- d · window_history --------------------------------------------------------
_wh = getattr(analytics, "window_history", None)
check("0.74.0 d: analytics.window_history existiert", callable(_wh), True)
_LBD = {d: "green" for d in _dl}
_LBD["2026-09-20"] = "amber"; _LBD["2026-09-21"] = "red"; del _LBD["2026-09-22"]
if callable(_wh):
    _H = _wh(_BD, _LBD, 60)
    check("0.74.0 d: 60 Tage bis heute", (len(_H), _H[0]["date"], _H[-1]["date"]), (60, "2026-07-29", "2026-09-26"))
    _diff = [h["date"] for h in _H
             if (lambda b: (h["window_load"], h["window_allowed"]) != (b["window_load"], b["window_allowed"]))(
                 analytics.load_budget(_BD, _LBD.get(h["date"], "unknown"), h["date"]))]
    check("0.74.0 d: je Tag window_load/allowed aus load_budget(Licht des Tages)", _diff, [])
    _hd = {h["date"]: h for h in _H}
    _c20 = analytics.load_budget(_BD, "green", "2026-09-20")["chronic"]
    check("0.74.0 d/f: Faktor je Tag (gelb 1,0 / rot 0,8 / fehlt -> unknown 1,0)",
          [_hd[x]["window_allowed"] for x in ("2026-09-20", "2026-09-21", "2026-09-22")],
          [analytics.load_budget(_BD, s, x)["window_allowed"] for s, x in
           (("amber", "2026-09-20"), ("red", "2026-09-21"), ("unknown", "2026-09-22"))])
    check("0.74.0 d: heute = Last bis heute Abend (7 Tage bis Ende heute)",
          _hd["2026-09-26"]["window_load"], _sum("2026-09-20", "2026-09-26"))
    check("0.74.0 d: over = Last ueber dem Ziel", [h["over"] for h in _H],
          [h["window_load"] > h["window_allowed"] for h in _H])
    check("0.74.0 d: Fixture hat Tage ueber und unter dem Ziel", ({h["over"] for h in _H}), {True, False})
    _Hk = _wh(_bl(n=20), {}, 60)
    check("0.74.0 §4 unter 28 Tagen: kein Ziel, nur die Last-Linie",
          (len(_Hk), {h["window_allowed"] for h in _Hk}, {h["over"] for h in _Hk}), (20, {None}, {False}))
    _k20 = _bl(n=20); _kd = {r["date"]: r["load"] for r in analytics.daily_load(_k20)}
    check("0.74.0 §4 unter 28 Tagen: Last = Summe der 7 Tage bis Tagesende",
          _Hk[-1]["window_load"], round(sum(v for k, v in _kd.items() if "2026-09-20" <= k <= "2026-09-26"), 1))

# --- e · window_projection ------------------------------------------------------
_wp = getattr(analytics, "window_projection", None)
_PL = _try(getattr(analytics, "planned_loads", lambda *a: "FEHLT"), _BEV, "2026-09-26", "2026-10-10")
check("0.74.0 g: planned_loads nimmt nur WORKOUT, > heute, Last > 0, ungepaart, bis zum Ende",
      _PL, {"2026-09-27": 70.0, "2026-10-05": 80.0})
# 0.74.1 B6: ein verborgenes Event (hide_from_athlete) zaehlt nicht - wie in _day_planned
_BEVh = list(_BEV) + [{"id": 99, "category": "WORKOUT", "start_date_local": "2026-09-29T09:00:00",
                       "icu_training_load": 55, "name": "verborgen", "hide_from_athlete": True},
                      {"id": 98, "category": "WORKOUT", "start_date_local": "2026-09-30T09:00:00",
                       "icu_training_load": 33, "name": "sichtbar", "hide_from_athlete": False}]
check("0.74.1 B6: planned_loads zaehlt ein verborgenes Event nicht, ein sichtbares schon",
      _try(analytics.planned_loads, _BEVh, "2026-09-26", "2026-10-10"),
      {"2026-09-27": 70.0, "2026-09-30": 33.0, "2026-10-05": 80.0})
check("0.74.1 B6: _day_planned und planned_loads filtern gleich",
      sorted(d for d in analytics._day_planned(_BEVh) if "2026-09-26" < d <= "2026-10-10"
             and any((x.get("load") or 0) > 0 and not x.get("done") for x in analytics._day_planned(_BEVh)[d])),
      sorted(analytics.planned_loads(_BEVh, "2026-09-26", "2026-10-10")))
check("0.74.0 e: analytics.window_projection existiert", callable(_wp), True)
if callable(_wp) and isinstance(_PL, dict):
    _P = _wp(_BD, "amber", _PL, 14)
    check("0.74.0 e: 14 Tage ab morgen", (len(_P), _P[0]["date"], _P[-1]["date"]), (14, "2026-09-27", "2026-10-10"))
    _pd = [p["date"] for p in _P if (lambda b: (p["window_load"], p["window_allowed"]) !=
           (b["window_load"], b["window_allowed"]))(analytics.load_budget(_BD, "amber", p["date"], planned=_PL))]
    check("0.74.0 e: je Tag aus load_budget(planned, Licht von heute)", _pd, [])
    _pp = {p["date"]: p for p in _P}
    check("0.74.0 e: geplante 70 am 27. in der Vorschau", _pp["2026-09-27"]["window_load"],
          round(_sum("2026-09-21", "2026-09-26") + 70.0, 1))
    check("0.74.0 e: am 03.10. nur noch 27.09. (70) im Fenster, sonst 0",
          _pp["2026-10-03"]["window_load"], 70.0)
    check("0.74.0 e: am 05.10. die 80 der naechsten Woche", _pp["2026-10-05"]["window_load"], 80.0)
    _P0 = _wp(_BD, "amber", {}, 14)
    check("0.74.0 §8 Gegenprobe planned: ohne Plan am 27. weniger um genau 70",
          round(_pp["2026-09-27"]["window_load"] - {p["date"]: p for p in _P0}["2026-09-27"]["window_load"], 1), 70.0)
    check("0.74.0 e: Ziel = Faktor von heute (gelb -> 7 x chronisch x 1,0)",
          _pp["2026-09-27"]["window_allowed"], analytics.load_budget(_BD, "amber", "2026-09-27", planned=_PL)["window_bands"]["steady"])
    check("0.74.0 §4 unter 28 Tagen: Vorschau ohne Ziel", {p["window_allowed"] for p in _wp(_bl(n=20), "green", {}, 14)}, {None})

# --- h · readiness: Akut zu chronisch aus load_budget ---------------------------
# heute ein grosser Tag: der alte Schnitt (inklusive heute) und der neue (vor heute) gehen auseinander
_BDh = _bl(); _BDh["wellness"]["2026-09-26"]["ctlLoad"] = 300.0
_rdy = analytics.readiness(_BDh)
_ac = next((c for c in _rdy["components"] if c["id"] == "acwr"), {})
_lb = analytics.load_budget(_BDh, "green", "2026-09-26")
_neu = round(_lb["window_load"] / (7 * _lb["chronic"]), 2)
# der alte Weg (acwr_series bis 0.74.0, Schnitt INKLUSIVE des Tages) nur noch hier als Vergleich
def _alt_ratio(data, day):
    rows = [r for r in analytics.daily_load(data) if r["date"] <= day]
    if len(rows) < 28:
        return None
    ld = [r["load"] for r in rows]
    c = sum(ld[-28:]) / 28
    return round((sum(ld[-7:]) / 7) / c, 2) if c else None
_alt = _alt_ratio(_BDh, "2026-09-26")
print(f"   0.74.0 h Beispielzahl: alt (Schnitt inkl. heute) {_alt} -> neu (load_budget, Schnitt vor heute) {_neu}")
check("0.74.0 h Fixture: alter und neuer Weg unterscheiden sich", _neu != _alt, True)
# --- 0.74.1 B4 · EINE Funktion fuer das Verhaeltnis ---------------------------------
_wr = getattr(analytics, "window_ratio", None)
check("0.74.1 B4: analytics.window_ratio existiert", callable(_wr), True)
if callable(_wr):
    check("0.74.1 B4: window_ratio = window_load / (7 x chronic) aus load_budget(day)", _wr(_BDh, "2026-09-26"), _neu)
    for _dd in ("2026-09-24", "2026-09-25", "2026-09-26"):
        _l = analytics.load_budget(_BDh, "green", _dd)
        check(f"0.74.1 B4: window_ratio am {_dd} aus load_budget(today={_dd})", _wr(_BDh, _dd),
              round(_l["window_load"] / (7 * _l["chronic"]), 2))
        print(f"   0.74.1 B4 Fixture {_dd}: alt {_alt_ratio(_BDh, _dd)} -> neu {_wr(_BDh, _dd)}")
    check("0.74.1 B4 unter 28 Tagen: None", _wr(_bl(n=20), "2026-09-26"), None)
    check("0.74.1 B4 Tag ohne Wellness-Reihe (leer): None", _wr({"wellness": {}, "activities": {}, "dfa": {}}, "2026-09-26"), None)
check("0.74.0 h: Akut zu chronisch = window_load / (7 x chronic) aus load_budget(heute)", _ac.get("value"), _neu)
check("0.74.0 h: Schwellen und Texte bleiben (Einstufung am neuen Wert: 1,51 > 1,5 -> rot)",
      (_ac.get("reference"), _ac.get("label"), _ac.get("state"), _ac.get("detail")),
      (analytics.ACWR_HIGH, "Akut zu chronisch", "red", "deutlich über dem Korridor"))
_rsrc = (COMP / "analytics.py").read_text(encoding="utf-8")
_rbody = _rsrc[_rsrc.index("def readiness("):]
_rbody = _rbody[:_rbody.index("\ndef ", 10)]
check("0.74.0 h AST: readiness ruft acwr_series nicht mehr, load_budget genau einmal",
      ("acwr_series(" in _rbody, _rbody.count("load_budget(") + _rbody.count("window_ratio(")), (False, 1))
check("0.74.1 B4 AST: readiness nimmt das Verhaeltnis aus window_ratio, nicht selbst aus load_budget",
      (_rbody.count("window_ratio("), _rbody.count("load_budget(")), (1, 0))
check("0.74.0 h Randfall unter 28 Tagen: kein Punkt", [c["id"] for c in analytics.readiness(_bl(n=20))["components"]].count("acwr"), 0)

# --- i · summary ohne ACWR-Felder -------------------------------------------------
_sm = analytics.summary(_BD)
check("0.74.0 i: summary ohne acwr, acwr_latest", ("acwr" in _sm, "acwr_latest" in _sm), (False, False))
check("0.74.0 i: thresholds ohne acwr_*", sorted(k for k in _sm["thresholds"] if k.startswith("acwr")), [])
check("0.74.0 i: der Rest der Payload bleibt",
      sorted(_sm), sorted(["weeks", "ramp_rate", "form", "form_percent", "form_zone", "intensity",
                           "dfa_distribution", "decoupling", "hrv", "thresholds"]))
check("0.74.1 B4: acwr_series ist entfernt", hasattr(analytics, "acwr_series"), False)
check("0.74.1 B4: acwr_series kommt im Paket nicht mehr vor",
      sorted(f.name for f in COMP.rglob("*.py") if "acwr_series" in f.read_text(encoding="utf-8")), [])

print(f"test_analytics: {CHECKS} Prüfungen, {len(failures)} Fehler")
print("FEHLER:", failures if failures else "keine")
sys.exit(1 if failures else 0)
