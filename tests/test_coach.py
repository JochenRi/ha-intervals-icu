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
import workouts  # noqa: E402

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
out = coach.assessment(data)
eq(out["state"]["state"], "ready", "1 assessment: Zustand")
check(out["warnings"] == [], "1 assessment: Warnung ohne Anlass")

# --- 2  an acute slump today is a slump, not "strained" -----------------------
slump = build(overrides={day(0): {"hrv": 30.0, "restingHR": 66.0}})
st = coach.state(slump)
eq(st["state"], "slump", "2 einbruch")
eq(st["since"], day(0), "2 einbruch: falscher Tag")
slump_fits = [w["key"] for w in workouts.suggest("slump") if w["fit"] == "ok"]
eq(slump_fits, ["recovery_40"], "2 einbruch: mehr als Regeneration freigegeben")

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
out = coach.assessment(back)
eq(out["state"]["state"], "rebound", "4 wiedereinstieg: Zustand")
eq(out["layoff"]["phase"], "wiedereinstieg", "4 wiedereinstieg: Phase")
check(out["state"]["infection_suspected"], "4 wiedereinstieg: Infektmuster nicht erkannt")
picks = workouts.suggest(out["state"]["state"], layoff_days=out["layoff"]["days"])
hard_ok = [w["key"] for w in picks if w["fit"] == "ok" and w["intensity"] >= 80]
eq(hard_ok, [], "4 wiedereinstieg: harte Einheit freigegeben")
check(any("Infekt" in w or "stufenweise" in w for w in out["warnings"]),
      "4 wiedereinstieg: kein Hinweis zur stufenweisen Rückkehr")
check(any("Muster" in w for w in out["warnings"]),
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
out = coach.assessment(build(activities=hard))
eq(out["hard_days_last_7"], 2, "5 zwei harte Tage: nicht gezählt")
check(any("Seiler" in r["quelle"] for r in out["reasons"]), "5 zwei harte Tage: Begründung fehlt")
downgraded = [w for w in workouts.suggest("ready", hard_days_last_7=2) if w["intensity"] >= 80]
check(downgraded and all(w["fit"] != "ok" for w in downgraded),
      "5 zwei harte Tage: dritter harter Tag ohne Abwertung")

# --- 6  anchors come from measured DFA, not from a guess ---------------------
anc = coach.anchors(data)
eq(anc["aerobic_hr"], 157, "6 anker: Herzfrequenz")
eq(anc["aerobic_power"], 158, "6 anker: Leistung")
check("Rogers" in anc["source"], "6 anker: Quelle fehlt")
thin = build()
thin["dfa"] = {k: {"hr_at_threshold": 150, "threshold_samples": 2} for k in list(thin["activities"])[:5]}
check(coach.anchors(thin)["aerobic_hr"] is None, "6 anker: dünne Messungen zählen mit")

# --- 7  target windows are derived from those anchors ------------------------
anc7 = coach.anchors(data)
for entry in workouts.suggest("ready", ftp=250, aerobic_hr=anc7["aerobic_hr"]):
    if entry.get("hr_window"):
        low, high = entry["hr_window"]
        check(90 < low < high < 210, f"7 zielfenster unplausibel: {entry['key']} {entry['hr_window']}")
    check(entry["dfa"], f"7 {entry['key']}: kein erwarteter DFA-Bereich")
    check(entry["effect"] and len(entry["effect"]) > 40, f"7 {entry['key']}: keine Wirkungsbeschreibung")

# --- 8  budget interaction ----------------------------------------------------
tight = workouts.suggest("ready", budget=20)
check(any(w["fits_budget"] is False for w in tight), "8 budget: zu große Einheit passt angeblich")
wide = workouts.suggest("ready", budget=500)
check(all(w["fits_budget"] is True for w in wide), "8 budget: passende Einheit passt angeblich nicht")
free = workouts.suggest("ready", budget=None)
check(all(w["fits_budget"] is None for w in free), "8 budget: erfundene Aussage ohne Budget")

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
    for key in ("state", "layoff", "anchors", "reasons", "warnings", "evidence"):
        check(key in out, f"10 {label}: {key} fehlt")
    for gone in ("recommendation", "plan", "sessions"):
        check(gone not in out, f"10 {label}: zweite Empfehlungsquelle ({gone}) im Payload")
eq(coach.state(build(days=10))["state"], "unknown", "10 kurze Historie: behauptet einen Zustand")
check(coach.state(build(days=10))["confidence"] == "keine", "10 kurze Historie: Vertrauen behauptet")

# --- 11  a session already ridden today is not ignored ------------------------
today_ride = build()
today_ride["activities"]["heute"] = {
    "id": "heute", "start_date_local": day(0) + "T09:00:00", "type": "Ride",
    "moving_time": 3600, "icu_intensity": 60, "icu_training_load": 50,
    "average_heartrate": 140, "icu_average_watts": 140, "decoupling": 1.5}
check(coach.assessment(today_ride)["trained_today"] is True,
      "11 heute gefahren: nicht erkannt")
check(coach.assessment(build())["trained_today"] is False,
      "11 nichts gefahren: trotzdem behauptet")

# --- 12  the payload carries its own limits ----------------------------------
full = coach.coach(data)
check("Düking" in full["evidence"]["limit"], "12 belege: die Metaanalyse fehlt")
check("Non-Responder" in full["evidence"]["limit"], "12 belege: der Non-Responder-Befund fehlt")
check("Javaloyes" in full["evidence"]["rule"], "12 belege: die Regel ist nicht benannt")

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

# --- 22  the day's load comes from the activities ------------------------------
# Reading it from the wellness row reported "0 load in seven days" on a week
# that contained a ride and a walk - that field is simply not filled on every
# account, and the activities always are.
noload = night_history()
for row in noload["wellness"].values():
    row.pop("load", None)
today_view = coach.today(noload, {"recommended": 90})
check(today_view["available"], "22 heute: nicht auswertbar")
check(today_view["week_load"] > 0,
      f"22 heute: Wochenlast 0 trotz Einheiten im Archiv ({today_view['week_load']})")
ridden = [row for row in today_view["recent"] if row["load"] > 0]
check(ridden, "22 heute: kein Tag mit Last")
check(all(row["sessions"] for row in ridden), "22 heute: Einheiten nicht benannt")
check(today_view["rest_days"] < 7, "22 heute: alle Tage als Ruhetage gezählt")

# a genuinely empty week must still read as empty
empty = night_history()
empty["activities"] = {}
for row in empty["wellness"].values():
    row.pop("load", None)
quiet = coach.today(empty, None)
eq(quiet["week_load"], 0, "22 heute: Last ohne Einheiten erfunden")
eq(quiet["rest_days"], 7, "22 heute: Ruhetage nicht gezählt")

# --- 23  every signal ships 42 days of history for the enlarged card ----------
history = today_view.get("history") or {}
check("hrv" in history, "23 verlauf: HRV fehlt")
check(len(history["hrv"]) <= 42, "23 verlauf: mehr als 42 Tage")
check(any(v is not None for v in history["hrv"]), "23 verlauf: nur Lücken")
check(all(v is None or 10 < v < 200 for v in history["hrv"]), "23 verlauf: unplausible Werte")
check(all(v is None or 3 < v < 14 for v in history.get("sleep", [])),
      "23 verlauf: Schlaf nicht in Stunden umgerechnet")

# --- 23b  the same 42 days, but NAMED, with load and state --------------------
# The enlarged signal card draws a diagram, and a diagram needs an axis. The
# frontend cannot build that axis itself: these are the wellness days that
# EXIST, not 42 consecutive calendar days. "Today minus n" is wrong from the
# first gap onwards - the same defect class as reading a number off the wrong
# source. So the dates travel with the values.
raw_hdays = today_view.get("history_days")
check(isinstance(raw_hdays, list) and bool(raw_hdays),
      "23b spur: history_days fehlt oder ist leer")
# Everything below runs off a list that EXISTS, so a missing key produces a
# counted failure instead of a traceback. A test that dies on the mutation
# skips the rest of the file and reports "0 Fehler" - that was the most
# expensive find of 0.35.0, and it does not get to happen in its own fix.
hdays = [r for r in raw_hdays if isinstance(r, dict)] if isinstance(raw_hdays, list) else []
hist_hrv = (history or {}).get("hrv") or []
eq(len(hdays), len(hist_hrv), "23b spur: andere Länge als der Werteverlauf")
check(all({"date", "load", "state"} <= set(r) for r in hdays),
      "23b spur: Zeile ohne Datum, Last oder Zustand")
hd_dates = [r.get("date") for r in hdays]
check(hdays and all(isinstance(d, str) and len(d) == 10 for d in hd_dates),
      "23b spur: Datum nicht als ISO-Tag")
check(hd_dates == sorted(hd_dates, key=str), "23b spur: Tage nicht aufsteigend")
check(len(set(hd_dates)) == len(hd_dates), "23b spur: Tag doppelt")
check(all(isinstance(r.get("load"), (int, float)) and r.get("load") >= 0 for r in hdays),
      "23b spur: Last fehlt oder ist negativ")
check(any((r.get("load") or 0) > 0 for r in hdays), "23b spur: kein einziger Trainingstag")
check(hdays and all(isinstance(r.get("state"), str) and r.get("state") for r in hdays),
      "23b spur: Zustand leer")
# ONE way to the day's load: the 7-day strip and the 42-day track must agree
by_date = {r.get("date"): r.get("load") for r in hdays}
check(bool(hdays) and all(by_date.get(row["date"]) == row["load"]
                          for row in today_view.get("recent") or []),
      "23b spur: Last weicht von der 7-Tage-Leiste ab — zwei Rechenwege")
# and the decisive one: punch a hole in the archive. The dates must JUMP over
# it, not silently renumber - that is what "today minus n" would get wrong.
gapped = night_history()
for row in gapped["wellness"].values():
    row.pop("load", None)
missing = sorted(gapped["wellness"])[-20]
del gapped["wellness"][missing]
gap_rows = coach.today(gapped, None).get("history_days") or []
gap_days = [r.get("date") for r in gap_rows if isinstance(r, dict)]
check(bool(gap_days) and missing not in gap_days,
      "23b spur: gelöschter Tag taucht im Verlauf auf")
check(gap_days == sorted(gapped["wellness"])[-42:],
      "23b spur: Tage folgen nicht den vorhandenen Wellness-Tagen")

# --- 24  the bands, in the signal's own unit ----------------------------------
# A rider recognises 41 ms; -1.5 SD means nothing at a glance. So the
# thresholds the rules already use are converted back into real units - and for
# the HRV that conversion has to go through exp(), because the baseline is
# computed on the log scale.
bands = today_view.get("bands") or {}
check("hrv" in bands and "rhr" in bands, "24 bereiche: fehlen")
hrv_band = bands["hrv"]
check(hrv_band["noise"][0] < hrv_band["baseline"] < hrv_band["noise"][1],
      f"24 bereiche: Rauschband liegt nicht um die Basislinie ({hrv_band})")
check(hrv_band["usual"][0] < hrv_band["noise"][0], "24 bereiche: 1 SD enger als 0,5 SD")
check(hrv_band["usual"][1] > hrv_band["noise"][1], "24 bereiche: 1 SD enger als 0,5 SD")
check(hrv_band["slump"] < hrv_band["usual"][0],
      f"24 bereiche: Einbruchsschwelle innerhalb der gewohnten Schwankung ({hrv_band})")
check(10 < hrv_band["baseline"] < 200, f"24 bereiche: HRV-Basislinie unplausibel ({hrv_band})")
check(hrv_band["slump"] > 0, "24 bereiche: negative HRV-Schwelle - log-Rücktransformation fehlt")

# for the resting heart rate the threshold points the OTHER way: HIGH is bad
rhr_band = bands["rhr"]
check(rhr_band["slump"] > rhr_band["usual"][1],
      f"24 bereiche: Ruhepuls-Schwelle nach unten statt nach oben ({rhr_band})")
check(40 < rhr_band["baseline"] < 90, f"24 bereiche: Ruhepuls unplausibel ({rhr_band})")

# thin history yields no bands rather than invented ones
thin_bands = coach.today(night_history(days=15), None).get("bands") or {}
check(not thin_bands, f"24 bereiche: aus zu wenigen Tagen erfunden ({thin_bands})")

# --- 25  one signal on one day is noise, not a slump --------------------------
# The tension text itself says a single day is noise - the trigger has to agree.
lone = build(overrides={day(0): {"hrv": 38.0}})
st = coach.state(lone)
check(st["state"] != "slump", f"25 einzeltag: ein Signal an einem Tag löst aus ({st['state']})")

# --- 26  one signal on two consecutive days is a signal -----------------------
double = build(overrides={day(-1): {"hrv": 38.0}, day(0): {"hrv": 38.0}})
st = coach.state(double)
eq(st["state"], "slump", "26 folgetage: zwei Tage HRV lösen nicht aus")
eq(st["cause"], "hrv", "26 folgetage: Ursache nicht benannt")
check(not st["infection_suspected"], "26 folgetage: Infektverdacht ohne zweites Signal")
check("zweiten Tag in Folge" in st["detail"], "26 folgetage: Text erklärt die Regel nicht")
series = {row["date"]: row["state"] for row in coach.state_series(double)}
check(series[day(-1)] != "slump", "26 folgetage: erster Tag schon als Einbruch gebändert")
eq(series[day(0)], "slump", "26 folgetage: Verlauf widerspricht dem Trainer")
# resting heart rate alone, two days in a row, triggers the same way
double_rhr = build(overrides={day(-1): {"restingHR": 66.0}, day(0): {"restingHR": 66.0}})
st = coach.state(double_rhr)
eq(st["state"], "slump", "26 folgetage: Ruhepuls-Doppeltag löst nicht aus")
eq(st["cause"], "ruhepuls", "26 folgetage: Ruhepuls-Ursache nicht benannt")

# --- 27  both signals on the same day: the infection pattern ------------------
# The September infection sat at -2.7 SD HRV and +3.7 SD resting HR on ONE day -
# the sharpened trigger must still catch exactly that case.
sept = build(overrides={day(0): {"hrv": 46.0, "restingHR": 57.2}})
zh = (46.0 - 50.0) / 1.41
check(zh <= -2.0, "27 infekt: Testwert unter der Schwelle gewählt")
st = coach.state(sept)
eq(st["state"], "slump", "27 infekt: beide Signale am selben Tag lösen nicht aus")
eq(st["cause"], "beide", "27 infekt: Ursache nicht als gemeinsam erkannt")
check(st["infection_suspected"], "27 infekt: kein Infektverdacht bei beiden Signalen")
check("Infekt" in st["detail"], "27 infekt: Text benennt das Muster nicht")
out = coach.assessment(sept)
check(any("Leiter" in w and "Halses" in w for w in out["warnings"]),
      "27 infekt: symptomgeleitete Leiter fehlt in den Warnungen")
check(any("Konvention" in w for w in out["warnings"]),
      "27 infekt: Halsregel nicht als Konvention gekennzeichnet")

# --- 28  ONE "now" per anchor block -------------------------------------------
anc = coach.anchors(build())
if anc["trend_power"]:
    eq(anc["trend_power"]["hr_now"], anc["aerobic_hr"],
       "28 anker: zwei verschiedene Jetzt-Werte für die Herzfrequenz")
    eq(anc["trend_power"]["power_now"], anc["aerobic_power"],
       "28 anker: zwei verschiedene Jetzt-Werte für die Leistung")
check("alleinige Verankerung nicht" in anc["source"],
      "28 anker: Quellzeile ohne den Trend-Vorbehalt")


# --- 29 · Basislinien-Primitive: ein Rechenweg, vier Aufrufer -----------------
# Bis 0.36.1 rechnete state() die HRV-Basislinie roh, die Verlaufsbänder im
# Log — Trainerurteil und Bänder konnten am selben Tag verschieden ausfallen.
# Der Wächter prüft die Aufrufer per AST, der Nachweis eine Fixture, die den
# Unterschied sichtbar macht: heute -2,6 SD im Log, aber nur -1,5 SD roh.
import ast  # noqa: E402

_COACH_SRC = (Path(__file__).resolve().parents[1] / "custom_components"
              / "intervals_icu" / "coach.py").read_text(encoding="utf-8")
_COACH_TREE = ast.parse(_COACH_SRC)


def _callers_of(name: str) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(_COACH_TREE):
        if isinstance(node, ast.FunctionDef):
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                        and sub.func.id == name):
                    found.add(node.name)
    return found


_band_callers = _callers_of("_band")
eq(_band_callers, {"_norm_band", "night_after"},
   "29 primitive: _band wird außerhalb von _norm_band/night_after gerufen — "
   "eine Basislinie rechnet am Rechenweg vorbei")
_norm_callers = _callers_of("_norm_band")
for required in ("state", "_z_series", "_night_z", "_signal_bands"):
    check(required in _norm_callers,
          f"29 primitive: {required} ruft _norm_band nicht — eigener Rechenweg")

# Log-Nachweis: 55×50 ms und 5×110 ms Vorgeschichte, heute 30 ms. Roh ist das
# -1,51 SD (kein Treffer), im Log -2,65 SD (Treffer). Ruhepuls springt am
# selben Tag — das Infektmuster feuert also NUR, wenn state() im Log rechnet.
_lw = {}
for _i in range(60):
    _d = (TODAY - timedelta(days=60 - _i)).isoformat()
    _lw[_d] = {"id": _d, "hrv": 110.0 if _i % 12 == 0 else 50.0,
               "restingHR": 56.0 + ((_i * 7) % 5 - 2) * 0.2,
               "sleepSecs": 7.5 * 3600}
_lw[TODAY.isoformat()] = {"id": TODAY.isoformat(), "hrv": 30.0,
                          "restingHR": 66.0, "sleepSecs": 7.5 * 3600}
_ldata = {"wellness": _lw, "activities": {}, "dfa": {}}
_lst = coach.state(_ldata)
eq(_lst["state"], "slump",
   "29 log: Infektmuster (HRV -2,6 SD log / -1,5 SD roh + Ruhepuls) "
   "löst nicht aus — state() rechnet die HRV nicht im Log")
_lser = coach.state_series(_ldata)
eq(_lser[-1]["state"], "slump",
   "29 log: Verlaufsband widerspricht dem Trainerurteil am selben Tag")

# week_z ist das Mittel der ln-Werte gegen das Log-Band — unabhängig nachgerechnet.
import math as _math  # noqa: E402
_st29 = coach.state(build())
_w = build()["wellness"]
_hd = sorted(d for d in _w if _w[d].get("hrv"))
_base_vals = [_math.log(_w[d]["hrv"]) for d in _hd if d < _hd[-1]][-60:]
_bmean = sum(_base_vals) / len(_base_vals)
_bsd = (sum((v - _bmean) ** 2 for v in _base_vals) / len(_base_vals)) ** 0.5
_wk = [_math.log(_w[d]["hrv"]) for d in _hd[-7:]]
_expected = (sum(_wk) / len(_wk) - _bmean) / _bsd
check(_st29["week_z"] is not None and _st29["week_z"] == round(_expected, 2),
      f"29 log: week_z {_st29['week_z']} statt ln-Rechnung {round(_expected, 2)}")

# --- 30 · Eingefrorene Referenz: der No-op-Anker für Paket B ------------------
# Diese Werte wurden NACH der Log-Angleichung (d99fd8f) und VOR der ersten
# Zeile Gewichtung festgeschrieben. Ein Archiv ganz ohne Etiketten muss sie
# exakt reproduzieren — sonst hat die Gewichtung den Bestand verändert, bevor
# je ein Etikett gesetzt wurde. Die Sammel-Prüfsumme ist das weite Netz, die
# benannten Felder davor sagen, WAS sich bewegt hat.
import hashlib  # noqa: E402
import json  # noqa: E402
from collections import Counter  # noqa: E402

_f30 = build()
_st30 = coach.state(_f30)
_ser30 = coach.state_series(_f30)
_td30 = coach.today(_f30)
eq(_st30["state"], "ready", "30 referenz: state")
eq(_st30["week_z"], 0.0, "30 referenz: week_z")
eq(_st30["recent_hrv_z"], 0.47, "30 referenz: recent_hrv_z")
eq(_st30["recent_rhr_z"], -0.47, "30 referenz: recent_rhr_z")
eq(len(_ser30), 120, "30 referenz: Serienlänge")
eq(dict(Counter(r["state"] for r in _ser30)),
   {"unknown": 20, "strained": 40, "ready": 60}, "30 referenz: Zustandszählung")
eq([r["state"] for r in _ser30[-5:]],
   ["strained", "ready", "ready", "strained", "ready"], "30 referenz: letzte fünf Tage")
eq([(s["key"], s["value"], s["baseline"], s["z"]) for s in _td30["signals"]],
   [("hrv", 51.0, 49.98, 0.71), ("rhr", 55.8, 56.0, 0.71)],
   "30 referenz: Signalkarten (Wert, Basislinie, z)")
eq(_td30["bands"].get("hrv"),
   {"baseline": 49.98, "noise": [49.28, 50.69], "usual": [48.59, 51.41],
    "slump": 47.23, "unit": "ms", "weighted": False},
   "30 referenz: HRV-Band in echten Einheiten")
eq(_td30["bands"].get("rhr"),
   {"baseline": 56.0, "noise": [55.86, 56.14], "usual": [55.72, 56.28],
    "slump": 56.57, "unit": "bpm", "weighted": False},
   "30 referenz: Ruhepuls-Band in echten Einheiten")
# Die 0.37.0-Form trägt drei neue Schlüssel — ohne Etiketten sind sie leer.
# Benannt geprüft, DANN die Prüfsumme: sie deckt die Form, die Felder die Werte.
eq(_st30.get("explained"), False, "30 referenz: unetikettiert ist nichts erklärt")
eq(_st30.get("context"), None, "30 referenz: unetikettiert kein Tageskontext")
eq(_st30.get("baseline_note"), None,
   "30 referenz: unetikettiert kein Rückfall-Hinweis — der Hinweis darf nur "
   "feuern, wenn er etwas zu sagen hat")
check(all("context" not in r and "explained" not in r for r in _ser30),
      "30 referenz: unetikettierte Serienzeilen tragen keine Kontextschlüssel")
eq(_td30["bands"].get("hrv", {}).get("weighted"), False,
   "30 referenz: unetikettiert bleibt die Basislinie ungewichtet")
_trio30 = {"state": _st30, "series": _ser30,
           "today_sig": [(s["key"], s["value"], s["baseline"], s["z"])
                         for s in _td30["signals"]],
           "bands": _td30["bands"]}
_sha30 = hashlib.sha256(json.dumps(_trio30, sort_keys=True,
                                   ensure_ascii=False).encode()).hexdigest()
# Neu eingefroren für die 0.37.0-Form (Werte per Feldern oben als unverändert
# belegt; Ur-Anker nach der Log-Angleichung war 058c4fc7…).
eq(_sha30, "d7c4bb9fd944eef405b539e76e4397fc498ae17bb15cfd9bc58572451623bbfc",
   "30 referenz: Prüfsumme — etwas außerhalb der benannten Felder hat sich bewegt")

# --- 31 · Gewichtete Basislinie (Paket B3) ------------------------------------
# Die drei Ebenen: Basislinie gewichtet, Warnlampe schließt NIE aus,
# Last bleibt unberührt (Ebene 3 wird in test_analytics bewacht).


def ctx_build(labels=True, low=44.0):
    """20 Nachtschicht-Tage drücken die HRV; gestern und heute liegen bei
    `low`. Gewichtet ist die Basislinie ~50 (Nachtschichten zählen nicht)
    und `low`=44 ein Einbruch — ungewichtet ist die Basislinie ~47 mit
    breiter Streuung und derselbe Wert unauffällig."""
    w, ctx = {}, {}
    for i in range(120):
        d = (TODAY - timedelta(days=119 - i)).isoformat()
        wob = ((i * 7) % 5 - 2) * 1.0
        hrv = 50.0 + wob
        if 80 <= i <= 99:
            hrv = 42.0 + wob
            if labels:
                ctx[d] = {"tag": "nachtschicht", "weight": 0.0, "note": "", "set_at": ""}
        if i >= 118:
            hrv = low
        w[d] = {"id": d, "hrv": hrv, "restingHR": 56.0 - wob * 0.2, "sleepSecs": 27000}
    return {"wellness": w, "activities": {}, "dfa": {}, "day_context": ctx}


# Fixture-Beweis: gewichteter und ungewichteter Bestand ergeben VERSCHIEDENE
# Basislinien — sonst könnte die Suite eine tote Gewichtung nicht von einer
# lebenden unterscheiden.
_twa = coach.today(ctx_build(True))
_twb = coach.today(ctx_build(False))
check(_twa["bands"]["hrv"]["baseline"] != _twb["bands"]["hrv"]["baseline"],
      "31 beweis: Etiketten ändern die Basislinie nicht — Gewichtung tot")
eq(_twa["bands"]["hrv"]["weighted"], True, "31 beweis: Band meldet sich nicht als gewichtet")
eq(_twb["bands"]["hrv"]["weighted"], False, "31 beweis: unetikettiert fälschlich gewichtet")
# unabhängige Nachrechnung des gewichteten Mittels (Log-Skala, Fenster <= heute)
_w31 = ctx_build(True)["wellness"]
_c31 = ctx_build(True)["day_context"]
_d31 = sorted(_w31)[-60:]
_pairs = [(_math.log(_w31[d]["hrv"]), 0.0 if d in _c31 else 1.0) for d in _d31]
_sw = sum(w for _v, w in _pairs)
_mu = sum(v * w for v, w in _pairs) / _sw
check(abs(_twa["bands"]["hrv"]["baseline"] - round(_math.exp(_mu), 2)) < 0.011,
      f"31 beweis: Basislinie {_twa['bands']['hrv']['baseline']} statt "
      f"unabhängig gerechnet {round(_math.exp(_mu), 2)}")

# Gleichlauf: dieselbe Gewichtungsregel greift in state() UND state_series() —
# am letzten Tag müssen beide dasselbe sagen, und zwar NUR gewichtet Einbruch.
eq(coach.state(ctx_build(True))["state"], "slump",
   "31 gleichlauf: Trainerurteil sieht den gewichteten Einbruch nicht")
eq(coach.state_series(ctx_build(True))[-1]["state"], "slump",
   "31 gleichlauf: Verlaufsband sieht den gewichteten Einbruch nicht")
check(coach.state(ctx_build(False))["state"] != "slump",
      "31 gleichlauf: Einbruch auch ungewichtet — Fixture beweist nichts")
check(coach.state_series(ctx_build(False))[-1]["state"] != "slump",
      "31 gleichlauf: Serie bricht auch ungewichtet ein — Fixture beweist nichts")

# Rückfall Σw < 30: 35 etikettierte Tage im 60er-Fenster lassen 25 belastbare —
# der Hinweis MUSS die Zahlen nennen (ein Hinweis ohne Zahl ist ein
# Schulterzucken), und ohne einen einzigen etikettierten Tag gibt es keinen.
_fb = build()
_fb["day_context"] = {day(-o): {"tag": "nachtschicht", "weight": 0.0,
                                "note": "", "set_at": ""}
                      for o in range(1, 36)}
_fbt = coach.today(_fb)
eq(_fbt["bands"]["hrv"]["weighted"], False,
   "31 rückfall: unter Σw=30 wird trotzdem gewichtet")
_note = _fbt["bands"]["hrv"].get("note", "")
check("25" in _note and "30" in _note and "35 Tage sind etikettiert" in _note,
      f"31 rückfall: Hinweis nennt die Zahlen nicht: {_note!r}")
check("zurückgefallen" in _note, "31 rückfall: Hinweis benennt den Rückfall nicht")
_fbs = coach.state(_fb)
check(_fbs.get("baseline_note") and "belastbare" in _fbs["baseline_note"],
      "31 rückfall: Trainerurteil trägt den Hinweis nicht")
check(_fbt.get("context_note") and "25" in _fbt["context_note"],
      "31 rückfall: today() reicht den Hinweis nicht durch")
# Rechenwert des Rückfalls == ungewichteter Bestand, Bit für Bit
_fb0 = build()
eq(coach.today(_fb0)["bands"]["hrv"]["baseline"], _fbt["bands"]["hrv"]["baseline"],
   "31 rückfall: Rückfallwert weicht vom ungewichteten Bestand ab — zweiter Rechenweg")

# Ebene 2: ein w=0-Tag verändert die Basislinie der Beurteilung nicht, löst
# aber weiterhin aus, wenn er extrem ist. Genau der Infekt-Fall: krank
# etikettiert, und die Lampe MUSS trotzdem angehen.
_inf = build(overrides={day(0): {"hrv": 30.0, "restingHR": 66.0}})
_inf["day_context"] = {day(0): {"tag": "krank", "weight": 0.0, "note": "", "set_at": ""}}
_inf0 = build(overrides={day(0): {"hrv": 30.0, "restingHR": 66.0}})
_ist = coach.state(_inf)
eq(_ist["state"], "slump",
   "31 ebene2: krank-Etikett unterdrückt die Einbruchserkennung — genau der "
   "Infekt, den das System nie ausblenden darf")
eq(_ist["explained"], True, "31 ebene2: erklärter Einbruch nicht als erklärt markiert")
check("gesehen" in _ist["detail"] and "Krank" in _ist["detail"],
      "31 ebene2: der Erklärsatz fehlt im Urteilstext")
_irow = coach.state_series(_inf)[-1]
eq(_irow["state"], "slump", "31 ebene2: Serie unterdrückt den erklärten Einbruch")
eq(_irow.get("explained"), True, "31 ebene2: Serienzeile trägt das erklärt-Merkmal nicht")
eq(_irow.get("context"), "krank", "31 ebene2: Serienzeile trägt das Etikett nicht")
eq(coach.state(_inf)["week_z"], coach.state(_inf0)["week_z"],
   "31 ebene2: das Etikett des Tages verschiebt seine eigene Beurteilungsbasis")

# Löschen == nie etikettiert: nach dem Entfernen rechnet ALLES byte-gleich.
_del = build()
_del["day_context"] = {day(-3): {"tag": "alkohol", "weight": 0.5, "note": "", "set_at": ""}}
del _del["day_context"][day(-3)]
_plain = build()
check(json.dumps({"s": coach.state(_del), "r": coach.state_series(_del),
                  "t": coach.today(_del)["bands"]}, sort_keys=True)
      == json.dumps({"s": coach.state(_plain), "r": coach.state_series(_plain),
                     "t": coach.today(_plain)["bands"]}, sort_keys=True),
      "31 löschen: ein entfernter Eintrag rechnet anders als nie etikettiert")

# history_days trägt den Kontext für Chips und Hohlmarker
_hd = coach.today(_inf)["history_days"][-1]
eq(_hd.get("context"), {"tag": "krank", "weight": 0.0},
   "31 payload: history_days ohne Tageskontext")
_ctx_state = coach.state(_inf)
eq(_ctx_state["context"], {"tag": "krank", "label": "Krank", "weight": 0.0},
   "31 payload: state() ohne heutigen Kontext")

print(f"test_coach: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
sys.exit(1 if FAILURES else 0)
