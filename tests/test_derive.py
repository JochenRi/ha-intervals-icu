"""Simulation against recorded live payloads. Run: python3 tests/test_derive.py"""

import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"))

import derive  # noqa: E402
from fixtures import ATHLETE, EVENTS, WELLNESS  # noqa: E402

failures = []


def check(label, got, expected):
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

print()
print("FEHLER:", failures if failures else "keine")
sys.exit(1 if failures else 0)
