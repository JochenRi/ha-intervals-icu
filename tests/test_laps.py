"""Laps: the API field names are undocumented, so the normaliser has to
degrade to a missing value instead of an exception whatever it is handed.

Every case below is a payload shape the account could plausibly return, plus
the ones that are simply broken. No Home Assistant instance required.
"""

import sys
from pathlib import Path

import coldcache  # noqa: F401,E402  - MUSS vor jedem Bauteil-Import stehen (§9)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"))

import derive  # noqa: E402

FAILURES: list[str] = []
CHECKS = 0


def check(condition: bool, label: str) -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILURES.append(label)


def eq(got, want, label: str) -> None:
    check(got == want, f"{label}: {got!r} statt {want!r}")


# --- the documented shape (intervals=true on the activity) -----------------
payload = {
    "id": "i181999211",
    "icu_intervals": [
        {"label": "Aufwärmen", "moving_time": 989, "average_watts": 118,
         "average_heartrate": 123, "average_cadence": 76, "zone": "Z1",
         "average_dfa_a1": 1.44, "distance": 5200},
        {"label": "4x", "moving_time": 237, "average_watts": 259,
         "weighted_average_watts": 261, "average_heartrate": 170, "zone": "Z5",
         "average_dfa_a1": 0.85, "icu_training_load": 18},
    ],
}
out = derive.normalize_laps(payload)
eq(out["source"], "icu_intervals", "Quelle")
eq(len(out["laps"]), 2, "Anzahl")
eq(out["laps"][0]["n"], 1, "Nummerierung beginnt bei 1")
eq(out["laps"][1]["avg_watts"], 259, "Watt")
eq(out["laps"][1]["np_watts"], 261, "normalisierte Watt")
eq(out["laps"][1]["avg_hr"], 170, "Herzfrequenz")
eq(out["laps"][1]["dfa_a1"], 0.85, "DFA")
eq(out["laps"][1]["zone"], "Z5", "Zone")
eq(out["laps"][1]["load"], 18, "Last")
check("label" in out["seen_keys"] and "average_watts" in out["seen_keys"],
      "gesehene Schlüssel werden nicht gemeldet")

# efficiency factor is derived when the API does not send it: watts per beat
eq(out["laps"][1]["ef"], round(261 / 170, 2), "EF aus NP abgeleitet")
eq(out["laps"][0]["ef"], round(118 / 123, 2), "EF aus Ø-Watt abgeleitet")

# an EF sent by the API wins over the derived one
sent = derive.normalize_laps({"icu_intervals": [
    {"average_watts": 200, "average_heartrate": 100, "efficiency_factor": 1.93}]})
eq(sent["laps"][0]["ef"], 1.93, "gesendeter EF wird überschrieben")

# --- alternative field names ----------------------------------------------
alt = derive.normalize_laps({"laps": [
    {"name": "Runde 1", "elapsed_time": 600, "icu_average_watts": 118,
     "avg_hr": 123, "icu_efficiency_factor": 0.96, "hr_pw_decoupling": 4.1}]})
eq(alt["source"], "laps", "alternative Liste")
eq(alt["laps"][0]["label"], "Runde 1", "alternativer Name")
eq(alt["laps"][0]["moving_time"], 600, "alternative Dauer")
eq(alt["laps"][0]["decoupling"], 4.1, "alternative Entkopplung")

# --- broken and empty payloads --------------------------------------------
for label, value in [
    ("None", None),
    ("Liste statt Objekt", [1, 2, 3]),
    ("Text", "kaputt"),
    ("leeres Objekt", {}),
    ("leere Liste", {"icu_intervals": []}),
    ("Liste mit Müll", {"icu_intervals": ["x", 42, None]}),
]:
    result = derive.normalize_laps(value)
    check(isinstance(result, dict) and isinstance(result["laps"], list),
          f"{label}: keine brauchbare Antwort")
    check(result["laps"] == [], f"{label}: erfundene Runden")

# null values must not crash and must not invent an EF
nulls = derive.normalize_laps({"icu_intervals": [
    {"label": None, "moving_time": None, "average_watts": None, "average_heartrate": None}]})
eq(len(nulls["laps"]), 1, "Runde mit lauter Nullwerten verschwindet")
check("ef" not in nulls["laps"][0], "EF aus Nullwerten erfunden")

# division by zero, and text where numbers belong
zero = derive.normalize_laps({"icu_intervals": [{"average_watts": 200, "average_heartrate": 0}]})
check("ef" not in zero["laps"][0], "EF durch null geteilt")
text = derive.normalize_laps({"icu_intervals": [{"average_watts": "viel", "average_heartrate": "wenig"}]})
check("ef" not in text["laps"][0], "EF aus Text gerechnet")

# the first matching list wins, and the order of preference is stable
both = derive.normalize_laps({"laps": [{"name": "alt"}], "icu_intervals": [{"label": "neu"}]})
eq(both["source"], "icu_intervals", "Reihenfolge der Kandidatenlisten")

print(f"test_laps: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
sys.exit(1 if FAILURES else 0)
