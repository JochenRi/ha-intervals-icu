"""The coach, rule by rule, against the case each rule exists for.

The dangerous failure here is not a crash - it is a confident recommendation
built on a misread state. So every state gets a synthetic history that can
only mean one thing, and the assertions check the decision, not the wording.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import coldcache  # noqa: F401  - MUSS vor jedem Bauteil-Import stehen (§9)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"))

import coach  # noqa: E402
import const  # noqa: E402
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
                             "average_heartrate": 140, "icu_average_watts": 135,
                             "icu_weighted_avg_watts": 138, "icu_joules": 607500}
    if activities is not None:
        acts = activities
    dfa = {key: {"hr_at_threshold": 157, "power_at_threshold": 158, "hr_windows": 40, "power_windows": 40,
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
check("2021a" in anc["source"] and "Laufband" in anc["source"],
      "6 anker: Quelle ohne Arbeit und Sportart (0,75 = Rogers 2021a, Laufband)")
thin = build()
thin["dfa"] = {k: {"hr_at_threshold": 150, "hr_windows": 2, "power_windows": 0} for k in list(thin["activities"])[:5]}
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

# --- 9  durability: split by WORK, and no claim out of an empty group --------
# The tile used to split at 90 minutes. On the live archive that hid the effect
# entirely (-0.1 pp) while the work split showed it (+1.5 pp), because duration
# is a poor stand-in for work. Everything below is about the new contract.

_RIDE_DAY = [0]


def ride(key, kj, dec, *, minutes=90, intensity=60, kind="Ride", vi=1.02, watts=120, days_ago=None):
    seconds = minutes * 60
    # Dates run forward deterministically. hash() is salted per process, so a
    # date built from it would make this file's fixture differ between runs -
    # exactly the kind of test that fails for reasons that teach nothing.
    _RIDE_DAY[0] += 1
    # days_ago lets the block tests place rides deliberately; without it the
    # dates just run forward, one per ride.
    back = days_ago if days_ago is not None else 400 - _RIDE_DAY[0]
    stamp = (TODAY - timedelta(days=back)).isoformat()
    return {
        "id": key, "start_date_local": stamp + "T09:00:00",
        "type": kind, "moving_time": seconds, "icu_intensity": intensity,
        "decoupling": dec, "average_heartrate": 140,
        "icu_average_watts": watts, "icu_weighted_avg_watts": round(watts * vi, 1),
        "icu_joules": kj * 1000,
    }


def dur_data(rows):
    return {"wellness": {}, "activities": {r["id"]: r for r in rows}, "dfa": {}}


# Ein Bestand, der die Kachel überhaupt trägt - klein und groß gemischt.
both = dur_data(
    [ride(f"lo{i}", 600, 1.0) for i in range(8)]
    + [ride(f"hi{i}", 1000, 3.0) for i in range(6)]
)
dur = coach.durability(both)
check(dur is not None, "9 durability: nicht berechnet")
eq(dur["n"], 14, "9 durability: Pool falsch besetzt")
eq(dur["n_full"] + dur["n_partial"] + dur["n_zero"], dur["n"],
   "9 durability: Gewichtsbuchhaltung summiert sich nicht auf n")
check("Setzung" in dur["source"] and "faustregel" in dur["source"].lower(),
      "9 durability: die 5-%-Marke wird als Befund ausgegeben")

# Jede Zahl, die das Panel druckt, muss IN der Payload stehen - im Panel-Test
# steht ein Quelltext-Wächter gegen jede zweite Kopie davon.
for key in ("decoupling_good", "min_minutes", "max_intensity", "vi_full", "vi_none",
            "min_weight_sum", "min_weight_sum_block", "min_slope_t", "block_weeks",
            "bins_kj", "power_days", "power_days_fallback", "min_per_group", "min_sessions"):
    check(dur.get(key) is not None, f"9 durability: {key} fehlt in der Payload")

# --- 9a  Ehrlichkeitsregel 1: nie über den Bestand hinaus hochrechnen --------
# Ein Zusammenhang, dessen Schnittpunkt INNERHALB der Daten liegt: Leitzahl.
clear = dur_data([ride(f"c{i}", 300 + i * 60, round(0.005 * (300 + i * 60) - 1 + (0.2 if i % 2 else -0.2), 3))
                  for i in range(21)])
dur_clear = coach.durability(clear)
eq(dur_clear["blocked"], None, "9a Kipppunkt: klarer Zusammenhang wird nicht ausgesprochen")
check(dur_clear["tipping_kj"] is not None, "9a Kipppunkt: keine Leitzahl trotz gesicherter Steigung")
check(dur_clear["tipping_kj"] <= dur_clear["max_kj"],
      "9a Kipppunkt: liegt jenseits der arbeitsreichsten Fahrt und wird trotzdem genannt")
# Gegenprobe: denselben Zusammenhang, aber der Bestand endet VOR dem Schnitt.
short_stock = dur_data([ride(f"s{i}", 300 + i * 30, round(0.005 * (300 + i * 30) - 1 + (0.2 if i % 2 else -0.2), 3))
                        for i in range(21)])
dur_short = coach.durability(short_stock)
eq(dur_short["blocked"], "beyond",
   "9a Gegenprobe: verkürzter Bestand liefert trotzdem einen Kipppunkt")
check(dur_short["tipping_kj"] is None, "9a Gegenprobe: Kipppunkt jenseits des Bestands genannt")
check(str(dur_short["max_kj"]) in dur_short["headline"] and "Weiter reichen" in dur_short["headline"],
      "9a Gegenprobe: die Überschrift nennt die eigene Grenze nicht")
check(dur_clear["headline"] != dur_short["headline"],
      "9a Fixture-Beweis: voller und verkürzter Bestand sind nicht unterscheidbar")

# --- 9b  Ehrlichkeitsregel 2: keine Leitzahl ohne erkennbare Steigung -------
noisy = dur_data([ride(f"n{i}", 300 + i * 60, [8.0, -8.0, 2.0, -3.0][i % 4]) for i in range(21)])
dur_noisy = coach.durability(noisy)
eq(dur_noisy["blocked"], "flat", "9b flach: Leitzahl aus einer Steigung, die null sein kann")
check(dur_noisy["tipping_kj"] is None, "9b flach: Kipppunkt trotz unerkennbarer Steigung")
check(dur_noisy["slope_t"] < dur_noisy["min_slope_t"], "9b flach: Fixture ist doch signifikant")
check("Streuung" in dur_noisy["headline"],
      "9b flach: die Auskunft sagt nicht, WORAN es liegt - \"kein Zusammenhang\" liest sich wie \"alles gut\"")
check(dur_noisy["needed_sessions"] and dur_noisy["needed_sessions"] > dur_noisy["n"],
      "9b flach: es fehlt die Angabe, was die Messung voranbrächte")
check(dur_clear["slope_t"] >= dur_clear["min_slope_t"],
      "9b Fixture-Beweis: klarer und verrauschter Fall sind am Kriterium nicht unterscheidbar")

# --- 9c  Ehrlichkeitsregel 3: keine Leitzahl unter Mindestbelegung ----------
# Genau der Fall aus dem Livebestand: vier Fahrten, bilderbuchmäßige Steigung
# (|t| 3,3 auf dem echten Block ab 22.04.2026), Kipppunkt bei 640 kJ - und
# trotzdem schweigt die Kachel, weil vier Punkte nichts tragen.
few = dur_data([ride(f"f{i}", 300 + i * 100, round(0.005 * (300 + i * 100) - 1, 3)) for i in range(9)]
               + [ride(f"g{i}", 300 + i * 100, 0.0, vi=1.24) for i in range(3)])
dur_few = coach.durability(few)
check(dur_few["w_sum"] < dur_few["min_weight_sum"],
      "9c dünn: Fixture erreicht die Mindestbelegung doch")
eq(dur_few["blocked"], "thin", "9c dünn: Leitzahl trotz zu geringer Belegung")
check(dur_few["tipping_kj"] is None, "9c dünn: Kipppunkt aus einer Belegung, die nichts trägt")
check(f"{dur_few['w_sum']:.1f}" in dur_few["headline"],
      "9c dünn: die Überschrift nennt die erreichte Belegung nicht")
# und der Beweis, dass die Regel nicht bloß an der Stückzahl hängt: MEHR
# Einheiten, alle fast gewichtslos, bleiben unter derselben Schwelle
heavy_but_wavy = dur_data([ride(f"w{i}", 300 + i * 60, 1.0, vi=1.24) for i in range(30)])
dur_wavy = coach.durability(heavy_but_wavy)
check(dur_wavy["n"] == 30 and dur_wavy["w_sum"] < dur_wavy["min_weight_sum"],
      "9c Gewicht: 30 wellige Einheiten zählen wie 30 gleichmäßige")
eq(dur_wavy["blocked"], "thin", "9c Gewicht: Leitzahl aus 30 fast gewichtslosen Fahrten")

# --- 9d  Die Gewichtung wirkt: mit und ohne muss verschieden herauskommen ---
mixed_weight = dur_data(
    [ride(f"e{i}", 300 + i * 80, round(0.004 * (300 + i * 80), 3)) for i in range(11)]
    + [ride(f"u{i}", 300 + i * 80, 9.0, vi=1.22) for i in range(11)]
)
dur_w = coach.durability(mixed_weight)
flat_points = [{"kj": p["kj"], "dec": p["dec"], "w": 1.0} for p in dur_w["points"]]
unweighted = coach._weighted_line(flat_points)
check(abs(unweighted["b"] * 1000 - dur_w["slope"]) > 0.5,
      "9d Gewichtung: mit und ohne Gewichte kommt dieselbe Trendgerade heraus - "
      "die Fixture belegt den Umbau nicht")
check(0 < min(p["w"] for p in dur_w["points"]) < 1 == max(p["w"] for p in dur_w["points"]),
      "9d Gewichtung: die Fixture enthält keine zwei unterscheidbaren Gewichtsfälle")

# --- 9e  Zeitumrechnung: die Leistung stammt aus dem Pool, nicht aus einer Konstante
check(dur_clear["power"]["watts"] == 120,
      f"9e Umrechnung: fremde Leistung ({dur_clear['power']}) statt der des Pools")
eq(dur_clear["tipping_hours"],
   round(dur_clear["tipping_kj"] * 1000 / (dur_clear["power"]["watts"] * 3600), 2),
   "9e Rundung: Kipppunkt, Leistung und Stunden stammen nicht aus denselben gerundeten Zahlen")
# Gegenprobe mit verändertem Pool: dieselbe Arbeit, doppelte Leistung, halbe Zeit
stronger = dur_data([ride(f"p{i}", 300 + i * 60, round(0.005 * (300 + i * 60) - 1 + (0.2 if i % 2 else -0.2), 3), watts=240)
                     for i in range(21)])
dur_strong = coach.durability(stronger)
eq(dur_strong["tipping_kj"], dur_clear["tipping_kj"],
   "9e Gegenprobe: die Leistung verschiebt den Kipppunkt (sie darf nur die Zeit ändern)")
check(dur_strong["tipping_hours"] < dur_clear["tipping_hours"],
      "9e Gegenprobe: die genannte Zeit hängt nicht am Pool - sie stammt aus einer Konstante")
check(str(dur_strong["power"]["watts"]) in dur_strong["headline"],
      "9e Umrechnung: die verwendete Leistung wird nicht genannt")

# --- 9f  Blöcke: leere Blöcke bleiben leer und werden nicht interpoliert ----
gapped = dur_data([ride(f"alt{i}", 300 + i * 90, round(0.005 * (300 + i * 90) - 1, 3), days_ago=260 + i)
                   for i in range(12)]
                  + [ride(f"neu{i}", 300 + i * 90, round(0.004 * (300 + i * 90) - 1, 3), days_ago=i)
                     for i in range(12)])
dur_gap = coach.durability(gapped)
eq(len(dur_gap["blocks"]), 2,
   f"9f Blöcke: {len(dur_gap['blocks'])} Blöcke statt zwei - die Lücke wurde aufgefüllt")
check(all(b["n"] > 0 for b in dur_gap["blocks"]), "9f Blöcke: Block ohne Einheiten im Verlauf")
check(dur_gap["blocks"][0]["start"] < dur_gap["blocks"][1]["start"],
      "9f Blöcke: Verlauf läuft nicht von alt nach neu")
# und die drei Regeln gelten JE BLOCK: ein Block, der eine reißt, bleibt leer
for block in dur_gap["blocks"]:
    check((block["tipping_kj"] is None) == (block["reason"] is not None),
          "9f Blöcke: Kipppunkt und Ablehnungsgrund widersprechen sich")
    if block["tipping_kj"] is not None:
        check(block["tipping_kj"] <= block["max_kj"],
              "9f Blöcke: ein Block rechnet über seinen EIGENEN Bestand hinaus")

# --- 9g  Was aussortiert wird, und unter welchem Namen ----------------------
mixed = dur_data(
    [ride(f"lo{i}", 600, 1.0) for i in range(8)]
    + [ride(f"hi{i}", 1000, 3.0) for i in range(6)]
    + [ride("rolle", 1000, 0.1, kind="VirtualRide"),
       ride("wellig", 1000, 0.1, vi=1.30),
       ride("hart", 1000, 0.1, intensity=95),
       ride("kurz", 1000, 0.1, minutes=20)]
)
mixed["activities"]["ohne"] = {
    "id": "ohne", "start_date_local": TODAY.isoformat() + "T09:00:00", "type": "Ride",
    "moving_time": 5400, "icu_intensity": 60, "decoupling": 1.0, "icu_joules": 900000,
}
dur_mixed = coach.durability(mixed)
eq(dur_mixed["n"], 14, "9g: aussortierte Einheiten sind doch mitgezählt")
eq(dur_mixed["dropped"]["indoor"], 1, "9g: Rollenfahrt nicht aussortiert")
eq(dur_mixed["dropped"]["variable"], 1, "9g: wellige Einheit nicht aussortiert")
eq(dur_mixed["dropped"]["intense"], 1, "9g: Intervalleinheit nicht aussortiert")
eq(dur_mixed["dropped"]["short"], 1, "9g: zu kurze Einheit nicht aussortiert")
# Der Fehler aus 0.39.0: eine Fahrt OHNE Leistungsmessung wurde als "zu wellig"
# gezählt. Am Livebestand waren das 53 von 64 - die Kachel behauptete etwas
# über Fahrten, über die sie nichts weiß.
eq(dur_mixed["dropped"]["no_power"], 1,
   "9g: Fahrt ohne Leistungsmessung wird nicht getrennt gezählt")
check(dur_mixed["dropped"]["variable"] != dur_mixed["dropped"]["no_power"] + 1,
      "9g Fixture-Beweis: wellig und ohne Leistung sind in dieser Fixture nicht unterscheidbar")

# --- 9h  Die gebinnten Mediane: Beschreibung, keine Vorhersage --------------
bands = dur_clear["bins"]
eq(len(bands), len(dur_clear["bins_kj"]) + 1, "9h Bänder: Anzahl passt nicht zu den Grenzen")
check(all(b["median"] is None for b in bands if b["thin"]),
      "9h Bänder: ein zu dünn besetztes Band behauptet trotzdem einen Median")
check(all(b["n"] >= dur_clear["min_per_group"] for b in bands if b["median"] is not None),
      "9h Bänder: Median aus weniger Einheiten als die Mindestbesetzung")
eq(sum(b["n"] for b in bands), dur_clear["n"], "9h Bänder: die Bänder summieren sich nicht auf n")

# Zu wenig Historie: gar keine Kachel, statt einer Kachel auf vier Einheiten.
check(coach.durability(dur_data([ride(f"x{i}", 600, 1.0) for i in range(4)])) is None,
      "9 durability: Kachel aus zu wenigen Einheiten gebaut")


# --- 9i  Paket H: der Kopf. Belegte Faehigkeit, nie aus einem Modell ---------
# Die erste Zeile steht ab der ersten Fahrt da und kippt NICHT, wenn die
# Statistik nicht traegt. Genau deshalb wird sie am GESPERRTEN Fall geprueft.
check(dur_noisy["blocked"] == "flat", "9i Fixture-Beweis: der verrauschte Fall ist nicht gesperrt")
prog_noisy = dur_noisy["progression"]
check(prog_noisy is not None, "9i Kopf: fehlt, obwohl die Kachel gesperrt ist")
check(prog_noisy["demonstrated"]["minutes"] > 0 and prog_noisy["demonstrated"]["watts"],
      "9i Kopf: die belegte Fahrt hat keine Dauer oder keine Leistung")

# Dauer und Leistung liegen AN den Punkten - Kopf und Wolke kommen aus einer
# Liste. Das ist die Zusicherung "gleicher Pool", und sie folgt aus der
# Datenstruktur statt aus einem Test, der daneben steht.
for point in dur_noisy["points"]:
    check(point.get("minutes") and point.get("watts"),
          "9i Punkte: Dauer oder Leistung fehlt am Punkt")
# .get statt [] mit Absicht: faellt das Feld weg, soll der Test es ZAEHLEN und
# BENENNEN, nicht abstuerzen - ein Absturz ueberspringt alles Folgende und
# meldet am Ende "0 Fehler" (PROJEKTSTAND Paragraph 9).
longest = max(dur_noisy["points"], key=lambda q: q.get("minutes") or 0)
eq(prog_noisy["demonstrated"]["minutes"], longest.get("minutes"),
   "9i Kopf: die belegte Dauer stammt nicht aus dem Punkt-Pool")
eq(prog_noisy["demonstrated"]["watts"], longest.get("watts"),
   "9i Kopf: die genannte Leistung ist nicht die der belegten Fahrt")

# --- 9j  Laengste (nach ZEIT) ist NICHT arbeitsreichste (nach kJ) ------------
# Am Livebestand vom 13.09.2026 sind beide dieselbe Fahrt. Eine daran gebaute
# Fixture wuerde die Unterscheidung ueberhaupt nicht pruefen, also wird sie hier
# erzwungen: eine lange leichte gegen eine kurze arbeitsreiche Fahrt.
apart = dur_data(
    [ride(f"m{i}", 400 + i * 20, [1.0, -1.0, 2.0, -2.0][i % 4], minutes=90, watts=90)
     for i in range(12)]
    + [ride("lang_leicht", 670, 0.5, minutes=240, watts=47),
       ride("kurz_schwer", 2000, 0.5, minutes=110, watts=303)]
)
dur_apart = coach.durability(apart)
p_apart = dur_apart["progression"]
heaviest = max(dur_apart["points"], key=lambda q: q.get("kj") or 0)
longest_a = max(dur_apart["points"], key=lambda q: q.get("minutes") or 0)
check(heaviest["id"] != longest_a["id"],
      "9j Fixture-Beweis: laengste und arbeitsreichste Fahrt sind dieselbe - "
      "der Widerspruch waere nicht pruefbar")
eq(p_apart["demonstrated"]["id"], "lang_leicht",
   "9j Kopf: der Kopf zeigt die arbeitsreichste statt der laengsten Fahrt")
eq(dur_apart["max_kj"], heaviest["kj"],
   "9j Rechenweg: max_kj ist nicht die arbeitsreichste Fahrt")
check(p_apart["demonstrated"]["kj"] != dur_apart["max_kj"],
      "9j: die beiden Superlative fallen zusammen - die Beschriftung ist nicht pruefbar")
# Gegenprobe: wer im Kopf nach kJ sortiert, landet auf der kurzen Fahrt.
eq(max(dur_apart["points"], key=lambda q: q.get("kj") or 0).get("minutes"), 110,
   "9j Gegenprobe: Sortierung nach Arbeit liefert doch die laengste Fahrt")

# --- 9k  Die Wattzahl im Kopf ist die der Fahrt, nicht der Pool-Median -------
# Auch diese Verwechslung waere am Livebestand unsichtbar: dort hat die
# laengste Fahrt zufaellig genau die 136 W des Pool-Medians.
check(dur_apart["power"] and dur_apart["power"]["watts"] != p_apart["demonstrated"]["watts"],
      "9k Fixture-Beweis: Fahrt-Leistung und Pool-Median sind identisch - "
      "eine Leihgabe aus der Umrechnung waere unsichtbar")
eq(p_apart["demonstrated"]["watts"], 47,
   "9k Kopf: im Kopf steht eine andere Leistung als die der belegten Fahrt")

# --- 9l  Zeile 2 kann Zeile 1 nie uebersteigen ------------------------------
for label, payload in (("verrauscht", dur_noisy), ("getrennt", dur_apart),
                       ("klar", dur_clear), ("duenn", dur_few)):
    pr = payload["progression"]
    check(pr is not None, f"9l {label}: kein Kopf")
    check(pr["recent"]["minutes"] <= pr["demonstrated"]["minutes"],
          f"9l {label}: der Bezug uebersteigt die belegte Dauer - "
          "zwei verschiedene Grundgesamtheiten")
    ids = {q["id"] for q in payload["points"]}
    check(pr["demonstrated"]["id"] in ids and pr["recent"]["id"] in ids,
          f"9l {label}: eine Kopfzeile stammt nicht aus dem Punkt-Pool")

# --- 9m  Leeres 30-Tage-Fenster: ausgeweitet UND genannt ---------------------
# Zwei Bestaende mit denselben Fahrten und derselben Luecke, die sich NUR darin
# unterscheiden, ob im nahen Fenster etwas liegt. Ohne das zweite prueft das
# erste nur, dass die Leiter ueberhaupt eine Sprosse hat.
_far = [ride(f"far{i}", 500 + i * 40, [1.0, -1.0, 2.0][i % 3], minutes=80 + i, days_ago=150 + i)
        for i in range(12)]
away = dur_data(list(_far))
away["wellness"] = {TODAY.isoformat(): {"id": TODAY.isoformat()}}
near = dur_data(_far + [ride("nah", 700, 1.0, minutes=95, days_ago=6)])
near["wellness"] = {TODAY.isoformat(): {"id": TODAY.isoformat()}}
p_away = coach.durability(away)["progression"]
p_near = coach.durability(near)["progression"]
eq(p_away["recent"]["days"], 365, "9m leer: das Fenster wurde nicht ausgeweitet")
check(p_away["recent"]["widened"] is True, "9m leer: die Ausweitung wird nicht ausgewiesen")
eq(p_near["recent"]["days"], p_near["window_days"],
   "9m gefuellt: das nahe Fenster wird ausgeweitet, obwohl es besetzt ist")
check(p_near["recent"]["widened"] is False,
      "9m gefuellt: eine Ausweitung wird behauptet, die nicht stattfand")
eq(p_near["recent"]["id"], "nah", "9m gefuellt: der Bezug stammt nicht aus dem nahen Fenster")
check(p_away["recent"]["days"] != p_near["recent"]["days"],
      "9m Fixture-Beweis: leeres und gefuelltes Fenster sind nicht unterscheidbar")
# Und der Uhrzeiger ist der des Archivs, nicht der der Maschine: ohne Wellness
# faellt er auf die juengste Fahrt zurueck, mit Wellness laeuft er weiter.
p_noclock = coach.durability(dur_data(list(_far)))["progression"]
eq(p_noclock["recent"]["days"], p_noclock["window_days"],
   "9m Uhr: ohne Wellness-Tag wird trotzdem ausgeweitet")

# --- 9n  Der Progressionsfaktor: aus const.py, einmal, und in der Payload ----
eq(p_apart["factor"], const.PROGRESSION_FACTOR, "9n: der Faktor steht nicht in der Payload")
eq(p_apart["round_minutes"], const.PROGRESSION_ROUND_MINUTES,
   "9n: der Rundungsschritt steht nicht in der Payload")
eq(p_apart["window_days"], const.PROGRESSION_WINDOWS_DAYS[0],
   "9n: das Bezugsfenster steht nicht in der Payload")
step = const.PROGRESSION_ROUND_MINUTES
eq(p_apart["next_minutes"],
   int(round(p_apart["recent"]["minutes"] * const.PROGRESSION_FACTOR / step) * step),
   "9n: der gedruckte Schritt ist nicht der nachgerechnete")
eq(p_apart["next_minutes"] % step, 0, "9n: der Schritt ist nicht auf den Schritt gerundet")
# Die Gegenprobe, die der Auftrag verlangt: Faktor auf 1,0 -> der Satz verliert
# seine Aussage. Steht sie nicht drin, prueft die Zeile darueber nur Arithmetik.
check(p_apart["next_minutes"] > p_apart["recent"]["minutes"],
      "9n Gegenprobe: der naechste Schritt liegt nicht ueber dem Bezug - "
      "mit Faktor 1,0 sagt die Zeile nichts mehr")

# --- 9o  Der Rueckfall: Regel, nicht Sonderfall -----------------------------
# Er greift, sobald eine einzelne Ausreisser-Langfahrt mehr als den Faktor ueber
# dem nahen Bezug liegt - am Livebestand vom 13.09.2026 trifft das bei GUT
# gefuelltem Fenster zu (260 gegen 230 Minuten).
back = dur_data(
    [ride(f"b{i}", 400 + i * 20, [1.0, -1.0, 2.0][i % 3], minutes=100, days_ago=20 + i)
     for i in range(10)]
    + [ride("ausreisser", 900, 1.0, minutes=240, days_ago=200)]
)
back["wellness"] = {TODAY.isoformat(): {"id": TODAY.isoformat()}}
p_back = coach.durability(back)["progression"]
eq(p_back["demonstrated"]["minutes"], 240, "9o: die belegte Dauer ist nicht die Ausreisser-Fahrt")
eq(p_back["recent"]["minutes"], 100, "9o: der Bezug stammt nicht aus dem nahen Fenster")
check(p_back["below_demonstrated"] is True,
      "9o: der Rueckfall wird nicht erkannt, obwohl der Schritt unter der Bestleistung liegt")
check(p_back["next_minutes"] < p_back["demonstrated"]["minutes"],
      "9o: below_demonstrated widerspricht den eigenen Zahlen")
# Gegenfall aus demselben Bestand, nur ohne den Ausreisser: kein Rueckfall.
forward_only = dur_data([a for k, a in back["activities"].items() if k != "ausreisser"])
forward_only["wellness"] = back["wellness"]
p_fwd = coach.durability(forward_only)["progression"]
check(p_fwd["below_demonstrated"] is False,
      "9o Fixture-Beweis: auch ohne Ausreisser wird ein Rueckfall gemeldet - "
      "der Zweig ist nicht unterscheidbar")

# --- 9p  Bloecke sagen, worauf sie warten -----------------------------------
for block in dur_gap["blocks"] + dur_noisy["blocks"]:
    if block["reason"] == "thin":
        check(block["need_w"] and block["need_w"] > 0,
              "9p Block: 'zu duenn' ohne Angabe, wieviel Gewicht fehlt")
    if block["reason"] == "flat" and block["slope_t"] and block["slope_t"] > 0:
        check(block["need_n"] and block["need_n"] > block["n"],
              "9p Block: 'kein Trend' ohne Angabe, wieviele Einheiten es braeuchte")
    if block["tipping_kj"] is not None:
        check(block["need_w"] is None and block["need_n"] is None,
              "9p Block: ein tragender Block wartet angeblich noch auf etwas")


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
                           "power_at_threshold": 158, "hr_windows": 40, "power_windows": 40}
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

# --- 18b  L2 (0.69.0): die Nacht-Bewertung als ANZEIGE, Setzung, kein Eingang ---
# Entscheidung 25.09.: verdaut (HRV-z der Nacht danach >= -0,5) · gekostet (< -0,5)
# · zu viel (< -1,0 ODER beide Naechte < -0,5; 0.69.1) · gekostet verzoegert (erste im
# Band, zweite < -0,5; 0.69.1). Nur Anzeige - der Trainer liest
# sie nicht. Die Schwellen sind benannte Konstanten.
eq((coach.NIGHT_DIGESTED_Z, coach.NIGHT_TOO_MUCH_Z, coach.NIGHT_SECOND_Z), (-0.5, -1.0, -0.5),
   "18b L2: die Schwellen sind nicht die der Entscheidung")
_v = result.get("verdict") or {}
eq(_v.get("key"), "zu_viel", f"18b L2: Nacht bei z {result['night']['hrv']['z']} ist nicht 'zu viel'")
check(_v.get("setting") is True and "Setzung" in str(_v.get("rule")), "18b L2: die Bewertung ist nicht als Setzung beschriftet")
check(_v.get("z_hrv") == result["night"]["hrv"]["z"], "18b L2: z der Nacht steht nicht an der Bewertung")
check(_v.get("z_hrv_next") is not None, "18b L2: die zweite Nacht fehlt, obwohl sie im Bestand liegt")
# (die zweite Nacht wird auf die Basislinie gesetzt - das Rauschen der Fixture
# soll nicht ueber die ODER-Regel entscheiden; die zweite Nacht prueft der Fall darunter)
def _second_flat(d, key):
    a = d["activities"][key]
    n2 = (date.fromisoformat(str(a["start_date_local"])[:10]) + timedelta(days=2)).isoformat()
    d["wellness"][n2]["hrv"] = 49.0
    return d
_mild = coach.night_after(_second_flat(night_history(damp=1.0), hard_keys[-2]), hard_keys[-2])
eq((_mild.get("verdict") or {}).get("key"), "verdaut", f"18b L2: leichte Nacht (z {_mild['night']['hrv']['z']}) nicht 'verdaut'")
_cost = coach.night_after(_second_flat(night_history(damp=3.2), hard_keys[-2]), hard_keys[-2])
eq((_cost.get("verdict") or {}).get("key"), "gekostet", f"18b L2: Nacht bei z {_cost['night']['hrv']['z']} nicht 'gekostet'")
# zweite Nacht (0.69.1, Regel geschaerft): erste Nacht verdaut, zweite unter -0,5
# -> GEKOSTET, verzoegert - nicht mehr "zu viel". Zu viel braucht die erste Nacht:
# unter -1,0, ODER beide Naechte unter -0,5.
_two = night_history(damp=1.0)
_t_act = _two["activities"][hard_keys[-2]]
_n2 = (date.fromisoformat(str(_t_act["start_date_local"])[:10]) + timedelta(days=2)).isoformat()
_two["wellness"][_n2]["hrv"] = 35.0
_tv = coach.night_after(_two, hard_keys[-2]).get("verdict") or {}
eq(_tv.get("key"), "gekostet", f"18b L2: zweite Nacht allein (z {_tv.get('z_hrv_next')}) ist nicht 'gekostet'")
check(_tv.get("delayed") is True and "zweite" in str(_tv.get("label")), "18b L2: verzoegertes 'gekostet' nicht als solches beschriftet")
check(_tv.get("z_hrv_next") is not None and _tv["z_hrv_next"] < -0.5, "18b L2 Fixture: zweite Nacht nicht unter -0,5")
# die Regel total, je Zweig mit Gegenprobe direkt an der Funktion (Wahrheitstafel 0.69.1)
_NV = coach.night_verdict
eq(_NV(-1.01, None).get("key"), "zu_viel", "18b L2 Tafel: erste < -1,0 ist zu viel")
eq(_NV(-1.01, 0.0).get("key"), "zu_viel", "18b L2 Tafel: erste < -1,0 bleibt zu viel, auch bei guter zweiter")
eq(_NV(-0.6, -0.6).get("key"), "zu_viel", "18b L2 Tafel: beide < -0,5 ist zu viel")
eq(_NV(-0.6, -0.4).get("key"), "gekostet", "18b L2 Tafel: erste < -0,5, zweite nicht -> gekostet")
eq(_NV(-0.6, None).get("key"), "gekostet", "18b L2 Tafel: erste < -0,5 ohne zweite -> gekostet")
check(_NV(-0.6, -0.4).get("delayed") is False, "18b L2 Tafel: sofortiges 'gekostet' traegt delayed")
eq(_NV(-0.4, -0.6).get("key"), "gekostet", "18b L2 Tafel: erste >= -0,5, zweite < -0,5 -> gekostet (verzoegert)")
check(_NV(-0.4, -0.6).get("delayed") is True, "18b L2 Tafel: verzoegertes 'gekostet' ohne delayed")
eq(_NV(-0.4, -0.4).get("key"), "verdaut", "18b L2 Tafel: beide >= -0,5 ist verdaut")
eq(_NV(-0.4, None).get("key"), "verdaut", "18b L2 Tafel: erste >= -0,5 ohne zweite ist verdaut")
eq(_NV(-0.5, -0.5).get("key"), "verdaut", "18b L2 Tafel: genau -0,5 liegt noch im Band (>=)")
eq(_NV(-1.0, None).get("key"), "gekostet", "18b L2 Tafel: genau -1,0 ist noch nicht zu viel (<)")
eq(_NV(None, -2.0).get("key"), "unbekannt", "18b L2 Tafel: ohne erste Nacht keine Bewertung, egal wie die zweite liegt")
# SOLLWERT VOM LIVEBESTAND (Johannes, 25.09.): die Nacht nach dem VO2max vom 01.09.
# lag bei -0,23, die zweite bei -0,63. Unter 0.69.0 hiess das "zu viel"; unter der
# geschaerften Regel ist es "gekostet" (verzoegert).
eq(_NV(-0.23, -0.63).get("key"), "gekostet", "18b L2 Livebestand 01.09.: (-0,23 / -0,63) ist nicht 'gekostet'")
check("verz" in str(_NV(-0.23, -0.63).get("label")) or "zweite" in str(_NV(-0.23, -0.63).get("label")),
      "18b L2 Livebestand 01.09.: das Etikett nennt die zweite Nacht nicht")
# letzte Einheit ohne zweite Nacht: Bewertung aus der ersten, die zweite als offen benannt
_last = coach.night_after(base_data, hard_keys[-1]).get("verdict") or {}
check(_last.get("key") in ("verdaut", "gekostet", "zu_viel") and _last.get("z_hrv_next") is None
      and "zweite Nacht" in str(_last.get("note")), "18b L2: ohne zweite Nacht keine Bewertung oder kein Hinweis")
# KEIN EINGANG IN DEN TRAINER: state(), Deckel, Erholung, Urteil lesen die Bewertung nicht
import ast as _ast2  # noqa: E402
_csrc = (Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu" / "coach.py").read_text(encoding="utf-8")
_ctree = _ast2.parse(_csrc)
for _fn in ("state", "state_series", "load_ceiling", "recovery_offered", "assessment", "coach"):
    _src_fn = _ast2.get_source_segment(_csrc, next(n for n in _ast2.walk(_ctree) if isinstance(n, _ast2.FunctionDef) and n.name == _fn))
    check(all(tok not in _src_fn for tok in ("night_after(", "night_verdict(", '"verdict"', "NIGHT_DIGESTED_Z", "NIGHT_TOO_MUCH_Z")),
          f"18b L2: {_fn} liest die Nacht-Bewertung - sie ist nur Anzeige")
_wsrc = (Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu" / "workouts.py").read_text(encoding="utf-8")
check(all(tok not in _wsrc for tok in ("night_after", "night_verdict", '"verdict"', "NIGHT_DIGESTED_Z")),
      "18b L2: workouts liest die Nacht-Bewertung")

# --- 18c  F2 (0.69.2): NACH DEM TRAINING GILT DIE OBERGRENZE VON MORGEN -------------
# Live 25.09. nach einer VO2max-Einheit: die Karten sagten "gelten fuer morgen",
# rechneten aber mit der Obergrenze von HEUTE (Obergrenze 0, "nicht kuerzbar" bis
# zur Regeneration). Eine Stelle entscheidet: coach.session_ceiling - ist heute
# trainiert, liest sie das Budget fuer morgen (heute zaehlt dann zu den sechs
# Tagen davor, F2.10), sonst das heutige Budget bitgenau wie bisher.
import analytics as _an  # noqa: E402
import ast as _ast2  # noqa: E402
_f2 = build()
_f2_today = sorted(_f2["wellness"])[-1]
# (Last 60 wie die uebrigen Fahrten: eine harte Einheit wuerde die Ampel rot machen und
# beide Budgets auf 0 setzen - dann unterschiede die Fixture nichts mehr)
_f2["activities"]["heute"] = {"id": "heute", "start_date_local": _f2_today + "T17:00:00", "type": "Ride",
                              "moving_time": 4500, "icu_intensity": 62, "icu_training_load": 60,
                              "average_heartrate": 140, "icu_average_watts": 135}
# 0.73.1 umgestellt: das Budget kommt aus dem ZUSTAND (coach.week_budget,
# BUDGET_LIGHT), nicht mehr aus readiness().overall/budget.
_f2_state = coach.state(_f2).get("state", "unknown")
_sc = coach.session_ceiling(_f2, _f2_state, _f2_today)
check(_sc.get("for_tomorrow") is True, "18c F2: nach dem Training gilt die Grenze nicht fuer morgen")
_morgen = (date.fromisoformat(_f2_today) + timedelta(days=1)).isoformat()
eq(_sc.get("day"), _morgen, "18c F2: der Tag der Grenze ist nicht morgen")
_soll = coach.load_ceiling(_f2_state, _an.load_budget(_f2, coach.BUDGET_LIGHT[_f2_state], today=_morgen))
eq(_sc.get("ceiling"), _soll["ceiling"], "18c F2: die Grenze ist nicht die von morgen (Budget mit heute in den sechs Tagen)")
_heute = coach.load_ceiling(_f2_state, coach.week_budget(_f2, _f2_state, _f2_today))["ceiling"]
check(_sc.get("ceiling") != _heute, f"18c F2 Trefferzusicherung: morgen ({_sc.get('ceiling')}) = heute ({_heute}) - die Fixture unterscheidet nicht")
check(_sc.get("ceiling") is not None and _heute is not None and _sc["ceiling"] < _heute,
      "18c F2 Richtung: die heutige Fahrt zaehlt fuer morgen zu den sechs Tagen - die Grenze muss sinken")
check((_sc.get("used_today") or 0) == 0.0, "18c F2: fuer morgen ist noch nichts verbraucht")
# GEGENPROBE: vor dem Training - heutiges Budget, bitgenau wie load_ceiling
_g2 = build(); _g2_today = sorted(_g2["wellness"])[-1]
_g2_state = coach.state(_g2).get("state", "unknown")
_gsc = coach.session_ceiling(_g2, _g2_state, _g2_today)
check(_gsc.get("for_tomorrow") is False, "18c F2 Gegenprobe: ohne Training heute 'fuer morgen'")
eq({k: v for k, v in _gsc.items() if k not in ("for_tomorrow", "day")}, coach.load_ceiling(_g2_state, coach.week_budget(_g2, _g2_state, _g2_today)),
   "18c F2 Gegenprobe: vor dem Training weicht die Grenze von load_ceiling ab")
# GEGENPROBE: unter 28 Tagen kein Budget, trainiert oder nicht
_k2 = build(days=20); _k2_today = sorted(_k2["wellness"])[-1]
_k2["activities"]["heute"] = dict(_f2["activities"]["heute"], start_date_local=_k2_today + "T17:00:00")
_ksc = coach.session_ceiling(_k2, "ready", _k2_today)
eq((_ksc.get("for_tomorrow"), _ksc.get("budget")), (True, None), "18c F2: unter 28 Tagen erfindet morgen ein Budget")
# EIN ERZEUGER: die beiden Handler (Trainer-Karten, Wochenplan) lesen session_ceiling,
# nicht load_ceiling direkt - sonst rechnet einer weiter mit heute.
_wsrc2 = (Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu" / "websocket.py").read_text(encoding="utf-8")
_wtree2 = _ast2.parse(_wsrc2)
for _hn in ("websocket_workouts", "websocket_goal"):
    _hsrc = _ast2.get_source_segment(_wsrc2, next(n for n in _ast2.walk(_wtree2) if isinstance(n, _ast2.FunctionDef) and n.name == _hn))
    check("session_ceiling(" in _hsrc and "load_ceiling(" not in _hsrc,
          f"18c F2: {_hn} liest nicht session_ceiling (oder noch load_ceiling direkt)")

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
long_dec = long_ctx["metrics"]["decoupling"]
check(not long_dec["enough"],
      "21 einordnung: Langfahrt gegen Kurzeinheiten verglichen")
# Two reasons for "no group", two sentences. This one HAS predecessors - the
# caliper simply never fills. The other case below has none at all, and they
# must not get the same wording: the first does not heal, the second does.
eq(long_dec["why"], "too_few", "21 einordnung: Langfahrt als 'zu früh' abgetan")
check("weitesten Stufe" in long_dec["say"], "21 einordnung: die erreichte Stufe fehlt im Satz")
# a run must never be compared against rides
mixed["activities"]["run"] = {
    "id": "run", "start_date_local": day(-1) + "T09:00", "type": "Run",
    "icu_training_load": 60.0, "icu_intensity": 62.0, "moving_time": 3600,
    "decoupling": 3.0, "average_heartrate": 140.0,
}
eq(coach.session_context(mixed, "run")["earlier"], 0,
   "21 einordnung: Lauf gegen Radfahrten verglichen")
# only sessions BEFORE this one count - no peeking into the future
early = coach.session_context(rides, "r2")
check(early["earlier"] <= 2, f"21 einordnung: spätere Einheiten im Vergleich ({early['earlier']})")
early_dec = early["metrics"]["decoupling"]
eq(early_dec["why"], "too_early", "21 einordnung: dünner Anfang als 'zu wenige vergleichbare' abgetan")
check("zu früh" in early_dec["say"], "21 einordnung: der Anfangsfall bekommt nicht seinen eigenen Satz")
# Fixture-Beweis: die beiden dünnen Fälle sind unterscheidbar, sonst prüfen die
# beiden Zusicherungen oben dieselbe Sache zweimal.
check(early_dec["why"] != long_dec["why"] and early_dec["say"] != long_dec["say"],
      "21 einordnung: Fixture-Beweis - die beiden Dünn-Gründe sind nicht unterscheidbar")

# --- 21b  the caliper: narrowest step that fills, and reciprocal -------------
cal = coach.session_context(rides, "r39")
dec39 = cal["metrics"]["decoupling"]
check(dec39["enough"], "21b caliper: keine Einordnung trotz voller Historie")
check(dec39["stage"] in cal["stages"], "21b caliper: gegriffene Stufe ist keine der Stufen")
# The chosen step must be the NARROWEST that reaches the minimum - a wider one
# that also works would quietly buy peers with worse matches.
narrower = [st for st in cal["stages"] if st < dec39["stage"]]
for step in narrower:
    values = []
    for key, other in rides["activities"].items():
        if key == "r39" or str(other["start_date_local"])[:10] >= str(
                rides["activities"]["r39"]["start_date_local"])[:10]:
            continue
        if abs(other["icu_intensity"] - 62.0) > step * cal["sd_intensity"]:
            continue
        values.append(other["decoupling"])
    check(len(values) < cal["min_peers"],
          f"21b caliper: engere Stufe {step} hätte gereicht, genommen wurde {dec39['stage']}")
# Never a symmetric plus/minus on the duration - the log caliper is asymmetric
# in percent, and a single "±" is a lie in one direction.
check(dec39["duration_low_pct"] <= 0 <= dec39["duration_high_pct"],
      "21b caliper: die Dauerspanne liegt nicht um die Einheit herum")
check(abs(dec39["duration_low_pct"]) != dec39["duration_high_pct"]
      or dec39["duration_high_pct"] == 0.0,
      "21b caliper: Spanne symmetrisch ausgewiesen, obwohl auf dem Logarithmus gerechnet")

# Reciprocity: if A is a comparison partner of B, then B is one of A. The old
# rule measured the tolerance against the CURRENT session's duration, so it was
# not - and nothing would have noticed.
spread = ride_history()
for index, act in enumerate(spread["activities"].values()):
    act["moving_time"] = 2400 + index * 120
    act["icu_intensity"] = 62.0


def partner(data, left, right):
    """True when `right` falls inside `left`'s caliper, ignoring the date."""
    import math as _math
    ctx_left = coach.session_context(data, left)
    stage = ctx_left["metrics"]["decoupling"].get("stage") or ctx_left["stages"][-1]
    a = data["activities"][left]["moving_time"] / 60
    b = data["activities"][right]["moving_time"] / 60
    return abs(_math.log(a) - _math.log(b)) <= stage * ctx_left["sd_log_duration"]


pairs = [("r10", "r30"), ("r5", "r20"), ("r12", "r13")]
for left, right in pairs:
    check(partner(spread, left, right) == partner(spread, right, left),
          f"21b caliper: {left}/{right} ist einseitig Vergleichspartner")
check(any(partner(spread, a, b) for a, b in pairs),
      "21b caliper: Fixture-Beweis - kein einziges Paar liegt im Fenster, "
      "die Gegenseitigkeit wäre nur zufällig erfüllt")
check(coach.session_context(rides, "nope")["available"] is False,
      "21 einordnung: unbekannte Einheit ausgewertet")

# --- 22  the day's load comes from the activities ------------------------------
# Reading it from the wellness row reported "0 load in seven days" on a week
# that contained a ride and a walk - that field is simply not filled on every
# account, and the activities always are.
noload = night_history()
for row in noload["wellness"].values():
    row.pop("load", None)
today_view = coach.today(noload)  # 0.73.1: kein Budget von aussen mehr
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
quiet = coach.today(empty)
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


# S1 (0.69.0): das Band lebt in baseline.py (ein Erzeuger fuer Trainer, Ampel und
# Signale); coach.py behaelt _norm_band/_z_at/_z_series als Namen, die dorthin
# durchreichen. _band ruft in coach.py nur noch night_after.
_band_callers = _callers_of("_band")
eq(_band_callers, {"night_after"},
   "29 primitive: _band wird außerhalb von night_after gerufen — "
   "eine Basislinie rechnet am Rechenweg vorbei")
check(coach._norm_band is coach.baseline.norm_band, "29 primitive (S1): coach._norm_band ist nicht das eine Band aus baseline.py")
_norm_callers = _callers_of("_norm_band")
for required in ("state", "_night_z", "_signal_bands"):
    check(required in _norm_callers,
          f"29 primitive: {required} ruft _norm_band nicht — eigener Rechenweg")
# _z_series reicht seit S1 an baseline.z_series durch - derselbe Rechenweg,
# eine Datei weiter; ein eigener Rechenweg in coach.py waere ein Rueckfall.
check("baseline.z_series(" in _COACH_SRC.split("def _z_series")[1].split("def state_series")[0],
      "29 primitive: _z_series rechnet in coach.py statt in baseline.py")

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
# 0.70.0 UMGESTELLT: der Zustand traegt den Kurzsatz `short` (Zustandszeile A2).
# Benannt geprueft, dann AUS der Pruefsumme genommen - so haelt die alte Summe
# weiter fest, dass sich sonst nichts bewegt hat.
eq(_st30.get("short"), coach.STATE_SHORT.get(_st30.get("state")), "30 referenz: der Kurzsatz kommt aus STATE_SHORT")
check(bool(_st30.get("short")), "30 referenz: der Zustand traegt keinen Kurzsatz")
_st30 = {k: v for k, v in _st30.items() if k != "short"}
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
# unabhängige Nachrechnung des gewichteten Mittels (Log-Skala, Fenster VOR heute -
# seit S1 wie im Urteil; bis 0.68.0 zaehlte die Anzeige die heutige Nacht mit)
_w31 = ctx_build(True)["wellness"]
_c31 = ctx_build(True)["day_context"]
_d31 = sorted(_w31)[:-1][-60:]
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


# --- recovery_offered: the setting behind the stimulus grade (ausbau.md I7) ----
# Three conditions, and each one has to be able to fail ON ITS OWN - otherwise
# the rule is only ever proven by the state and the other two ride along unseen.
def recovery_case(quiet_load=8.0, base_load=50.0, hard=False, hrv=50.0, rhr=56.0):
    """A healthy history with an explicit daily load, quiet at the end."""
    data = build(days=120, hrv=hrv, rhr=rhr)
    order = sorted(data["wellness"])
    for index, day_key in enumerate(order):
        remaining = len(order) - 1 - index
        data["wellness"][day_key]["ctlLoad"] = quiet_load if remaining < 2 else base_load
    if hard:
        last = order[-1]
        data["activities"]["hard"] = {
            "id": "hard", "start_date_local": last + "T09:00:00", "type": "Ride",
            "moving_time": 3600, "icu_intensity": 88, "icu_training_load": 95,
        }
    return data


calm = coach.recovery_offered(recovery_case())
check(calm["offered"] is True, f"erholung: ruhiger Bestand gilt nicht als erholt ({calm['missing']})")
check(calm["state"] == "ready", f"erholung: Grundfall ist nicht im Zustand ready ({calm['state']})")
check(calm["hard_days_last_7"] == 0, "erholung: Grundfall zählt harte Tage")
check(calm["recent_daily_load"] is not None and calm["chronic_daily_load"] is not None,
      "erholung: die beiden Lastzahlen fehlen in der Payload")
check(calm["recent_daily_load"] < calm["chronic_daily_load"],
      "erholung: der ruhige Fall liegt nicht unter dem chronischen Schnitt")
check(not calm["missing"], f"erholung: erfüllter Fall nennt trotzdem Gründe ({calm['missing']})")

# 1 - the load of the last days is NOT below the chronic mean
loud = coach.recovery_offered(recovery_case(quiet_load=140.0))
check(loud["offered"] is False, "erholung: laute letzte Tage gelten als erholt")
check(any("chronischen" in reason for reason in loud["missing"]),
      f"erholung: der Lastgrund wird nicht benannt ({loud['missing']})")
check(loud["state"] == "ready", "erholung: der Lastfall verändert den Zustand — Fall untauglich")

# 2 - a hard day inside the last seven
hard = coach.recovery_offered(recovery_case(hard=True))
check(hard["offered"] is False, "erholung: harter Tag in der Woche gilt als erholt")
check(hard["hard_days_last_7"] >= 1, "erholung: der harte Tag wird nicht gezählt")
check(any("harte" in reason or "harter" in reason for reason in hard["missing"]),
      f"erholung: der harte Tag wird nicht benannt ({hard['missing']})")

# 3 - the state itself
dip = recovery_case()
for offset in range(3):
    key = (TODAY - timedelta(days=offset)).isoformat()
    dip["wellness"][key].update({"hrv": 26.0, "restingHR": 68.0})
slumped = coach.recovery_offered(dip)
check(slumped["offered"] is False, "erholung: Einbruch gilt als erholt")
check(any("Zustand" in reason for reason in slumped["missing"]),
      f"erholung: der Zustand wird nicht als Grund benannt ({slumped['missing']})")

# the thresholds are CHOSEN, and the payload says so - the same honesty the
# load budget shows about its target ratio per traffic light
check(calm["quiet_days"] == const.RECOVERY_QUIET_DAYS,
      "erholung: die Tageszahl kommt nicht aus const.py")
check(calm["max_hard_days_7"] == const.RECOVERY_MAX_HARD_DAYS_7,
      "erholung: die Grenze für harte Tage kommt nicht aus const.py")
check("Setzung" in calm["note"] and "gewählt" in calm["note"],
      "erholung: die Schwellen werden nicht als Setzung beschriftet")
check(str(const.RECOVERY_QUIET_DAYS) in calm["note"],
      "erholung: die Zahl steht nicht im Text, der sie erklärt")

# a thin archive says so instead of guessing
thin = coach.recovery_offered({"wellness": {}, "activities": {}})
check(thin["offered"] is False, "erholung: leerer Bestand gilt als erholt")
check(thin["chronic_daily_load"] is None, "erholung: chronischer Schnitt aus dem Nichts")

# and the one that matters for error class 3: the daily load comes from
# analytics, not from a second walk over the activities
source = (Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"
          / "coach.py").read_text(encoding="utf-8")
recovery_src = source[source.index("def recovery_offered("):]
recovery_src = recovery_src[:recovery_src.index("\ndef ", 10)]
check("analytics.daily_load" in recovery_src,
      "erholung: rechnet die Tageslast selbst statt sie zu holen")
check('data.get("activities")' not in recovery_src,
      "erholung: läuft selbst über die Aktivitäten — zweiter Rechenweg")
# Gegenprobe: der Wächter muss einen wiedereingebauten Durchlauf auch finden
check('data.get("activities")' in recovery_src + '\nfor a in data.get("activities"): pass',
      "erholung Gegenprobe: der Wächter findet einen eingebauten Durchlauf nicht")


# --- S2 · EINE Tageslast (Sollzustand S2, Messung M-S2 vom 24.09.) -------------
# Vier Wege rechneten die Tageslast: analytics.daily_load (ctlLoad, Luecken 0),
# coach._acwr_local (ctlLoad -> load, keine Luecken), coach._day_load
# (Aktivitaeten -> load), Plan/Kalender-Woche (Aktivitaetssumme). Am Livebestand
# sind ctlLoad und Aktivitaetssumme an 60 von 60 Tagen gleich - die Wahl ist
# Bauhygiene: EIN Erzeuger, analytics.daily_load. Die Fixture stellt beide
# Reihen absichtlich VERSCHIEDEN, damit jeder Leser zeigt, wen er liest.
import analytics as _an  # noqa: E402
_d2 = {"wellness": {}, "activities": {}, "dfa": {}, "section_marks": {}, "settings": {}, "goal": {}}
import datetime as _dt
_base = _dt.date(2026, 8, 1)
for i in range(40):
    d = (_base + _dt.timedelta(days=i)).isoformat()
    _d2["wellness"][d] = {"ctlLoad": 50 + i, "load": 999, "hrv": 60, "restingHR": 50, "ctl": 40, "atl": 40}
    if i % 2 == 0:
        _d2["activities"][f"a{i}"] = {"start_date_local": d + "T08:00:00", "icu_training_load": 5, "moving_time": 3600,
                                      "type": "Ride", "icu_intensity": 60, "name": "x"}
# ein Tag ohne ctlLoad: der Erzeuger faellt auf die Aktivitaetssumme des Tages
# (5) zurueck, der alte Signale-Weg nahm wellness.load (999)
_d2["wellness"][(_base + _dt.timedelta(days=36)).isoformat()]["ctlLoad"] = None
check({r["date"]: r["load"] for r in _an.daily_load(_d2)}[(_base + _dt.timedelta(days=36)).isoformat()] == 5.0,
      "S2 Regel: ohne ctlLoad zaehlt die Aktivitaetssumme des Tages")
_today = (_base + _dt.timedelta(days=39)).isoformat()
_erz = {r["date"]: r["load"] for r in _an.daily_load(_d2)}
check(_erz[_today] == 89 and _erz[(_base + _dt.timedelta(days=38)).isoformat()] == 88, "S2 Fixture: der Erzeuger liest ctlLoad")
# 1 · Heute-Reiter: die Tageslast der letzten 7 Tage kommt vom Erzeuger
_t = coach.today(_d2) if "coach" in globals() else None
_recent = {r["date"]: r["load"] for r in (_t or {}).get("recent") or []}
eq(_recent.get(_today), 89, "S2 Treffer Heute: die Tageslast ist die des Erzeugers (ctlLoad), nicht die Aktivitaetssumme")
# 2 · Signale-Reiter: dasselbe Verhaeltnis wie die readiness - EINE Funktion (0.74.1 B4: analytics.window_ratio)
_sig = coach.signals(_d2)
_ac_sig = {r["date"]: r.get("acwr") for r in _sig.get("days") or []}
_wr = getattr(_an, "window_ratio", None)
eq(_ac_sig.get(_today), _wr(_d2, _today) if callable(_wr) else "FEHLT", "S2 Treffer Signale: das Verhaeltnis ist das von window_ratio")
# 0.74.1 B4: an JEDEM Tag der Signale derselbe Wert wie window_ratio; die Fixture muss den alten
# Schnitt (inklusive des Tages) vom neuen (vor dem Tag) unterscheiden, sonst prueft das nichts.
def _alt_ratio(data, day):
    rows = [r for r in _an.daily_load(data) if r["date"] <= day]
    if len(rows) < 28:
        return None
    ld = [r["load"] for r in rows]
    c = sum(ld[-28:]) / 28
    return round((sum(ld[-7:]) / 7) / c, 2) if c else None
_d3 = _json.loads(_json.dumps(_d2)) if "_json" in globals() else __import__("json").loads(__import__("json").dumps(_d2))
for _k in (32, 36, 39):
    _d3["wellness"][(_base + _dt.timedelta(days=_k)).isoformat()]["ctlLoad"] = 260.0
_sig3 = {r["date"]: r.get("acwr") for r in coach.signals(_d3).get("days") or []}
_mis = [d for d, v in _sig3.items() if callable(_wr) and v != _wr(_d3, d)]
check(callable(_wr) and not _mis, f"0.74.1 B4: Signale weichen von window_ratio ab ({_mis[:3]})")
_diff = [d for d, v in _sig3.items() if v is not None and _alt_ratio(_d3, d) is not None and _alt_ratio(_d3, d) != v]
check(len(_diff) >= 3, f"0.74.1 B4 Fixture: alter und neuer Schnitt unterscheiden sich an zu wenigen Tagen ({len(_diff)})")
_rd3 = next((c["value"] for c in _an.readiness(_d3)["components"] if c["id"] == "acwr"), None)
_last3 = sorted(_d3["wellness"])[-1]
check(_rd3 is not None and _rd3 == _sig3.get(_last3) == (_wr(_d3, _last3) if callable(_wr) else None),
      f"0.74.1 B4: readiness ({_rd3}), Signale ({_sig3.get(_last3)}) und window_ratio am selben Tag verschieden")
_csrc = Path(coach.__file__).read_text(encoding="utf-8") if "Path" in globals() else open(coach.__file__, encoding="utf-8").read()
_sbody = _csrc[_csrc.index("def signals("):]; _sbody = _sbody[:_sbody.index("\ndef ", 10)]
check("window_ratio(" in _sbody and "acwr_series" not in _sbody and "mean(" not in _sbody,
      "0.74.1 B4 AST: signals rechnet das Verhaeltnis nicht ueber window_ratio")
# 3 · Kalender-Woche: die Wochenlast ist die Summe der Tageslasten des Erzeugers
_cal = _an.calendar_days(_d2, [])
_wk = [w for w in (_cal.get("weeks") or []) if w.get("start") and w["start"] <= _today][-1] if (_cal.get("weeks") or []) else None
_tage = [r for r in _an.daily_load(_d2) if _wk and _wk["start"] <= r["date"] < (_dt.date.fromisoformat(_wk["start"]) + _dt.timedelta(days=7)).isoformat()]
eq(_wk["load"] if _wk else None, float(sum(r["load"] for r in _tage)), "S2 Treffer Kalender: die Wochenlast ist die Summe der Tageslasten")

# --- 32 · S1: EINE HRV-Basislinie fuer Trainer, Ampel und Signale (0.69.0) ---
# Bis 0.68.0 rechnete signals() seine z-Reihe ungewichtet (Karte 4b, F4b.3):
# am ctx_build-Bestand lag heute (44 ms) im Signale-Reiter unauffaellig, beim
# Trainer im Einbruch. Jetzt liest signals() dieselben Gewichte.
_sg = coach.signals(ctx_build(True))
_su = coach.signals(ctx_build(False))
_zg = (_sg["days"][-1].get("z") or {}).get("hrv")
_zu = (_su["days"][-1].get("z") or {}).get("hrv")
check(_zg is not None and _zu is not None, "32 S1 Fixture: Signale ohne z-Wert fuer heute")
check(_zg is not None and _zu is not None and _zg < _zu - 0.5,
      f"32 S1: Signale rechnen ungewichtet (z heute gewichtet {_zg}, ungewichtet {_zu})")
check(_zg is not None and _zg <= -2.0, f"32 S1: der gewichtete Einbruch (state slump) steht nicht in den Signalen ({_zg})")
# Gleichlauf mit dem Trainer: dieselbe Zahl wie coach.today (Band heute)
_tz = {x["key"]: x["z"] for x in coach.today(ctx_build(True))["signals"]}.get("hrv")
check(_tz is not None and _zg is not None and abs(_tz - _zg) < 0.02,
      f"32 S1: Signale ({_zg}) und Heute-Reiter ({_tz}) nennen zwei z-Werte fuer dieselbe Nacht")

# --- 0.70.0 · C4: "höchstens 0 harte Tage" ----------------------------------------
check("höchstens 0" not in calm["note"], f"C4: der Satz sagt noch 'höchstens 0 harte Tage' ({calm['note'][:120]})")
check("kein harter Tag" in calm["note"], "C4: der Satz sagt nicht 'kein harter Tag' bei der Grenze 0")
check(f"{const.RECOVERY_QUIET_DAYS} Tage" in calm["note"] and "Setzung" in calm["note"],
      "C4 Gegenprobe: der Rest des Satzes (ruhige Tage, Setzung) ist verloren")

# --- 0.72.1 · die Nachtbewertung liest das Tagesetikett (Skizze 0.72.1) ---------
# EIN Erzeuger: day_context.weight_for. Nur Anzeige - keine Vorgabe liest das.
import copy as _cp
import day_context as _dc
_K = hard_keys[-2]
_base = coach.night_after(base_data, _K)
_ref_sha = hashlib.sha256(json.dumps(_base, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
eq(_ref_sha, "c9bb94f983b78a6dfa6bee69e32144c90444429c89d144c420d1f2e47681d305",
   "0.72.1 Gegenprobe: Nacht ohne Etikett nicht bitgenau wie 0.72.0")
_act_day = str(base_data["activities"][_K]["start_date_local"])[:10]
_n1 = (date.fromisoformat(_act_day) + timedelta(days=1)).isoformat()
_n2 = (date.fromisoformat(_act_day) + timedelta(days=2)).isoformat()
def _tagged(day_iso, tag, weight=None):
    d = _cp.deepcopy(base_data)
    _dc.set_entry(d, day_iso, tag, weight)
    return coach.night_after(d, _K)
# 1 · erste Nacht mit Etikett (Gewicht < 1): kein Urteil, Grund in einem Satz, Rohwerte bleiben
_a = _tagged(_n1, "alkohol")
_satz = f"Nacht zum {_n1[8:10]}.{_n1[5:7]}. mit Etikett Alkohol, Gewicht 0,5 — sie misst nicht nur die Einheit"
eq((_a.get("verdict") or {}).get("key"), "nicht_bewertbar", "0.72.1 1: erste Nacht mit Alkohol wird bewertet")
check(_satz in str((_a.get("verdict") or {}).get("label")), f"0.72.1 1: der Grund-Satz fehlt am L2-Urteil ({(_a.get('verdict') or {}).get('label')})")
eq(_a.get("state"), "unrated", "0.72.1 1: der Vergleich mit frueheren Einheiten urteilt trotz Etikett")
check(_satz in str(_a.get("headline")), "0.72.1 1: der Grund-Satz fehlt am Vergleich")
# (die zweite Nacht darf sich bewegen: das Etikett der ersten geht - wie seit S1 - gewichtet in
# IHRE Basislinie der 60 Naechte davor ein; geprueft wird, dass der Rohwert dasteht)
eq((_a["night"], (_a["verdict"] or {}).get("z_hrv")), (_base["night"], _base["verdict"]["z_hrv"]),
   "0.72.1 1: die Rohwerte der Nacht sind weg oder veraendert")
check((_a["verdict"] or {}).get("z_hrv_next") is not None, "0.72.1 1: der Rohwert der zweiten Nacht ist weg")
# 1 · nur die zweite Nacht mit Etikett -> ebenfalls nicht bewertbar
_b = _tagged(_n2, "krank")
eq(((_b.get("verdict") or {}).get("key"), _b.get("state")), ("nicht_bewertbar", "unrated"), "0.72.1 1: zweite Nacht mit Etikett wird bewertet")
check("Etikett Krank, Gewicht 0" in str((_b.get("verdict") or {}).get("label")) and f"Nacht zum {_n2[8:10]}.{_n2[5:7]}." in str((_b.get("verdict") or {}).get("label")),
      "0.72.1 1: der Satz nennt die zweite Nacht nicht")
# Gegenproben: Normal (1,0) unveraendert; Alkohol mit Gewicht 1,0 zaehlt als Gewicht 1 -> unveraendert;
# Gewicht 0,75 -> nicht bewertbar; Etikett am Tag der Einheit (Nacht davor) -> Urteil unveraendert
_c = _tagged(_n1, "normal")
eq(hashlib.sha256(json.dumps(_c, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), _ref_sha,
   "0.72.1 Gegenprobe: Etikett Normal veraendert die Nachtbewertung")
eq((_tagged(_n1, "alkohol", 1.0).get("verdict") or {}).get("key"), _base["verdict"]["key"], "0.72.1 Gegenprobe: Gewicht 1,0 macht die Nacht unbewertbar")
eq((_tagged(_n1, "reise", 0.75).get("verdict") or {}).get("key"), "nicht_bewertbar", "0.72.1: Gewicht 0,75 wird bewertet")
_d = _tagged(_act_day, "nachtschicht")
eq(((_d.get("verdict") or {}).get("key"), _d.get("state")), (_base["verdict"]["key"], _base["state"]),
   "0.72.1 Gegenprobe: ein Etikett am Tag der Einheit (Nacht davor) veraendert das Urteil")
# 2 · Referenz sauber: eine Folgenacht eines frueheren Peers mit Etikett zaehlt nicht
_peer_nights = sorted({(date.fromisoformat(str(base_data["activities"][k]["start_date_local"])[:10]) + timedelta(days=1)).isoformat()
                       for k in hard_keys if str(base_data["activities"][k]["start_date_local"])[:10] < _act_day})
_e = _tagged(_peer_nights[-1], "alkohol")
eq(_e["reference"]["hrv"]["n"], _base["reference"]["hrv"]["n"] - 1, "0.72.1 2: ein Peer mit Etikett zaehlt in die Vergleichsgruppe")
_f = _cp.deepcopy(base_data)
for _pn in _peer_nights[:-4]:
    _dc.set_entry(_f, _pn, "reise")
_fr = coach.night_after(_f, _K)
eq((_fr.get("reference") or {}).get("hrv"), None, "0.72.1 2: mit vier sauberen Peers entsteht trotzdem eine Referenz")
eq(_fr.get("state"), "unknown", "0.72.1 2 Gegenprobe: unter fuenf Peers nicht 'kein Vergleich möglich'")
check(_fr["verdict"]["key"] == _base["verdict"]["key"], "0.72.1 2: die Peers veraendern das L2-Urteil (das liest keine Peers)")
# 3 · das Etikett Cannabis
_cb = _dc.TAGS.get("cannabis") or {}
eq((_cb.get("label"), _cb.get("weight"), _cb.get("read")),
   ("Cannabis", 0.5, "akuter Stressor, senkt die nächtliche HRV — der Wert bleibt echt"), "0.72.1 3: Etikett Cannabis fehlt oder falsch")
check(all(t in str(_cb.get("source")) for t in ("Gonzalez et al. 2026", "J Sleep Res", "10.1111/jsr.70298", "PMID 41692699", "Setzung")),
      "0.72.1 3: der Beleg am Etikett Cannabis fehlt oder nennt die Setzung nicht")
_alte = {k: v for k, v in _dc.TAGS.items() if k != "cannabis"}
eq(hashlib.sha256(json.dumps(_alte, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
   "ee6d9bc3847b5217b51d79defc275d9cdf94034cc3261a0a28bc74fec45628de", "0.72.1 3: ein vorhandenes Etikett wurde veraendert")
_g = _tagged(_n1, "cannabis") if "cannabis" in _dc.TAGS else {}
check("Etikett Cannabis, Gewicht 0,5" in str((_g.get("verdict") or {}).get("label")), "0.72.1 3: eine Cannabis-Nacht wird bewertet")
# Nur Anzeige: der Trainer (coach(), state) liest weight_for nicht zusaetzlich - kein neuer Eingang
_src_all = (Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu" / "coach.py").read_text(encoding="utf-8")
_fn_na = _src_all[_src_all.index("def night_after"):_src_all.index("def night_after") + 6000]
check("day_context.weight_for(" in _fn_na, "0.72.1: night_after fragt nicht day_context.weight_for (ein Erzeuger)")


# --- 0.73.0 · Heute-Kopf: bound_by, das Fenster im Heute-Payload, der Satz -------
import analytics as _an73  # noqa: E402
import copy as _cp73  # noqa: E402
_b140 = {"recommended": 140, "used_today": 0.0}
eq(coach.load_ceiling("ready", _b140).get("bound_by"), "week", "0.73.0 4: ready ohne Deckel -> die Woche begrenzt")
eq(coach.load_ceiling("strained", _b140).get("bound_by"), "state", "0.73.0 4: strained 75 < 140 -> der Zustand begrenzt")
eq(coach.load_ceiling("strained", {"recommended": 40}).get("bound_by"), "week", "0.73.0 4: strained 75 > 40 -> die Woche begrenzt")
eq(coach.load_ceiling("strained", {"recommended": 75}).get("bound_by"), "week", "0.73.0 4 Rand: Gleichstand -> die Woche (Zustand bremst nicht staerker)")
eq(coach.load_ceiling("slump", {"recommended": 0}).get("bound_by"), "week", "0.73.0 4 Rand: beide 0 -> die Woche")
eq(coach.load_ceiling("slump", {"recommended": 10}).get("bound_by"), "state", "0.73.0 4: slump 0 < 10 -> Zustand")
eq(coach.load_ceiling("strained", None).get("bound_by"), "state", "0.73.0 4: ohne Budget, mit Deckel -> Zustand")
eq(coach.load_ceiling("ready", None).get("bound_by"), None, "0.73.0 4: ohne Budget, ohne Deckel -> keine Grenze")
eq(coach.load_ceiling("unknown", None).get("bound_by"), None, "0.73.0 4: unbekannt ohne Budget -> keine Grenze")
eq({k: v for k, v in coach.load_ceiling("strained", _b140).items() if k != "bound_by"},
   {"ceiling": 75, "capacity": "Grundlage", "capacity_text": "Beansprucht — Umfang ja, Intensität nein.",
    "cap_load": 75, "budget": 140, "used_today": 0.0}, "0.73.0 4: die Rechnung der Obergrenze ist unveraendert")
# das Fenster im Heute-Payload: dieselben Tage wie das Budget
_h73 = night_history()
_days73 = sorted(_h73["wellness"])
_last73 = _days73[-1]
for _a in _h73["activities"].values():   # heute nicht trainiert -> Modus heute
    if str(_a.get("start_date_local") or "")[:10] == _last73:
        _a["start_date_local"] = _days73[-2] + "T08:00:00"
_st73 = coach.state(_h73)["state"]
# 0.73.1 umgestellt: das Budget des Heute-Payloads entsteht in coach (week_budget), nicht draussen
_bud73 = coach.week_budget(_h73, _st73, _last73)
check(_bud73 is not None, "0.73.0 Fixture: night_history traegt ein Budget")
_t73 = coach.today(_h73, day=_last73)
_wk73 = _t73.get("week") or {}
eq(_wk73.get("mode"), "today", "0.73.0 5.4: ohne Fahrt heute gilt der Modus heute")
eq(_t73["week_load"], round((_bud73 or {}).get("window_load", -1)), "0.73.0 5.4: week_load == window_load bei lueckenlosen Tagen")
eq(round(sum(x["load"] for x in _wk73.get("sessions") or []), 1), (_bud73 or {}).get("window_load"),
   "0.73.0 5.2: die Fahrten im Heute-Payload ergeben die Fensterlast")
eq((_wk73.get("budget") or {}).get("window_allowed"), (_bud73 or {}).get("window_allowed"), "0.73.0/0.73.1: das Budget im Heute-Payload ist das aus week_budget")
eq(_wk73.get("bound_by"), coach.load_ceiling(_t73["state"], _bud73).get("bound_by", "fehlt"), "0.73.0 4: bound_by im Heute-Payload aus load_ceiling")
eq(_t73.get("ceiling"), coach.load_ceiling(_t73["state"], _bud73)["ceiling"], "0.73.0: die Obergrenze des Heute-Reiters unveraendert")
# Morgen-Modus: heute schon trainiert -> das Fenster von morgen (dieselbe Stelle wie session_ceiling)
_m73 = _cp73.deepcopy(_h73)
_m73["activities"]["heute73"] = {"start_date_local": _last73 + "T07:00:00", "type": "Ride", "name": "heute",
                                 "moving_time": 3600, "icu_training_load": 50}
_tm73 = coach.today(_m73, day=_last73)
_wm73 = _tm73.get("week") or {}
_sc73 = coach.session_ceiling(_m73, _tm73["state"], _last73)
eq(_wm73.get("mode"), "tomorrow", "0.73.0: heute trainiert -> Modus morgen")
eq((_wm73.get("budget") or {}).get("window_end"), _sc73.get("day"), "0.73.0: Morgen-Fenster endet am Tag von session_ceiling")
eq(_wm73.get("ceiling"), _sc73.get("ceiling"), "0.73.0: Morgen-Grenze = die der Trainer-Karten")
check(any(x.get("name") == "heute" for x in _wm73.get("sessions") or []), "0.73.0: im Morgen-Fenster steht die heutige Fahrt")
# ohne Budget (unter 28 Tagen): Liste trotzdem, Budget None
_tn73 = coach.today(night_history(days=20))  # 0.73.1: unter 28 Tagen statt Budget None von aussen
eq((_tn73.get("week") or {}).get("budget"), None, "0.73.0 Budget None: kein Budget im Heute-Payload")
check(isinstance((_tn73.get("week") or {}).get("sessions"), list), "0.73.0 Budget None: die Fahrtenliste steht trotzdem")
# Events aus dem Koordinator werden durchgereicht
check("events" in __import__("inspect").signature(coach.today).parameters, "0.73.0: coach.today nimmt die Events des Koordinators")

# 6 · der Satz: "weicht/weichen ungünstig ab", nicht "liegt unter" (Ruhepuls 59 > Basis 56)
_state_saved73, _nz_saved73 = coach.state, coach._night_z
def _nz(labels):
    return lambda data, day: {k: {"label": l, "unit": u, "value": 1, "baseline": 1, "z": -1.0}
                              for k, l, u in labels}
try:
    coach.state = lambda data, **kw: {"state": "ready", "label": "", "text": ""}
    coach._night_z = _nz([("hrv", "HRV", "ms"), ("rhr", "Ruhepuls", "bpm")])
    _two = coach.today(_h73, day=_last73).get("tension") or ""
    coach._night_z = _nz([("rhr", "Ruhepuls", "bpm")])
    _one = coach.today(_h73, day=_last73).get("tension") or ""
finally:
    coach.state, coach._night_z = _state_saved73, _nz_saved73
check(_two.startswith("HRV und Ruhepuls weichen heute ungünstig von deiner Basislinie ab — aber weder weit genug noch "),
      f"0.73.0 6: zwei Signale -> Plural 'weichen ... ab': {_two[:90]!r}")
check(_one.startswith("Ruhepuls weicht heute ungünstig von deiner Basislinie ab — aber weder weit genug noch "),
      f"0.73.0 6: ein Signal -> 'weicht ... ab': {_one[:90]!r}")
check("liegt heute unter" not in _two + _one, "0.73.0 6: 'liegt heute unter' steht noch")
check(_one.endswith("Wenn es morgen wieder so aussieht, ist es keins mehr."), "0.73.0 6: der Rest des Satzes ist unveraendert")
check("Die Regel entscheidet über das Mittel der letzten drei Tage" in _one, "0.73.0 6: der Rest des Satzes (Mitte) ist unveraendert")


# --- 0.73.1 · 2.1 das Wochenziel folgt dem Zustand (BUDGET_LIGHT, ein Weg) ------
eq(getattr(coach, "BUDGET_LIGHT", None),
   {"ready": "green", "strained": "amber", "elevated": "amber", "recovering": "amber",
    "rebound": "amber", "slump": "red", "unknown": "unknown"}, "0.73.1 2.1: BUDGET_LIGHT")
_csrc = (Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu" / "coach.py").read_text(encoding="utf-8")
_bl_at = _csrc.find("BUDGET_LIGHT = {")
check(_bl_at > 0 and "setzung" in _csrc[max(0, _bl_at - 600):_bl_at].lower() and _bl_at > _csrc.find("CAPACITY = {") > 0,
      "0.73.1 2.1: BUDGET_LIGHT steht nicht neben CAPACITY oder ist nicht als Setzung beschriftet")
# je Zustand der Faktor, ueber den EINEN Weg (_ceiling_budget -> week_budget)
_g31 = build(); _d31 = sorted(_g31["wellness"])[-1]
for _st, _light, _fac in (("ready", "green", 1.3), ("strained", "amber", 1.0), ("elevated", "amber", 1.0),
                          ("recovering", "amber", 1.0), ("rebound", "amber", 1.0), ("slump", "red", 0.8),
                          ("unknown", "unknown", 1.0)):
    _b31 = (coach._ceiling_budget(_g31, _st, _d31)[0] if hasattr(coach, "week_budget") else None) or {}
    eq((_b31.get("state"), _b31.get("target_ratio")), (_light, _fac), f"0.73.1 2.1: Zustand {_st} -> Faktor")
# die zweite Ampel entscheidet nicht mehr: readiness rot + Zustand ready -> 1,3 (der Live-Fall)
_rd_saved = _an.readiness
try:
    _an.readiness = lambda data, today=None: {"overall": "red", "components": [], "budget": {"recommended": 0}}
    _live = (coach._ceiling_budget(_g31, "ready", _d31)[0] if hasattr(coach, "week_budget") else None) or {}
    _tl = coach.today(_g31, day=_d31) if hasattr(coach, "week_budget") else {}
finally:
    _an.readiness = _rd_saved
eq(_live.get("target_ratio"), 1.3, "0.73.1 2.1 Live-Fall: readiness rot + Zustand ready -> Faktor 1,3")
# Trainer-Obergrenze = Heute-Kopf-Obergrenze am selben Tag, fuer jeden Zustand
for _st in ("ready", "strained", "slump", "unknown"):
    if not hasattr(coach, "week_budget"):
        check(False, "0.73.1 2.1: coach.week_budget fehlt"); break
    _tr = coach.session_ceiling(_g31, _st, _d31)["ceiling"]
    _hk = coach.load_ceiling(_st, coach.week_budget(_g31, _st, _d31))["ceiling"]
    eq(_tr, _hk, f"0.73.1 2.1: Trainer-Obergrenze = Heute-Obergrenze ({_st})")
_st31 = coach.state(_g31)["state"]
_t31 = coach.today(_g31, day=_d31) if hasattr(coach, "week_budget") else {}
eq((_t31.get("ceiling"), (_t31.get("week") or {}).get("ceiling")),
   (coach.session_ceiling(_g31, _st31, _d31)["ceiling"],) * 2, "0.73.1 2.1: Heute-Payload und Trainer lesen dieselbe Grenze")
eq(((_t31.get("week") or {}).get("budget") or {}).get("state"), coach.BUDGET_LIGHT.get(_st31) if hasattr(coach, "BUDGET_LIGHT") else "?",
   "0.73.1 2.1: der Heute-Kopf rechnet mit der Farbe des Zustands")
# keine Hintertuer: die Handler und coach lesen readiness() nicht mehr fuers Budget
_wsrc31 = (Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu" / "websocket.py").read_text(encoding="utf-8")
_wt31 = _ast2.parse(_wsrc31)
for _hn in ("websocket_workouts", "websocket_goal", "websocket_today"):
    _hs = _ast2.get_source_segment(_wsrc31, next(n for n in _ast2.walk(_wt31) if isinstance(n, _ast2.FunctionDef) and n.name == _hn))
    check("readiness(" not in _hs and 'get("budget")' not in _hs and '"overall"' not in _hs,
          f"0.73.1 2.1: {_hn} liest noch readiness()/budget/overall")
check("readiness(" not in _csrc and 'get("overall"' not in _csrc, "0.73.1 2.1: coach liest noch readiness()/overall")
check(_csrc.count("analytics.load_budget(") == 1, f"0.73.1 2.1: coach ruft load_budget an {_csrc.count('analytics.load_budget(')} Stellen (soll: eine)")
# readiness behaelt Punkte und overall, das Feld budget hat keinen Leser mehr und ist fort
_rd31 = _an.readiness(_g31)  # 0.73.3 umgestellt: ohne today
check("overall" in _rd31 and _rd31.get("components"), "0.73.1 2.1: readiness verliert Punkte oder overall")
check("budget" not in _rd31, "0.73.1 2.1: readiness traegt noch das Feld budget ohne Leser")


# --- 0.73.2 · T1 ein bewerteter Tag fuer alle Zaehler (Skizze 0.73.2) -----------
def _live732(trained=True):
    """Live-Fall 26.09.: harte Tage So 20. und Fr 25., am Sa 26. trainiert (unter IF 80)."""
    d = build()
    d["activities"]["so20"] = {"id": "so20", "start_date_local": day(-6) + "T09:00:00", "type": "Ride",
                              "moving_time": 5400, "icu_intensity": 86, "icu_training_load": 90}
    d["activities"]["fr25"] = {"id": "fr25", "start_date_local": day(-1) + "T09:00:00", "type": "Ride",
                              "moving_time": 4000, "icu_intensity": 92, "icu_training_load": 75}
    if trained:
        d["activities"]["sa26"] = {"id": "sa26", "start_date_local": day(0) + "T09:00:00", "type": "Ride",
                                  "moving_time": 3600, "icu_intensity": 70, "icu_training_load": 50}
    return d
_jd = getattr(coach, "judged_day", None)
check(callable(_jd), "0.73.2 T1: coach.judged_day fehlt")
_L = _live732()
if callable(_jd):
    eq(_jd(_L), (day(1), True), "0.73.2 T1: trainiert -> der bewertete Tag ist morgen")
    eq(_jd(_live732(trained=False)), (day(0), False), "0.73.2 T1: nicht trainiert -> heute")
    eq(coach._ceiling_budget(_L, "ready")[2], _jd(_L)[0], "0.73.2 T1: _ceiling_budget liest den Tag aus judged_day")
_hd3 = lambda d, dd: coach._hard_days_recent(d, 7, dd)
try:
    eq((_hd3(_L, day(0)), _hd3(_L, day(1))), (2, 1), "0.73.2 T1 Live-Fall: heute-Fenster 2, morgen-Fenster 1")
    # Grenzfall: day-6 zaehlt, day-7 nicht
    eq(_hd3(_L, day(0)), 2, "0.73.2 T1 Grenzfall: harter Tag genau am Tag day-6 zaehlt")
    eq(_hd3(_L, day(1)), 1, "0.73.2 T1 Grenzfall: harter Tag am Tag day-7 zaehlt nicht")
    # nach oben begrenzt: ein harter Tag NACH dem bewerteten Tag zaehlt nicht
    eq(_hd3(_L, day(-2)), 1, "0.73.2 T1: das Fenster endet am bewerteten Tag")
except TypeError as _e:
    check(False, f"0.73.2 T1: _hard_days_recent nimmt keinen Tag ({_e})")
# heute-Modus unveraendert gegenueber 0.73.1 (Gegenprobe gleiche Zahl wie die alte Regel)
_H = _live732(trained=False)
def _alt_hard(d):
    order = sorted(d["wellness"]); cutoff = (date.fromisoformat(order[-1]) - timedelta(days=6)).isoformat()
    return len({str(a.get("start_date_local") or "")[:10] for a in d["activities"].values()
                if str(a.get("start_date_local") or "")[:10] >= cutoff and (a.get("icu_intensity") or 0) >= 80})
eq(coach.assessment(_H)["hard_days_last_7"], _alt_hard(_H), "0.73.2 T1 Gegenprobe: heute-Modus zaehlt wie 0.73.1")
eq(coach.assessment(_L)["hard_days_last_7"], 1, "0.73.2 T1: assessment zaehlt fuer den bewerteten Tag (morgen)")
# alle vier Aufrufer uebergeben den bewerteten Tag
import re as _re732
_ws732 = (Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu" / "websocket.py").read_text(encoding="utf-8")
_co732 = (Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu" / "coach.py").read_text(encoding="utf-8")
_calls = _re732.findall(r"_hard_days_recent\(([^)]*)\)", _ws732) + _re732.findall(r"(?<!def )_hard_days_recent\(([^)]*)\)", _co732)
_calls = [c for c in _calls if not c.startswith("data: ")]
check(len(_calls) >= 5 and all(len([x for x in c.split(",") if x.strip()]) == 3 for c in _calls),
      f"0.73.2 T1: ein Aufrufer uebergibt den Tag nicht: {_calls}")
check("judged_day(" in _ws732, "0.73.2 T1: websocket liest den Tag nicht aus judged_day")
# je Handler: das dritte Argument ist GENAU der Name, den judged_day(...) dort liefert
_hits732 = 0
for _fn in [n for n in _ast2.walk(_ast2.parse(_ws732)) if isinstance(n, _ast2.FunctionDef)]:
    _from_jd = set()
    for _n in _ast2.walk(_fn):
        if isinstance(_n, _ast2.Assign) and isinstance(_n.value, _ast2.Call) and getattr(_n.value.func, "attr", "") == "judged_day":
            for _t in _n.targets:
                for _e in (_t.elts if isinstance(_t, _ast2.Tuple) else [_t]):
                    if isinstance(_e, _ast2.Name):
                        _from_jd.add(_e.id)
    for _n in _ast2.walk(_fn):
        if isinstance(_n, _ast2.Call) and getattr(_n.func, "attr", "") == "_hard_days_recent":
            _hits732 += 1
            _a3 = _n.args[2] if len(_n.args) >= 3 else None
            check(isinstance(_a3, _ast2.Name) and _a3.id in _from_jd,
                  f"0.73.2 T1: {_fn.name} uebergibt nicht den Tag aus judged_day")
eq(_hits732, 3, "0.73.2 T1 Treffer: drei Aufrufe in websocket gefunden")
# Stufe VO2max morgen nicht herabgesetzt (1 harter Tag), heute schon (2)
_vo = next(e for e in workouts.LIBRARY if e["key"] == "vo2_4x4")
_fit = lambda n: workouts.suggest("ready", ftp=250, budget=500, hard_days_last_7=n)
_v1 = next((x for x in _fit(1) if x.get("family") == "vo2max"), {})
_v2 = next((x for x in _fit(2) if x.get("family") == "vo2max"), {})
eq((_v1.get("fit"), _v2.get("fit")), ("ok", "maybe"), "0.73.2 Live: VO2max morgen (1) nicht herabgesetzt, bei 2 schon")
# T2 der Satz im Katalog
check((_v2.get("fit_reason") or "").startswith("Zwei harte Tage liegen schon in den sechs Tagen davor. Zwei in sieben Tagen sind der Standard;"),
      f"0.73.2 T2: Satz workouts: {_v2.get('fit_reason')!r}")
check("in dieser Woche" not in (_v2.get("fit_reason") or ""), "0.73.2 T2: 'in dieser Woche' steht noch")
# T2 Begruendung im Zustandsblock: heute-Modus mit 2 harten Tagen
_st_saved732 = coach.state
try:
    coach.state = lambda data, **kw: {"state": "ready", "label": "im Normalbereich", "detail": "", "infection_suspected": False}
    _rs_h = [r for r in coach.assessment(_H)["reasons"] if "harte" in r["weil"]]
    _rs_m = [r for r in coach.assessment(_L)["reasons"] if "harte" in r["weil"]]
finally:
    coach.state = _st_saved732
eq([r["weil"] for r in _rs_h], ["2 harte Tage in den sechs Tagen vor heute"], "0.73.2 T2: Titel der Begruendung (heute)")
check(bool(_rs_h) and _rs_h[0]["text"].endswith("— heute spricht das für Umfang.")
      and _rs_h[0]["text"].startswith("Im Dreizonenmodell tragen 75–80 % der Einheiten"),
      "0.73.2 T2: Text der Begruendung (heute), Rest unveraendert")
eq(_rs_m, [], "0.73.2 Live: morgen (1 harter Tag) entfaellt die Begruendung")
# T1 recovery_offered: bewerteter Tag, chronischer Schnitt aus week_budget
_ro = coach.recovery_offered(_L)
eq(_ro["hard_days_last_7"], 1, "0.73.2 T1: recovery_offered zaehlt fuer den bewerteten Tag")
_wb = coach._ceiling_budget(_L, coach.state(_L)["state"])[0] or {}
eq(_ro["chronic_daily_load"], _wb.get("chronic"), "0.73.2 T1: chronischer Schnitt = week_budget-chronic")
check(any(m == "1 harter Tag in den sechs Tagen vor morgen" for m in _ro["missing"]),
      f"0.73.2 T2: recovery_offered-Satz: {_ro['missing']}")
check(any(m.endswith("in den sechs Tagen vor heute") for m in coach.recovery_offered(_H)["missing"]),
      "0.73.2 T2: recovery_offered heute-Satz")
# quiet-Fenster relativ zum bewerteten Tag: die RECOVERY_QUIET_DAYS Tage DAVOR
_series = {p["date"]: p["load"] for p in _an.daily_load(_L)}
_q = [(_series.get(day(1 - k)) or 0.0) for k in range(1, const.RECOVERY_QUIET_DAYS + 1)]
eq(_ro["recent_daily_load"], round(sum(_q) / len(_q), 1), "0.73.2 T1: ruhige Tage = die Tage vor dem bewerteten Tag")
_sH = {p["date"]: p["load"] for p in _an.daily_load(_H)}
_qH = [(_sH.get(day(-k)) or 0.0) for k in range(1, const.RECOVERY_QUIET_DAYS + 1)]
eq(coach.recovery_offered(_H)["recent_daily_load"], round(sum(_qH) / len(_qH), 1),
   "0.73.2 T1: heute-Modus: ruhige Tage = die Tage VOR heute")
_rsrc = _co732[_co732.index("def recovery_offered("):]
_rsrc = _rsrc[:_rsrc.index("\ndef ", 10)]
check("mean(loads[-28:])" not in _rsrc, "0.73.2 T1: recovery_offered rechnet noch einen eigenen chronischen Schnitt")

# --- 0.74.0 · Belastungs-Reiter: coach.load_view (Skizze 0.74.0 §3.1 f/g, §5, §8) ---
# Rot vor dem Bau: load_view fehlt. Der Verlauf liest je Tag das Licht des
# Zustands dieses Tages (BUDGET_LIGHT[state_series]), die Vorschau das Licht von
# heute, die Ueberschrift ist today().week - dieselben Zahlen wie der Heute-Kopf.
import analytics as _an74  # noqa: E402
_lv = getattr(coach, "load_view", None)
check(callable(_lv), "0.74.0 f: coach.load_view fehlt")
_ev74 = [{"id": 71, "category": "WORKOUT", "start_date_local": day(1) + "T09:00:00", "icu_training_load": 65},
         {"id": 72, "category": "WORKOUT", "start_date_local": day(0) + "T18:00:00", "icu_training_load": 50},
         {"id": 73, "category": "WORKOUT", "start_date_local": day(3) + "T09:00:00", "icu_training_load": 45,
          "paired_activity_id": "x"},
         {"id": 74, "category": "WORKOUT", "start_date_local": day(5) + "T09:00:00", "icu_training_load": 40}]
for _lbl, _dd in (("ohne Fahrt heute", build()), ("Einbruch heute", slump),
                  ("mit Fahrt heute", build(activities={**build()["activities"],
                                                        "heute": {"start_date_local": day(0) + "T07:00:00", "type": "Ride",
                                                                  "moving_time": 3600, "icu_training_load": 80,
                                                                  "icu_intensity": 70}}))):
    if not callable(_lv):
        break
    _v = _lv(_dd, _ev74)
    check(sorted(_v) == sorted(["weeks_by_group", "window_history", "window_projection", "headline", "planned"]),
          f"0.74.0 g ({_lbl}): Schluessel {sorted(_v)}")
    _ss = {r["date"]: r["state"] for r in coach.state_series(_dd)}
    _bad = [h["date"] for h in _v["window_history"]
            if h["window_allowed"] != (_an74.load_budget(_dd, coach.BUDGET_LIGHT.get(_ss.get(h["date"], "unknown"), "unknown"),
                                                          today=h["date"]) or {}).get("window_allowed")]
    check(not _bad, f"0.74.0 f ({_lbl}): Ziel je Tag aus dem Licht des Tages - abweichend {_bad[:3]}")
    _now = coach.BUDGET_LIGHT.get(coach.state(_dd)["state"], "unknown")
    _pl = _an74.planned_loads(_ev74, day(0))
    eq(_v["planned"], _pl, f"0.74.0 g ({_lbl}): geplant aus den Events nach heute")
    eq(_pl, {day(1): 65.0, day(5): 40.0}, f"0.74.0 g ({_lbl}): heute und gepaart zaehlen nicht")
    _pbad = [p["date"] for p in _v["window_projection"]
             if (p["window_load"], p["window_allowed"]) != (lambda b: (b["window_load"], b["window_allowed"]))(
                 _an74.load_budget(_dd, _now, today=p["date"], planned=_pl))]
    check(not _pbad, f"0.74.0 f ({_lbl}): Vorschau mit Licht von heute und Plan - abweichend {_pbad[:3]}")
    _wk = coach.today(_dd, _ev74)["week"]
    _b = _wk.get("budget") or {}
    eq(_v["headline"], {"mode": _wk["mode"], "window_load": _b.get("window_load"), "window_allowed": _b.get("window_allowed"),
                        "window_free": _b.get("window_free"), "bound_by": _wk["bound_by"], "ceiling": _wk["ceiling"],
                        "available": bool(_b)},
       f"0.74.0 g/§5 ({_lbl}): Ueberschrift = today().week")
    eq(_v["window_history"][-1]["date"], day(0), f"0.74.0 d ({_lbl}): der Verlauf endet heute")
_sl = _lv(slump, _ev74) if callable(_lv) else None
if _sl:
    eq(coach.state(slump)["state"], "slump", "0.74.0 f Fixture: heute Einbruch")
    _h0 = _sl["window_history"][-1]
    _c0 = _an74.load_budget(slump, "red", today=day(0))
    eq(_h0["window_allowed"], _c0["window_bands"]["low"], "0.74.0 f/§8 Einbruch heute: Ziel x0,8, nicht fest 1,3")
    check(_sl["window_history"][-2]["window_allowed"] != _an74.load_budget(slump, "red", today=day(-1))["window_allowed"],
          "0.74.0 f Gegenprobe: gestern (bereit) traegt nicht das Einbruch-Ziel")
    _pp = _sl["window_projection"][0]
    eq(_pp["window_allowed"], _an74.load_budget(slump, "red", today=day(1), planned=_sl["planned"])["window_bands"]["low"],
       "0.74.0 f Vorschau: Licht von heute (rot, x0,8)")
_lsrc = (Path(coach.__file__)).read_text(encoding="utf-8")
if "def load_view(" in _lsrc:
    _lbody = _lsrc[_lsrc.index("def load_view("):]
    _lbody = _lbody[:_lbody.find("\ndef ", 10) if _lbody.find("\ndef ", 10) > 0 else None]
    check("today(" in _lbody and "window_load" not in _lbody.replace('"window_load"', ""),
          "0.74.0 §8: Ueberschrift aus today().week, keine eigene Rechnung")
    check("load_budget(" not in _lbody, "0.74.0 §8: load_view rechnet kein eigenes Budget")

# Regel 9: die Panel-Fixture (tests/panel_fixtures.js, LV_KEYS) traegt dieselben
# Schluessel wie der Erzeuger - je Zeile der Wochen, des Verlaufs und die Ueberschrift.
import re as _re74  # noqa: E402
_fx = (Path(__file__).resolve().parent / "panel_fixtures.js").read_text(encoding="utf-8")
_lvk = _fx[_fx.index("const LV_KEYS = {"):_fx.index("};", _fx.index("const LV_KEYS = {"))]
_fxkeys = {m.group(1): _re74.findall(r'"([a-z_]+)"', m.group(2)) for m in _re74.finditer(r'(\w+): \[([^\]]*)\]', _lvk)}
if callable(_lv):
    _vv = _lv(build(), _ev74)
    eq(sorted(_fxkeys.get("weeks_by_group", [])), sorted(_vv["weeks_by_group"][-1]), "0.74.0 Regel 9: Fixture-Schluessel Wochen")
    eq(sorted(_fxkeys.get("window_history", [])), sorted(_vv["window_history"][-1]), "0.74.0 Regel 9: Fixture-Schluessel Verlauf")
    eq(sorted(_fxkeys.get("window_history", [])), sorted(_vv["window_projection"][-1]), "0.74.0 Regel 9: Fixture-Schluessel Vorschau")
    eq(sorted(_fxkeys.get("headline", [])), sorted(_vv["headline"]), "0.74.0 Regel 9: Fixture-Schluessel Ueberschrift")
check("acwr_low" not in _fx and "acwr_latest" not in _fx, "0.74.0 Regel 9: die Fixture traegt ACWR-Felder, die der Erzeuger nicht mehr schreibt")

# §5 Seitenprobe ueber drei Stellen: Ueberschrift Verlauf = Heute-Kopf = Trainer-Obergrenze (gleicher Tag)
if callable(_lv):
    for _lbl, _dd in (("ohne Fahrt", build()), ("Einbruch", slump)):
        _hh = _lv(_dd, _ev74)["headline"]
        _sc = coach.session_ceiling(_dd, coach.state(_dd)["state"])
        _want = _hh["window_free"] if _hh["bound_by"] == "week" else _hh["ceiling"]
        eq((_hh["ceiling"], _want), (_sc["ceiling"], _sc["ceiling"]), f"0.74.0 §5 ({_lbl}): Ueberschrift/frei = Trainer-Obergrenze")

print(f"test_coach: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
sys.exit(1 if FAILURES else 0)
