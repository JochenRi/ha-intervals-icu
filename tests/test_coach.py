"""The coach, rule by rule, against the case each rule exists for.

The dangerous failure here is not a crash - it is a confident recommendation
built on a misread state. So every state gets a synthetic history that can
only mean one thing, and the assertions check the decision, not the wording.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"))

import coach  # noqa: E402

FAILURES: list[str] = []
CHECKS = 0


def check(condition: bool, label: str) -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILURES.append(label)


def eq(got, want, label: str) -> None:
    check(got == want, f"{label}: {got!r} statt {want!r}")


TODAY = date(2026, 9, 11)


def build(days=120, hrv=50.0, rhr=56.0, noise=True, activities=None, overrides=None):
    """A plain, healthy history: stable HRV and resting HR, a ride every third day."""
    wellness = {}
    for index in range(days):
        day = (TODAY - timedelta(days=days - 1 - index)).isoformat()
        wobble = ((index * 7) % 5 - 2) * (1.0 if noise else 0.0)
        wellness[day] = {"id": day, "hrv": hrv + wobble, "restingHR": rhr - wobble * 0.2,
                         "sleepSecs": 7.5 * 3600, "ctl": 30, "atl": 28, "form": 2}
    for day, patch in (overrides or {}).items():
        wellness.setdefault(day, {"id": day}).update(patch)
    acts = {}
    for index in range(0, days, 3):
        day = (TODAY - timedelta(days=days - 1 - index)).isoformat()
        acts[f"a{index}"] = {"id": f"a{index}", "start_date_local": day + "T09:00:00",
                             "type": "Ride", "moving_time": 4500, "icu_intensity": 62,
                             "icu_training_load": 60, "decoupling": 1.5,
                             "average_heartrate": 140, "icu_average_watts": 135}
    if activities is not None:
        acts = activities
    dfa = {key: {"hr_at_threshold": 157, "power_at_threshold": 158, "threshold_samples": 40,
                 "samples": 2000}
           for key in list(acts)[:12]}
    return {"wellness": wellness, "activities": acts, "dfa": dfa}


def day(offset: int) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


# --- 1  a healthy history reads as ready --------------------------------------
data = build()
st = coach.state(data)
eq(st["state"], "ready", "1 normalzustand")
check(st["week_z"] is not None, "1 normalzustand: kein Vergleichswert")
rec = coach.recommend(data)
check(rec["key"] in ("sweetspot", "endurance"), f"1 empfehlung unerwartet: {rec['key']}")

# --- 2  an acute slump today is a slump, not "strained" -----------------------
slump = build(overrides={day(0): {"hrv": 30.0, "restingHR": 66.0}})
st = coach.state(slump)
eq(st["state"], "slump", "2 einbruch")
eq(st["since"], day(0), "2 einbruch: falscher Tag")
eq(coach.recommend(slump)["key"], "rest", "2 einbruch: Empfehlung")

# --- 3  Johannes' actual case: slump five days ago, values back ---------------
# This is the case the old traffic light got wrong: the 7-day mean still
# carries the slump, so it says red while the body is already back.
infekt = build(overrides={
    day(-6): {"hrv": 35.0, "restingHR": 61.0},
    day(-5): {"hrv": 30.0, "restingHR": 66.0},
    day(-4): {"hrv": 31.0, "restingHR": 54.0},
    day(-3): {"hrv": 55.0, "restingHR": 53.0},
    day(-2): {"hrv": 44.0, "restingHR": 57.0},
    day(-1): {"hrv": 63.0, "restingHR": 50.0},
    day(0): {"hrv": 63.0, "restingHR": 51.0},
})
st = coach.state(infekt)
eq(st["state"], "rebound", "3 erholung nach einbruch")
check(st["week_z"] is not None and st["week_z"] < 0,
      "3 erholung: das 7-Tage-Mittel müsste noch unter der Basislinie liegen")
check(st["recent_hrv_z"] is not None and st["recent_hrv_z"] > 0,
      "3 erholung: die letzten Tage müssten über der Basislinie liegen")
check("hinkt noch nach" in st["detail"], "3 erholung: der Nachlauf wird nicht erklärt")

# --- 4  slump plus break -> graded return wins over the traffic light ---------
# The history deliberately contains earlier breaks, each followed by a HARD
# first session - that is the habit the real account shows (six breaks, median
# 85% intensity), and the coach has to mirror it back.
acts = {}
for index in range(0, 100, 3):
    d = (TODAY - timedelta(days=100 - index)).isoformat()
    if d > day(-6):          # nothing ridden since the infection began
        continue
    if index in (18, 19, 20, 21, 30, 31, 32, 33, 60, 61, 62, 63):   # three earlier breaks
        continue
    hard_restart = index in (24, 36, 66)            # the first ride after each break
    acts[f"a{index}"] = {"id": f"a{index}", "start_date_local": d + "T09:00:00", "type": "Ride",
                         "moving_time": 4500, "icu_intensity": 90 if hard_restart else 62,
                         "icu_training_load": 70, "average_heartrate": 150,
                         "icu_average_watts": 160, "decoupling": 2.0}
back = build(activities=acts, overrides={
    day(-6): {"hrv": 30.0, "restingHR": 66.0}, day(-1): {"hrv": 63.0, "restingHR": 50.0},
    day(0): {"hrv": 63.0, "restingHR": 51.0}})
rec = coach.recommend(back)
eq(rec["state"]["state"], "rebound", "4 wiedereinstieg: Zustand")
eq(rec["layoff"]["phase"], "wiedereinstieg", "4 wiedereinstieg: Phase")
check(rec["key"] in ("endurance", "recovery"),
      f"4 wiedereinstieg: empfiehlt {rec['key']} statt einer lockeren Einheit")
check(any("Infekt" in w or "stufenweise" in w for w in rec["warnings"]),
      "4 wiedereinstieg: kein Hinweis zur stufenweisen Rückkehr")
check(any("Muster" in w for w in rec["warnings"]),
      "4 wiedereinstieg: das eigene Einstiegsmuster wird nicht gespiegelt")
habit = coach.pattern_after_breaks(back)
check(habit is not None and habit["n"] >= 3, "4 muster: zu wenige Pausen erkannt")
check(habit["median_intensity"] >= 75, f"4 muster: Intensität falsch ({habit})")
# and the other direction: with too few breaks the coach must stay silent
few = {"activities": {k: v for k, v in list(back["activities"].items())[:6]}}
check(coach.pattern_after_breaks(few) is None,
      "4 muster: behauptet ein Muster aus zu wenigen Fällen")

# --- 5  two hard days in a week -> no third ----------------------------------
hard = {}
for index in range(0, 100, 3):
    d = (TODAY - timedelta(days=100 - index)).isoformat()
    hard[f"a{index}"] = {"id": f"a{index}", "start_date_local": d + "T09:00:00", "type": "Ride",
                         "moving_time": 4500, "icu_intensity": 62, "icu_training_load": 60,
                         "average_heartrate": 140, "icu_average_watts": 135, "decoupling": 1.0}
for offset, name in ((-1, "h1"), (-3, "h2")):
    hard[name] = {"id": name, "start_date_local": day(offset) + "T09:00:00", "type": "Ride",
                  "moving_time": 3600, "icu_intensity": 92, "icu_training_load": 90,
                  "average_heartrate": 165, "icu_average_watts": 210, "decoupling": 3.0}
rec = coach.recommend(build(activities=hard))
eq(rec["key"], "endurance", "5 zwei harte Tage: dritter harter Tag empfohlen")
check(any("Seiler" in r["quelle"] for r in rec["reasons"]), "5 zwei harte Tage: Begründung fehlt")

# --- 6  anchors come from measured DFA, not from a guess ---------------------
anc = coach.anchors(data)
eq(anc["aerobic_hr"], 157, "6 anker: Herzfrequenz")
eq(anc["aerobic_power"], 158, "6 anker: Leistung")
check("Rogers" in anc["source"], "6 anker: Quelle fehlt")
thin = build()
thin["dfa"] = {k: {"hr_at_threshold": 150, "threshold_samples": 2} for k in list(thin["activities"])[:5]}
check(coach.anchors(thin)["aerobic_hr"] is None, "6 anker: dünne Messungen zählen mit")

# --- 7  target windows are derived from those anchors ------------------------
rec = coach.recommend(data)
low, high = rec["hr_window"]
check(120 < low < high < 200, f"7 zielfenster unplausibel: {rec['hr_window']}")
check(rec["expected_dfa"], "7 kein erwarteter DFA-Bereich")
check(rec["effect"] and len(rec["effect"]) > 40, "7 keine Wirkungsbeschreibung")
easy = coach.recommend(slump)
eq(easy["hr_window"], None, "7 Ruhetag mit Zielpuls")

# --- 8  budget interaction ----------------------------------------------------
rec = coach.recommend(data, budget={"recommended": 20})
check(rec["fits_budget"] is False, "8 budget: zu große Einheit passt angeblich")
rec = coach.recommend(data, budget={"recommended": 500})
check(rec["fits_budget"] is True, "8 budget: passende Einheit passt angeblich nicht")
rec = coach.recommend(data, budget=None)
check(rec["fits_budget"] is None, "8 budget: erfundene Aussage ohne Budget")

# --- 9  durability from real decoupling --------------------------------------
dur = coach.durability(data)
check(dur is not None and dur["n"] >= 8, "9 durability: nicht berechnet")
check("Friel" in dur["source"], "9 durability: Quelle fehlt")
bad = build()
for a in bad["activities"].values():
    a["decoupling"] = 12.0
    a["moving_time"] = 7200
check("noch nicht" in coach.durability(bad)["verdict"], "9 durability: hohe Entkopplung gelobt")

# --- 10  thin and broken data must not produce confident advice --------------
for label, payload in (("leer", {}), ("nur wellness", {"wellness": build()["wellness"]}),
                       ("kurz", build(days=10)), ("None-Felder", {"wellness": None, "activities": None})):
    st = coach.state(payload)
    check(isinstance(st, dict) and "state" in st, f"10 {label}: kein Zustand")
    out = coach.coach(payload)
    check(isinstance(out["recommendation"], dict), f"10 {label}: keine Empfehlung")
    check(isinstance(out["plan"], list), f"10 {label}: kein Plan")
eq(coach.state(build(days=10))["state"], "unknown", "10 kurze Historie: behauptet einen Zustand")
check(coach.state(build(days=10))["confidence"] == "keine", "10 kurze Historie: Vertrauen behauptet")

# --- 11  the plan separates hard days ----------------------------------------
week = coach.plan(data)
eq(len(week), 7, "11 plan: falsche Länge")
keys = [entry["key"] for entry in week]
for index in range(1, len(keys)):
    if keys[index] in ("sweetspot", "vo2max"):
        check(keys[index - 1] not in ("sweetspot", "vo2max"),
              f"11 plan: zwei harte Tage hintereinander an Position {index}")
easy_share = sum(1 for k in keys if k in ("recovery", "endurance", "rest")) / len(keys)
check(easy_share >= 0.6, f"11 plan: nur {easy_share:.0%} lockere Einheiten - Seiler verletzt")
check(all(entry["date"] for entry in week), "11 plan: Einträge ohne Datum")

# --- 12  the payload carries its own limits ----------------------------------
full = coach.coach(data)
check("Düking" in full["evidence"]["limit"], "12 belege: die Metaanalyse fehlt")
check("Javaloyes" in full["evidence"]["rule"], "12 belege: die Regel ist nicht benannt")
check(len(full["sessions"]) >= 5, "12 belege: Einheitenkatalog unvollständig")
for key, session in full["sessions"].items():
    check(bool(session["effect"]), f"12 katalog: {key} ohne Wirkungsbeschreibung")

# --- 13  the signal matrix ----------------------------------------------------
sig = coach.signals(infekt, 90)
check(len(sig["days"]) > 60, "13 signale: zu wenige Tage")
row = sig["days"][-1]
check("hrv" in row["z"] and "rhr" in row["z"], "13 signale: z-Werte fehlen")
check("hrv" in row["raw"], "13 signale: Rohwerte fehlen")
check(abs(row["z"]["hrv"]) < 6, f"13 signale: unplausibler z-Wert {row['z']}")
# a lower resting heart rate has to read as BETTER, so the sign is flipped
low = coach.signals(build(overrides={day(0): {"restingHR": 45.0}}), 60)["days"][-1]
high = coach.signals(build(overrides={day(0): {"restingHR": 67.0}}), 60)["days"][-1]
check(low["z"]["rhr"] > high["z"]["rhr"], "13 signale: Ruhepuls nicht gespiegelt")

# --- 14  bands and trainer must never disagree --------------------------------
# The chart paints the background from state_series, the trainer view from
# state(). If those two use different rules the picture contradicts the text.
for label, payload in (("infekt", infekt), ("normal", data), ("einbruch", slump)):
    banded = coach.signals(payload, 120)["days"]
    eq(banded[-1]["state"], coach.state(payload)["state"], f"14 {label}: Band widerspricht dem Trainer")

series = coach.state_series(infekt)
states_seen = [row["state"] for row in series[-8:]]
check("slump" in states_seen, f"14 verlauf: kein Einbruch erkannt ({states_seen})")
check(states_seen[-1] == "rebound", f"14 verlauf: endet nicht in Erholung ({states_seen})")
check(states_seen.index("slump") < len(states_seen) - 1, "14 verlauf: Einbruch am Ende statt davor")

# --- 15  sessions carry their DFA band split ----------------------------------
withdfa = build()
for key in withdfa["activities"]:
    withdfa["dfa"][key] = {"secs_aerobic": 3000, "secs_transition": 400,
                           "secs_anaerobic": 200, "hr_at_threshold": 157,
                           "power_at_threshold": 158, "threshold_samples": 40}
rows = [r for r in coach.signals(withdfa, 60)["days"] if r["activities"]]
check(rows, "15 einheiten: keine im Fenster")
bands = rows[-1]["activities"][0]["dfa_bands"]
check(bands and sum(bands) in (99, 100, 101), f"15 einheiten: DFA-Anteile summieren nicht ({bands})")
nodfa = coach.signals(build(), 60)["days"]
sess = [r for r in nodfa if r["activities"]]
check(sess and sess[-1]["activities"][0]["dfa_bands"] is None,
      "15 einheiten: DFA-Anteile erfunden, wo keine Auswertung vorliegt")

# --- 16  every signal ships its source and how to read it ---------------------
for key, meta in sig["signals"].items():
    check(bool(meta.get("read")), f"16 erklärung: {key} ohne Lesehilfe")
    check(bool(meta.get("source")), f"16 erklärung: {key} ohne Quelle")
    check(bool(meta.get("label")), f"16 erklärung: {key} ohne Bezeichnung")
check("Gabbett" in sig["load_signals"]["acwr"]["source"], "16 erklärung: ACWR ohne Quelle")
check(sig["swc"] == 0.5, "16 erklärung: kleinste bedeutsame Änderung fehlt")

# --- 17  thin data must not produce bands --------------------------------------
for label, payload in (("leer", {}), ("kurz", build(days=12)), ("kaputt", {"wellness": None})):
    out = coach.signals(payload, 90)
    check(isinstance(out["days"], list), f"17 {label}: keine Tagesliste")
    check(all(isinstance(r.get("z"), dict) for r in out["days"]), f"17 {label}: kaputte Zeile")

# --- 18  the night after a session --------------------------------------------
# The point of this reading: a night can look bad in absolute terms and be
# entirely ordinary for THIS athlete after THIS kind of session. The relation
# between load and HRV change is bell-shaped, so an absolute threshold would
# raise a false alarm after every hard ride.
import random as _random


def night_history(damp=7.0, last_damp=None, days=200):
    """A history where every hard session is followed by a damped night."""
    _random.seed(11)
    wellness, activities = {}, {}
    for index in range(days):
        iso = day(-(days - 1 - index))   # day() adds, so past days are negative
        hard = index % 7 == 2
        prev_hard = (index - 1) % 7 == 2
        load = 120.0 if hard else (45.0 if index % 3 == 0 else 0.0)
        fall = (last_damp if (last_damp is not None and index == days - 1) else damp)
        wellness[iso] = {
            "id": iso,
            "hrv": round(49 + _random.gauss(0, 4) - (fall if prev_hard else 0), 1),
            "restingHR": round(56 + _random.gauss(0, 1.6) + (4 if prev_hard else 0)),
            "sleepSecs": int((7.4 + _random.gauss(0, 0.4)) * 3600),
            "form": 0.0, "load": load,
        }
        if load:
            activities[f"a{index}"] = {
                "id": f"a{index}", "start_date_local": iso + "T09:00", "type": "Ride",
                "icu_training_load": load, "icu_intensity": 88.0 if hard else 62.0,
                "moving_time": 3600,
            }
    return {"wellness": wellness, "activities": activities, "dfa": {}}


base_data = night_history()
hard_keys = [k for k, v in base_data["activities"].items() if v["icu_training_load"] == 120]
result = coach.night_after(base_data, hard_keys[-2])
check(result["available"], "18 nacht: nicht auswertbar")
check("hrv" in result["night"], "18 nacht: HRV fehlt")
check(result["night"]["hrv"]["z"] < -0.8,
      f"18 nacht: gedämpfte HRV nicht erkannt ({result['night']['hrv']})")
# ... and yet the verdict must be "as usual", because it IS usual here
eq(result["state"], "usual", "18 nacht: übliche Reaktion als auffällig gemeldet")
check(result["reference"]["hrv"]["n"] >= 5, "18 nacht: zu wenige Vergleichsnächte genutzt")

# a night that falls much further than usual must be flagged
worse = coach.night_after(night_history(last_damp=20.0), hard_keys[-1])
check(worse["state"] in ("hard", "costly"),
      f"18 nacht: ungewöhnlich starke Dämpfung nicht erkannt ({worse['state']})")
# ... and one that barely moves must read as easier than usual
easier = coach.night_after(night_history(last_damp=-6.0), hard_keys[-1])
check(easier["state"] == "easy",
      f"18 nacht: auffällig gute Nacht nicht erkannt ({easier['state']})")

# the sign convention: a LOWER resting heart rate must read as positive
lowrhr = night_history()
target = lowrhr["activities"][hard_keys[-1]]
night_day = (date.fromisoformat(str(target["start_date_local"])[:10]) + timedelta(days=1)).isoformat()
lowrhr["wellness"][night_day]["restingHR"] = 48
flipped = coach.night_after(lowrhr, hard_keys[-1])
check(flipped["night"]["rhr"]["z"] > 0,
      f"18 nacht: niedriger Ruhepuls nicht als günstig gewertet ({flipped['night']['rhr']})")

# --- 19  honest refusal where the data cannot carry it -------------------------
thin = night_history(days=40)
thin_keys = [k for k, v in thin["activities"].items() if v["icu_training_load"] == 120]
sparse = coach.night_after(thin, thin_keys[-1])
check(sparse["state"] == "unknown" or not sparse.get("reference"),
      "19 nacht: Urteil trotz zu dünner Vergleichsbasis")
check(coach.night_after(base_data, "gibtsnicht")["available"] is False,
      "19 nacht: unbekannte Einheit wird ausgewertet")
nowell = coach.night_after({"activities": base_data["activities"]}, hard_keys[-1])
check(nowell["available"] is False, "19 nacht: Urteil ohne Wellness-Daten")
# the caveat has to travel with the number, always
check("glockenförmig" in result["caveat"], "19 nacht: Glockenform nicht genannt")
check("Nachtmessung" in result["caveat"], "19 nacht: Messgrenze nicht genannt")

# --- 20  where a session sits among comparable ones ---------------------------
# The point: 11.4% decoupling means nothing against a population benchmark.
# What answers "is that a lot for me" is this rider's own spread.
def ride_history(n=40):
    _random.seed(3)
    wellness, activities = {}, {}
    for index in range(n):
        iso = day(-(n - 1 - index))
        wellness[iso] = {"id": iso, "hrv": 49.0, "restingHR": 56.0,
                         "sleepSecs": 26640, "form": 0.0, "load": 60.0}
        activities[f"r{index}"] = {
            "id": f"r{index}", "start_date_local": iso + "T09:00", "type": "Ride",
            "icu_training_load": 60.0, "icu_intensity": 62.0, "moving_time": 3600,
            "decoupling": round(2.0 + _random.gauss(0, 1.2), 2),
            "average_heartrate": 138.0, "icu_average_watts": 96.0,
        }
    return {"wellness": wellness, "activities": activities, "dfa": {}}


rides = ride_history()
# make the newest ride an outlier in decoupling
rides["activities"]["r39"]["decoupling"] = 11.4
ctx = coach.session_context(rides, "r39")
check(ctx["available"], "20 einordnung: nicht verfügbar")
dec = ctx["metrics"]["decoupling"]
check(dec["enough"], "20 einordnung: Vergleichsgruppe zu klein gemeldet")
check(dec["rank"] >= 90, f"20 einordnung: Ausreißer nicht als solcher erkannt (Rang {dec['rank']})")
eq(dec["verdict"], "schlechter als sonst", "20 einordnung: hohe Entkopplung falsch gewertet")
check(dec["median"] < 4, f"20 einordnung: Median unplausibel ({dec['median']})")

# the same number at the good end must read as good - direction matters
rides["activities"]["r39"]["decoupling"] = -0.9
good = coach.session_context(rides, "r39")["metrics"]["decoupling"]
eq(good["verdict"], "besser als sonst", "20 einordnung: niedrige Entkopplung nicht als gut gewertet")
check(good["rank"] <= 15, f"20 einordnung: Rang der guten Fahrt zu hoch ({good['rank']})")

# a middling value must not be dressed up either way
rides["activities"]["r39"]["decoupling"] = 2.0
mid = coach.session_context(rides, "r39")["metrics"]["decoupling"]
eq(mid["verdict"], "im üblichen Bereich", "20 einordnung: Mittelfeld falsch gewertet")

# --- 21  the comparison group has to be comparable ----------------------------
mixed = ride_history()
# a three-hour easy ride and a 45-minute hard one must not share a group
mixed["activities"]["long"] = {
    "id": "long", "start_date_local": day(-2) + "T09:00", "type": "Ride",
    "icu_training_load": 129.0, "icu_intensity": 61.0, "moving_time": 12000,
    "decoupling": 10.6, "average_heartrate": 142.0, "icu_average_watts": 131.0,
}
long_ctx = coach.session_context(mixed, "long")
check(long_ctx["peers"] == 0 or not long_ctx["metrics"]["decoupling"]["enough"],
      f"21 einordnung: Langfahrt gegen Kurzeinheiten verglichen ({long_ctx['peers']} Partner)")
# a run must never be compared against rides
mixed["activities"]["run"] = {
    "id": "run", "start_date_local": day(-1) + "T09:00", "type": "Run",
    "icu_training_load": 60.0, "icu_intensity": 62.0, "moving_time": 3600,
    "decoupling": 3.0, "average_heartrate": 140.0,
}
eq(coach.session_context(mixed, "run")["peers"], 0, "21 einordnung: Lauf gegen Radfahrten verglichen")
# only sessions BEFORE this one count - no peeking into the future
early = coach.session_context(rides, "r2")
check(early["peers"] <= 2, f"21 einordnung: spätere Einheiten im Vergleich ({early['peers']})")
check(coach.session_context(rides, "nope")["available"] is False,
      "21 einordnung: unbekannte Einheit ausgewertet")

print(f"test_coach: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
sys.exit(1 if FAILURES else 0)
