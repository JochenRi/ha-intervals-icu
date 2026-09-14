"""Checks for the training analytics, with known-answer tests where possible."""

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
acwr = analytics.acwr_series(steady)
check("vor 28 Tagen kein Verhaeltnis", acwr[26]["ratio"], None)
check("gleichmaessige Last ergibt 1.0", acwr[-1]["ratio"], 1.0)

spike = dict(steady["wellness"])
for index in range(33, 40):
    spike[(start + timedelta(days=index)).isoformat()] = {"ctlLoad": 150.0}
jump = analytics.acwr_series({"wellness": spike, "activities": {}, "dfa": {}})
check("Belastungssprung hebt das Verhaeltnis ueber die Risikoschwelle",
      jump[-1]["ratio"] > analytics.ACWR_RISK, True)

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
hrv_days = {}
for index in range(90):
    day = (today - timedelta(days=89 - index)).isoformat()
    hrv_days[day] = {"hrv": 50.0}
status = analytics.hrv_status({"wellness": hrv_days, "activities": {}, "dfa": {}})
check("stabile HRV gilt als normal", status["state"], "normal")
check("SWC bei konstanter HRV ist null", status["swc"], 0.0)

for index in range(80, 90):
    day = (today - timedelta(days=89 - index)).isoformat()
    hrv_days[day] = {"hrv": 30.0}
dropped = analytics.hrv_status({"wellness": hrv_days, "activities": {}, "dfa": {}})
check("HRV-Einbruch wird erkannt", dropped["state"], "below")
check("Hinweis zur Messmethode mitgeliefert", "overnight" in dropped["note"], True)
check("zu wenig Daten ergibt nichts",
      analytics.hrv_status({"wellness": {"2026-01-01": {"hrv": 50}}, "activities": {}, "dfa": {}}), None)

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
budget = good["budget"]
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
check("Budget schrumpft mit der Ampel",
      alarm["budget"]["recommended"] < good["budget"]["recommended"], True)

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
check("Wochenlast summiert", woche["load"], 83)
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
# ACWR, Monotonie, Lastbudget, daily_load UND in analytics' eigener
# HRV-Rechnung dasselbe ergeben — analytics bleibt komplett kontextfrei,
# die Herkunftsnotiz dazu hängt die Websocket-Schicht an (siehe ausbau.md B3;
# die saubere Lösung der Ampel-Divergenz heißt B4).
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

for _name in ("daily_load", "weekly_summary", "acwr_series", "hrv_status",
              "readiness"):
    _fn = getattr(analytics, _name)
    check(f"Ebene 3: {_name} ignoriert Etiketten",
          _json.dumps(_fn(_lvl3), sort_keys=True, default=str)
          == _json.dumps(_fn(_lvl3_ctx), sort_keys=True, default=str), True)
check("Ebene 3: load_budget ignoriert Etiketten",
      analytics.load_budget(_lvl3, "green") == analytics.load_budget(_lvl3_ctx, "green"), True)

# Quelltext-Wächter: die Mauer steht im Code, nicht in der Absicht.
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

print(f"test_analytics: {CHECKS} Prüfungen, {len(failures)} Fehler")
print("FEHLER:", failures if failures else "keine")
sys.exit(1 if failures else 0)
