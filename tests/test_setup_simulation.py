"""Simulate the entity setup without Home Assistant.

Reads the sensor descriptions straight out of sensor.py (via AST, so no HA
imports are needed), applies them to the recorded live payloads and checks:

* which entities would be created and which of them enabled
* that every translation_key exists in all translation files
* that no two entities would share a unique_id
"""

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "custom_components" / "intervals_icu"
import coldcache  # noqa: F401,E402  - MUSS vor jedem Bauteil-Import stehen (§9)
sys.path.insert(0, str(COMP))

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


# --- pull the descriptions out of sensor.py ----------------------------------
tree = ast.parse((COMP / "sensor.py").read_text())
descriptions = []
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "WellnessSensorDescription":
        kwargs = {kw.arg: kw.value for kw in node.keywords}
        descriptions.append(
            {
                "key": ast.literal_eval(kwargs["key"]),
                "field": ast.literal_eval(kwargs["field"]),
                "translation_key": ast.literal_eval(kwargs["translation_key"]),
            }
        )

check("Anzahl Wellness-Sensoren", len(descriptions), 28)

available = derive.available_keys(WELLNESS)
enabled = [d["key"] for d in descriptions if d["field"] in available]
disabled = [d["key"] for d in descriptions if d["field"] not in available]

print("\n  aktiv:    " + ", ".join(sorted(enabled)))
print("  inaktiv:  " + ", ".join(sorted(disabled)) + "\n")

check("aktive Wellness-Sensoren", len(enabled), 11)
check("Gewicht deaktiviert", "weight" in disabled, True)
check("SpO2 deaktiviert", "spo2" in disabled, True)
check("VO2max aktiv", "vo2max" in enabled, True)
check("HRV aktiv", "hrv" in enabled, True)

# --- sport entities -----------------------------------------------------------
settings = derive.sport_settings(ATHLETE)
sport_entities = []
for setting in settings:
    label = derive.sport_label(setting)
    for field in ("ftp", "lthr", "max_hr"):
        sport_entities.append((label, field, setting.get(field) is not None))
check("Sport-Schwellensensoren", len(sport_entities), 12)
check("davon aktiv (FTP nur bei Ride gesetzt)", sum(1 for _, _, e in sport_entities if e), 9)
check("FTP Run deaktiviert", ("Run", "ftp", False) in sport_entities, True)

estimates = [(label, f) for label in derive.sport_info(WELLNESS) for f in ("eftp", "wPrime", "pMax")]
check("Schaetzwert-Sensoren (nur Sportarten mit Daten)", len(estimates), 3)

# --- unique_id collisions ------------------------------------------------------
athlete = ATHLETE["id"]
uids = [f"{athlete}_{d['key']}" for d in descriptions]
uids.append(f"{athlete}_form")
uids += [f"{athlete}_{label.lower()}_{field.lower()}" for label, field, _ in sport_entities]
uids += [f"{athlete}_{label.lower()}_{field.lower()}" for label, field in estimates]
uids += [f"{athlete}_next_workout", f"{athlete}_next_workout_date",
         f"{athlete}_next_workout_load", f"{athlete}_calendar", f"{athlete}_archive"]
check("unique_ids kollisionsfrei", len(uids), len(set(uids)))
check("Entities gesamt", len(uids), 49)

# --- translations --------------------------------------------------------------
needed = {d["translation_key"] for d in descriptions} | {
    "form", "next_workout", "next_workout_date", "next_workout_load", "archive"
}
for name in ("strings.json", "translations/en.json", "translations/de.json"):
    doc = json.loads((COMP / name).read_text())
    have = set(doc.get("entity", {}).get("sensor", {}))
    check(f"{name}: alle Namen vorhanden", sorted(needed - have), [])
    check(f"{name}: keine ueberfluessigen", sorted(have - needed), [])
    check(f"{name}: Kalendername", "planned" in doc.get("entity", {}).get("calendar", {}), True)

# --- regression guard: methods must not shadow base-class attributes ----------
# 0.2.0 shipped a sensor with a method named _entry() while the base class
# stored the config entry in self._entry - the attribute won every time and
# every wellness sensor died with "ConfigEntry object is not callable".
base = ast.parse((COMP / "entity.py").read_text())
base_attrs = {
    t.attr
    for node in ast.walk(base)
    if isinstance(node, ast.Assign)
    for t in node.targets
    if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self"
}
clashes = []
for name in ("sensor.py", "calendar.py"):
    module = ast.parse((COMP / name).read_text())
    for node in ast.walk(module):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in base_attrs:
            clashes.append(f"{name}:{node.name}")
check("keine Methode ueberschreibt ein Basis-Attribut", clashes, [])

print()
print(f"test_setup_simulation: {CHECKS} Prüfungen, {len(failures)} Fehler")
print("FEHLER:", failures if failures else "keine")
sys.exit(1 if failures else 0)
