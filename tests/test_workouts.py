"""Sessions: the right one for the state, and a payload Intervals can parse.

Two things can go badly wrong here. A hard session recommended on the wrong
day is a training error. A malformed payload silently puts a broken workout
on the calendar, which is worse than none. Both are checked below.
"""

import ast as _ast
import re
import sys
from pathlib import Path

import coldcache  # noqa: F401,E402  - MUSS vor jedem Bauteil-Import stehen (§9)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"))

import workouts as W  # noqa: E402

FAILURES: list[str] = []
CHECKS = 0


def check(condition: bool, label: str) -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILURES.append(label)


def eq(got, want, label: str) -> None:
    check(got == want, f"{label}: {got!r} statt {want!r}")


# --- 1  every entry is complete -----------------------------------------------
for entry in W.LIBRARY:
    key = entry["key"]
    for field in ("title", "purpose", "minutes", "intensity", "load", "blocks",
                  "text", "dfa", "effect", "evidence", "limit", "states"):
        check(entry.get(field) not in (None, "", []), f"1 {key}: {field} fehlt")
    check(len(entry["evidence"]) > 25, f"1 {key}: Beleg zu dünn")
    check(len(entry["limit"]) > 25, f"1 {key}: keine Grenze genannt")
    # the block sum has to match the stated duration, or the plan lies about time
    total = sum(block[0] for block in entry["blocks"])
    check(abs(total - entry["minutes"]) <= 6,
          f"1 {key}: Blöcke summieren auf {total} min, angegeben sind {entry['minutes']}")
    # load must rise with intensity within reason
    check(0 < entry["load"] < 200, f"1 {key}: unplausible Last {entry['load']}")

keys = [entry["key"] for entry in W.LIBRARY]
check(len(set(keys)) == len(keys), "1 doppelte Schlüssel in der Bibliothek")

# --- 2  every kind stays visible, and is JUDGED ------------------------------
# The earlier version filtered: in a rebound everything hard vanished and three
# base rides were left, which is not a choice. Now each family appears once and
# carries a verdict for today - the decision is the athlete's, the data's job
# is to say what it costs.
easy_families = {"recovery", "return", "endurance"}

for state in ("slump", "recovering", "rebound", "strained", "ready"):
    picks = W.suggest(state, ftp=215, aerobic_hr=157)
    families = [entry["family"] for entry in picks]
    check(len(families) == len(set(families)), f"2 {state}: dieselbe Art mehrfach ({families})")
    check(len(picks) >= 4, f"2 {state}: nur {len(picks)} Arten zur Auswahl")
    for entry in picks:
        check(entry["fit"] in ("ok", "maybe", "no"), f"2 {state}: kein Urteil")
        check(entry["fit"] == "ok" or entry["fit_reason"],
              f"2 {state}: {entry['key']} abgeraten ohne Begründung")

# in a slump nothing hard may be recommended - but it must still be THERE
slump = W.suggest("slump", ftp=215, aerobic_hr=157)
hard = [e for e in slump if e["intensity"] >= 75]
check(hard, "2 Einbruch: harte Einheiten ganz verschwunden statt bewertet")
check(all(e["fit"] == "no" for e in hard),
      f"2 Einbruch: harte Einheit nicht abgeraten ({[(e['key'], e['fit']) for e in hard]})")
check(any(e["fit"] == "ok" for e in slump), "2 Einbruch: gar nichts möglich")
check(all(e["fit"] == "ok" for e in slump if e["family"] == "recovery"),
      "2 Einbruch: Regeneration nicht empfohlen")

# in a rebound the middle kinds are possible, the hard ones are not
rebound = W.suggest("rebound", ftp=215, aerobic_hr=157)
by_family = {e["family"]: e for e in rebound}
check(by_family.get("vo2max", {}).get("fit") == "no", "2 Erholung: VO2max nicht abgeraten")
check(by_family.get("sweetspot", {}).get("fit") == "maybe", "2 Erholung: SweetSpot falsch gewertet")
check(by_family.get("endurance", {}).get("fit") == "ok", "2 Erholung: Grundlage nicht empfohlen")

# in a ready state everything is on the table
ready = W.suggest("ready", ftp=215, aerobic_hr=157)
check(all(e["fit"] == "ok" for e in ready), "2 Normalbereich: etwas grundlos abgeraten")
check(any(e["family"] == "vo2max" for e in ready), "2 Normalbereich: kein harter Reiz im Angebot")
# ... and the VO2max variant offered is the entry dose, not the hardest protocol
vo2 = next(e for e in ready if e["family"] == "vo2max")
eq(vo2["key"], "vo2_4x4", "2 Normalbereich: nicht die Einstiegsdosis angeboten")
check(vo2["alternatives"], "2 Normalbereich: keine Varianten der Art angeboten")

# --- 3  a break brings the graded return in ----------------------------------
after_break = W.suggest("ready", ftp=215, aerobic_hr=157, layoff_days=7)
keys_break = [e["key"] for e in after_break]
check("return_45" in keys_break, f"3 nach Pause: kein Wiedereinstieg angeboten ({keys_break})")
endu_break = next((e for e in after_break if e["family"] == "endurance"), None)
check(endu_break is not None,
      "3 nach Pause: Grundlage ausgeblendet — beurteilen, nicht filtern")
check(endu_break is not None and endu_break["fit"] != "ok",
      "3 nach Pause: Grundlage ohne Einordnung freigegeben")
check(endu_break is not None and "Wiedereinstieg" in endu_break["fit_reason"],
      "3 nach Pause: Grundlagen-Urteil nennt den besseren ersten Schritt nicht")
short_break = [e["key"] for e in W.suggest("ready", ftp=215, layoff_days=2)]
check("return_45" not in short_break, "3 zwei Tage Pause gelten schon als Wiedereinstieg")

# --- 4  a second hard day in the week downgrades, it does not hide ------------
capped = W.suggest("ready", ftp=215, aerobic_hr=157, hard_days_last_7=2)
hard_capped = [e for e in capped if e["intensity"] >= 80]
check(hard_capped, "4 zwei harte Tage: harte Einheiten verschwunden statt abgestuft")
check(all(e["fit"] == "maybe" for e in hard_capped),
      "4 zwei harte Tage: dritter harter Tag unbesehen empfohlen")
check(any("Standard für Wochen" in (e["fit_reason"] or "") for e in hard_capped),
      "4 zwei harte Tage: Begründung nennt die Regel nicht")

# --- 5  the athlete's own numbers ---------------------------------------------
scaled = W.suggest("ready", ftp=215, aerobic_hr=157)[0]
check("blocks_w" in scaled, "5 keine Wattzahlen trotz FTP")
first_block = scaled["blocks_w"][0]
eq(first_block[1], round(215 * scaled["blocks"][0][1] / 100), "5 Watt falsch gerechnet")
check(scaled["hr_window"][0] < scaled["hr_window"][1], "5 Pulsfenster verdreht")
# the first offer is now the base ride, whose window sits BELOW the threshold -
# that is the point of it
check(scaled["hr_window"][1] <= 157 or scaled["intensity"] >= 75,
      f"5 Pulsfenster passt nicht zur Art ({scaled['key']}: {scaled['hr_window']})")
hard_scaled = next(e for e in W.suggest("ready", ftp=215, aerobic_hr=157)
                   if e["family"] == "vo2max")
check(hard_scaled["hr_window"][0] > 157,
      "5 Pulsfenster einer harten Einheit unter der aeroben Schwelle")
bare = W.suggest("ready")[0]
check("blocks_w" not in bare, "5 Wattzahlen ohne FTP erfunden")
check(bare.get("hr_window") is None, "5 Pulsfenster ohne Anker erfunden")

# --- 6  budget is marked, not hidden ------------------------------------------
tight = W.suggest("ready", ftp=215, aerobic_hr=157, budget=50)
check(any(entry["fits_budget"] is False for entry in tight), "6 Budget: Überschreitung nicht markiert")
check(len(tight) >= 4, "6 Budget: Vorschläge werden weggefiltert statt markiert")
loose = W.suggest("ready", ftp=215, aerobic_hr=157, budget=500)
check(all(entry["fits_budget"] for entry in loose), "6 Budget: passende Einheit als zu groß markiert")
nobudget = W.suggest("ready", ftp=215)
check(all(entry["fits_budget"] is None for entry in nobudget), "6 Budget: Aussage ohne Budget")

# --- 7  the calendar payload -------------------------------------------------
event = W.to_event(W.BY_KEY["vo2_3015"], "2026-09-13")
eq(event["category"], "WORKOUT", "7 Kalender: falsche Kategorie")
eq(event["start_date_local"], "2026-09-13T00:00:00", "7 Kalender: Datumsformat")
eq(event["type"], "Ride", "7 Kalender: Sportart")
check(event["moving_time"] == 62 * 60, "7 Kalender: Dauer in Sekunden falsch")
check(isinstance(event["icu_training_load"], int), "7 Kalender: Last nicht ganzzahlig")
eq(event["target"], "POWER", "7 Kalender: Ziel nicht Leistung")
eq(event["workout_doc"], {}, "7 Kalender: workout_doc nicht leer - Intervals soll parsen")

# the description must be syntax Intervals can parse
text = event["description"]
check("Vorgeschlagen von Home Assistant" in text, "7 Kalender: Herkunft nicht vermerkt")
body = text.split("\n\n", 1)[1]
for line in body.splitlines():
    if not line.strip():
        continue
    ok_line = line.startswith("- ") or re.fullmatch(r"\d+x", line.strip())
    check(ok_line, f"7 Syntax: Zeile passt nicht ins Intervals-Format: {line!r}")
    if line.startswith("- "):
        check(re.match(r"- \d+(h|m|s|m\d+s)\b", line.strip()),
              f"7 Syntax: keine gültige Dauer in {line!r}")
check("13x" in body and "3x" in body, "7 Syntax: Wiederholungen fehlen")
check("30s" in body, "7 Syntax: Sekundenschritte fehlen")

# every workout in the library must survive the same check
for entry in W.LIBRARY:
    payload = W.to_event(entry, "2026-01-05")
    lines = payload["description"].split("\n\n", 1)[1].splitlines()
    for line in lines:
        if not line.strip():
            continue
        check(line.startswith("- ") or re.fullmatch(r"\d+x", line.strip()),
              f"7 Syntax {entry['key']}: {line!r}")
    check(payload["moving_time"] > 0, f"7 Kalender {entry['key']}: Dauer null")

# --- 8  a note is optional, and the sport can change --------------------------
run = W.to_event(W.BY_KEY["z2_60"], "2026-01-05", sport="Run", note=None)
eq(run["type"], "Run", "8 Sportart nicht übernommen")
check(not run["description"].startswith("Vorgeschlagen"), "8 Notiz erfunden")

# --- 9  unknown states fall back instead of failing ---------------------------
for state in ("unknown", "elevated", "quatsch"):
    picks = W.suggest(state, ftp=215, aerobic_hr=157)
    check(picks, f"9 {state}: keine Vorschläge")
    # an unclear state must not RECOMMEND a hard session - offering it with a
    # reservation is fine, that is the whole point of judging instead of hiding
    hard_unclear = [e for e in picks if e["intensity"] >= 85]
    check(all(e["fit"] != "ok" for e in hard_unclear),
          f"9 {state}: harter Reiz bei unklarer Lage empfohlen")
    check(all(e["fit"] != "ok" or e["fit_reason"] == "" for e in picks),
          f"9 {state}: Empfehlung mit Einschränkungstext")

# --- 10  watts, not percentages ----------------------------------------------
# A percentage only lands correctly if the FTP configured in Intervals matches
# the one this plan was built from. If it does not, every target in the session
# is silently wrong - and the rider has no way of noticing.
with_ftp = W.scaled(W.BY_KEY["vo2_4x4"], 215.0, 157)
check("text_w" in with_ftp, "10 Watt: kein Wattext erzeugt")
check("%" not in with_ftp["text_w"], f"10 Watt: Prozente geblieben ({with_ftp['text_w']})")
check("w" in with_ftp["text_w"], "10 Watt: keine Wattangaben")
check("228-236w" in with_ftp["text_w"] or "237w" in with_ftp["text_w"],
      f"10 Watt: falsch gerechnet ({with_ftp['text_w']})")
# the cadence markers must survive the rewrite
check("95rpm" in with_ftp["text_w"], "10 Watt: Trittfrequenz verlorengegangen")
check("4m" in with_ftp["text_w"] and "4x" in with_ftp["text_w"], "10 Watt: Struktur zerstört")

event = W.to_event(with_ftp, "2026-09-13")
check("%" not in event["description"], "10 Watt: Kalendereintrag trägt Prozente")
check("w" in event["description"], "10 Watt: Kalendereintrag ohne Wattwerte")

# without an FTP nothing is invented - percentages stay, and that is honest
bare = W.to_event(W.BY_KEY["vo2_4x4"], "2026-09-13")
check("%" in bare["description"], "10 Watt: Wattzahlen ohne FTP erfunden")

# every scaled entry in the library must convert cleanly
for entry in W.LIBRARY:
    converted = W.scaled(entry, 215.0, 157)
    check("%" not in converted["text_w"], f"10 Watt: {entry['key']} behält Prozente")
    for line in converted["text_w"].splitlines():
        if line.startswith("- "):
            check("w" in line, f"10 Watt: {entry['key']} Zeile ohne Wattwert: {line!r}")

# --- 11  the heart rate window stops at the measured maximum ------------------
vo2_entry = W.BY_KEY["vo2_4x8"]
unclamped = W.scaled(vo2_entry, 215, 157)
check(unclamped["hr_window"][1] > 170, "11 fenster: Testfall zu lasch gewählt")
clamped = W.scaled(vo2_entry, 215, 157, max_hr=175)
check(clamped["hr_window"][1] <= 175, "11 fenster: Obergrenze über dem Maximum")
check(clamped["hr_window"][0] < clamped["hr_window"][1], "11 fenster: leeres Fenster geliefert")
# floor at the ceiling -> no window at all instead of a fantasy range
gone = W.scaled(vo2_entry, 215, 157, max_hr=165)
check("hr_window" not in gone, "11 fenster: Fenster oberhalb des Maximums behauptet")
# an easy family is untouched by the clamp
easy = W.scaled(W.BY_KEY["z2_90"], 215, 157, max_hr=175)
check(easy.get("hr_window") == W.scaled(W.BY_KEY["z2_90"], 215, 157).get("hr_window"),
      "11 fenster: Klemme verändert eine lockere Einheit")

# --- 12  infection pattern -> a ladder, judged and visible --------------------
ladder = W.suggest("rebound", ftp=215, aerobic_hr=157, infection=True)
fams = {e["family"] for e in ladder}
check(fams == {f[0] for f in W.FAMILIES} - {"return"},
      f"12 leiter: Familien verschwunden ({sorted(fams)})")
for e in ladder:
    if e["family"] in ("recovery", "return"):
        continue
    if e["family"] == "endurance":
        check(e["fit"] == "maybe" and "Symptom" in e["fit_reason"],
              "12 leiter: Grundlage nicht symptomgeleitet eingeordnet")
    else:
        check(e["fit"] == "no", f"12 leiter: {e['family']} trotz Infektmuster freigegeben")
        check("Leiter" in e["fit_reason"] or "Symptom" in e["fit_reason"],
              f"12 leiter: {e['family']} ohne Begründung abgestuft")
# without the flag the rebound verdicts stay as they were
plain = {e["family"]: e["fit"] for e in W.suggest("rebound", ftp=215, aerobic_hr=157)}
check(plain["tempo"] == "maybe" and plain["sweetspot"] == "maybe",
      "12 leiter: Infekt-Abstufung wirkt auch ohne Infekt")


# --- anchor conflict: FTP watts vs the measured DFA threshold -----------------
# The live case that motivated this: FTP 215, measured aerobic power 146 -
# the base-ride watt window (140-150 W) sits ON the measured threshold, so a
# base ride ridden by watts contradicts the "DFA above 0.75" printed next to
# it. The guard has to fire there, stay silent on a sane pairing, and never
# invent a verdict from missing numbers.
conflict = W.anchor_conflict(215.0, 146.0)
check(conflict is not None, "konflikt 215/146: nicht erkannt")
check(conflict and conflict["share_pct"] == 68, f"konflikt: Anteil falsch ({conflict})")
check(conflict and "215" in conflict["text"] and "146" in conflict["text"],
      "konflikt: Zahlen fehlen im Text")
check(conflict and "Herzfrequenz" in conflict["text"],
      "konflikt: keine Handlungsanweisung")
check(W.anchor_conflict(215.0, 175.0) is None, "konflikt 215/175: Fehlalarm")
check(W.anchor_conflict(None, 146.0) is None, "konflikt: aus fehlender FTP erfunden")
check(W.anchor_conflict(215.0, None) is None, "konflikt: aus fehlender Schwelle erfunden")
check(W.anchor_conflict(0, 0) is None, "konflikt: aus Nullen erfunden")
# the boundary: exactly at the z2 top plus tolerance stays quiet, just under fires
check(W.anchor_conflict(200.0, 200.0 * 0.70 * 1.03 + 0.5) is None,
      "konflikt: Toleranzgrenze feuert zu früh")
check(W.anchor_conflict(200.0, 200.0 * 0.70) is not None,
      "konflikt: an der Z2-Obergrenze stumm")


# --- 12  the four grades (docs/ausbau.md I3) ----------------------------------
# Four grades, one place. The whole truth table is walked here, because the
# panel prints whatever comes back and has no rule of its own to fall back on.
eq(sorted(W.STAGES), ["green", "red", "stimulus", "yellow"], "stufen: nicht vier")

labels = [W.STAGES[key]["label"] for key in ("green", "yellow", "stimulus", "red")]
words = [W.STAGES[key]["word"] for key in ("green", "yellow", "stimulus", "red")]
eq(len(set(labels)), 4, "stufen: zwei Stufen teilen sich ein Wort")
eq(len(set(words)), 4, "stufen: zwei Stufen teilen sich eine Beschriftung")
eq(labels[2], "Reiz", "stufen: die vierte Stufe heißt nicht Reiz")

TRUTH = {
    # (fit, fits_budget, recovery): (stage, blocked_by)
    ("ok", True, True): ("green", None),
    ("ok", True, False): ("green", None),
    ("ok", None, True): ("green", None),
    ("ok", None, False): ("green", None),
    ("ok", False, True): ("stimulus", None),
    ("ok", False, False): ("red", "budget"),
    ("maybe", True, True): ("yellow", None),
    ("maybe", True, False): ("yellow", None),
    ("maybe", None, True): ("yellow", None),
    ("maybe", None, False): ("yellow", None),
    ("maybe", False, True): ("red", "both"),
    ("maybe", False, False): ("red", "both"),
    ("no", True, True): ("red", "state"),
    ("no", True, False): ("red", "state"),
    ("no", None, True): ("red", "state"),
    ("no", None, False): ("red", "state"),
    ("no", False, True): ("red", "both"),
    ("no", False, False): ("red", "both"),
}
for (fit, budget, recovery), (want_key, want_blocked) in TRUTH.items():
    got = W.stage(fit, budget, recovery)
    eq(got["key"], want_key, f"stufe {fit}/{budget}/{recovery}")
    eq(got["blocked_by"], want_blocked, f"stufe {fit}/{budget}/{recovery}: Begründung")

# red says WHICH of the two forbids it - "rot" without the reason is the half
# answer the specification rules out
check("Zustand" in W.stage("no", True, False)["detail"],
      "rot aus dem Zustand: nennt den Zustand nicht")
check("Lastbudget" in W.stage("ok", False, False)["detail"],
      "rot aus dem Budget: nennt das Budget nicht")
both = W.stage("maybe", False, False)["detail"]
check("Zustand" in both and "Lastbudget" in both, "rot aus beidem: nennt nur eines")

# an unknown budget cannot be exceeded - the stimulus grade needs a real one
eq(W.stage("ok", None, True)["key"], "green", "stufe: Reiz ohne existierendes Budget")

# the objection travels WITH the stimulus grade, never alone
stim = W.stage("ok", False, True)
check("Meeusen" in stim.get("evidence", ""), "Reiz: Beleg fehlt")
check("SCHWÄCHERE" in stim.get("evidence", "") or "schwächere" in stim.get("evidence", ""),
      "Reiz: die Gegenbefunde fehlen — 'je öfter desto besser' bliebe stehen")
for key in ("green", "yellow", "red"):
    check("evidence" not in W.stage(*{"green": ("ok", True, False),
                                      "yellow": ("maybe", True, False),
                                      "red": ("no", True, False)}[key]),
          f"{key}: trägt den Überreich-Beleg, der nicht zu ihm gehört")

# --- 13  the load of the session AS PLANNED -----------------------------------
# The plan calls the big day "5.0 h" and hands over z2_210_late (210 min, load
# 175). Judged by the catalogue entry that is a three-and-a-half-hour ride, and
# the most important session of the long-ride goal comes out systematically too
# green. Both directions are checked, and the no-hours case must stay untouched.
big = W.BY_KEY["z2_210_late"]
eq(W.session_load(big), 175, "last: Katalogeinheit ohne Stunden verändert")
eq(W.session_load(big, 3.5), 175, "last: gleiche Dauer ergibt nicht dieselbe Last")
eq(W.session_load(big, 5.0), 250, "last: 5 h nicht hochgerechnet")
eq(W.session_load(big, 2.0), 100, "last: kürzere Einheit nicht heruntergerechnet")
check(W.session_load(big, 5.0) > W.session_load(big),
      "last: die längere Fahrt ist nicht schwerer als der Katalogeintrag")
eq(W.session_load({"load": 80, "minutes": 0}, 2.0), 80, "last: Division durch null")
eq(W.session_load({}, 2.0), 0, "last: leerer Eintrag erfindet eine Zahl")

# and the consequence at the budget: the same ride flips the verdict
eq(W.stage("ok", W.session_load(big) <= 200, False)["key"], "green",
   "last: der Katalogwert allein ergäbe grün")
eq(W.stage("ok", W.session_load(big, 5.0) <= 200, False)["key"], "red",
   "last: die hochgerechnete Last ändert das Urteil nicht — die Skalierung wirkt nicht")

# The counter-proof with the ACTUAL numbers of the live plan, not just "something
# scales". A four-hour routine long day is planned as z2_90 - 95 minutes, load
# 72 in the catalogue. Before 0.42.0 the week view would have judged that ride by
# the 72; it carries 182. If a later change ever quietly drops the scaling, the
# figures below are what fails, and they name the defect instead of describing it.
ROUTINE_LONG = {"role": "long", "title": "Langer Tag — 4,0 h", "workout": "z2_90",
                "detail": "…", "why": "…", "hours": 4.0}
routine = W.rate_sessions([dict(ROUTINE_LONG)], "ready", budget=200)[0]
eq(routine["load"], 182, "skalierung: der lange Tag trägt nicht 182")
eq(routine["catalogue_load"], 72, "skalierung: die Kataloglast ist nicht 72")
check(routine["load"] != routine["catalogue_load"],
      "skalierung: geplante Last gleich Kataloglast — die Hochrechnung fehlt")
eq(W.session_load(W.BY_KEY["z2_90"], 4.0), 182, "skalierung: 4 h auf z2_90 ergibt nicht 182")

# and the same for the big day, the session the long-ride goal is actually about
BIG_DAY = {"role": "long", "title": "Großer Tag — 5,0 h", "workout": "z2_210_late",
           "detail": "…", "why": "…", "hours": 5.0}
big_rated = W.rate_sessions([dict(BIG_DAY)], "ready", budget=200)[0]
eq(big_rated["load"], 250, "skalierung: der große Tag trägt nicht 250")
eq(big_rated["catalogue_load"], 175, "skalierung: die Kataloglast des großen Tages ist nicht 175")

# The defect made visible: at a budget of 200 the catalogue figures call BOTH
# sessions green, the planned figures do not. That difference IS the bug fix -
# a test that only asserts "the numbers differ" would pass on a scaling factor
# of 1.001 and miss it.
eq(W.stage("ok", 72 <= 200, False)["key"], "green",
   "skalierung: schon die Kataloglast des langen Tages sprengte das Budget — Fall untauglich")
eq(W.stage("ok", 175 <= 200, False)["key"], "green",
   "skalierung: schon die Kataloglast des großen Tages sprengte das Budget — Fall untauglich")
eq(routine["stage"]["key"], "green", "skalierung: 182 gegen Budget 200 ist nicht grün")
eq(big_rated["stage"]["key"], "red", "skalierung: 250 gegen Budget 200 ist nicht rot")
check(big_rated["stage"]["blocked_by"] == "budget",
      "skalierung: der große Tag fällt nicht am Budget, sondern woanders")

# --- 14  the same session, four different grades ------------------------------
# The trap from the specification: a fixture in which every session is green in
# one state and red in another tests the SESSION, not the grade. These four
# cases hold the session constant (sweetspot_2x20, 1.2 h) and move only state,
# budget and recovery.
SESSION = {"role": "quality", "title": "SweetSpot 2×20", "workout": "sweetspot_2x20",
           "detail": "…", "why": "…", "hours": 1.2}
CASES = [
    ("ready", 200, False, "green"),      # state carries, load fits
    ("rebound", 200, False, "yellow"),   # state carries only partly
    ("ready", 50, True, "stimulus"),     # over budget, but rested
    ("ready", 50, False, "red"),         # over budget, no recovery behind it
]
for state, budget, recovery, want in CASES:
    rated = W.rate_sessions([dict(SESSION)], state, budget=budget, recovery_offered=recovery)
    eq(len(rated), 1, f"bewertung {state}/{budget}: Einheit verschwunden")
    eq(rated[0]["stage"]["key"], want, f"bewertung {state}/{budget}/{recovery}")
    eq(rated[0]["title"], SESSION["title"], "bewertung: Titel verändert")
    eq(rated[0]["hours"], SESSION["hours"], "bewertung: Stunden verändert")
grades = {W.rate_sessions([dict(SESSION)], s, budget=b, recovery_offered=r)[0]["stage"]["key"]
          for s, b, r, _ in CASES}
eq(len(grades), 4, "bewertung: dieselbe Einheit erreicht nicht alle vier Stufen")

# the grade sits ON the session, and the load with it
one = W.rate_sessions([dict(SESSION)], "ready", budget=200)[0]
eq(one["family"], "sweetspot", "bewertung: Familie nicht aufgelöst")
eq(one["catalogue_load"], W.BY_KEY["sweetspot_2x20"]["load"], "bewertung: Kataloglast fehlt")
check(one["load"] == W.session_load(W.BY_KEY["sweetspot_2x20"], 1.2),
      "bewertung: Last nicht über session_load gerechnet")
check(one.get("effect"), "bewertung: 'was das bringt' fehlt an der Einheit")

# an unknown workout key gets no invented verdict
odd = W.rate_sessions([{"title": "Handstand", "workout": "nope", "hours": 1}], "ready", budget=200)
check("stage" not in odd[0], "bewertung: unbekannte Einheit bekommt ein erfundenes Urteil")
eq(odd[0]["title"], "Handstand", "bewertung: unbekannte Einheit verschluckt")

# every workout key the plan can emit resolves - otherwise a session of the
# current week would silently lose its grade
for key in ("z2_210_late", "z2_150", "z2_90", "z2_60", "sweetspot_2x20",
            "tempo_2x20", "threshold_3x12", "vo2_3015", "vo2_4x8"):
    check(key in W.FAMILY_OF_KEY, f"bewertung: Plan-Einheit {key} ohne Familie")

# --- 15  one state rule, not two ----------------------------------------------
# fit_for() was pulled out of suggest() so the week view asks the SAME question.
# If the two ever drift apart, this fails: the list for today and the rating of
# a planned session of the same family must reach the same verdict.
for state in ("ready", "rebound", "strained", "slump", "recovering", "elevated", "unknown"):
    picks = {entry["family"]: entry["fit"]
             for entry in W.suggest(state, ftp=215, budget=400, layoff_days=0)}
    rated = W.rate_sessions([dict(SESSION)], state, budget=400)[0]
    if "sweetspot" in picks:
        eq(rated["fit"], picks["sweetspot"],
           f"eine Regel: Wochenansicht und Einheitenliste urteilen bei {state} verschieden")

# suggest() carries the grade too - the trainer tab must not derive one
sug = W.suggest("ready", ftp=215, budget=400, layoff_days=0)
check(all("stage" in entry for entry in sug), "einheitenliste: Stufe fehlt in der Payload")
check(all(entry["stage"]["key"] in W.STAGES for entry in sug),
      "einheitenliste: unbekannte Stufe in der Payload")
tight = W.suggest("ready", ftp=215, budget=10, layoff_days=0, recovery_offered=True)
check(any(entry["stage"]["key"] == "stimulus" for entry in tight),
      "einheitenliste: bei knappem Budget und Erholung erscheint keine Reiz-Stufe")
tired = W.suggest("ready", ftp=215, budget=10, layoff_days=0, recovery_offered=False)
check(not any(entry["stage"]["key"] == "stimulus" for entry in tired),
      "einheitenliste: Reiz-Stufe ohne Erholung im Rücken")

# --- 16  no verdict without its grade ------------------------------------------
# Found while the panel tests were nachgezogen: two fixtures flipped `fit` to
# "no" and left `stage` green behind, and the panel - correctly - followed the
# grade. That is a payload the BACKEND CANNOT PRODUCE, and the next session
# would have built one again and wondered. So it becomes an assertion: wherever
# a verdict travels, its grade travels with it, and the two agree.
def carries_grade(entries: list[dict], label: str) -> None:
    for entry in entries:
        if "fit" not in entry:
            continue
        grade = entry.get("stage") or {}
        check(bool(grade.get("key")), f"{label}: Urteil '{entry.get('fit')}' ohne Stufe")
        # and they agree: a blocking verdict can never wear a green grade
        if entry.get("fit") == "no":
            eq(grade.get("key"), "red", f"{label}: 'no' trägt nicht rot")
        if entry.get("fit") == "maybe" and entry.get("fits_budget") is not False:
            eq(grade.get("key"), "yellow", f"{label}: 'maybe' im Budget trägt nicht gelb")
        if entry.get("fit") == "ok" and entry.get("fits_budget") is not False:
            eq(grade.get("key"), "green", f"{label}: 'ok' im Budget trägt nicht grün")

for state in ("ready", "rebound", "slump", "recovering", "strained", "elevated", "unknown"):
    for budget in (None, 10, 400):
        carries_grade(W.suggest(state, ftp=215, budget=budget, layoff_days=0),
                      f"einheitenliste {state}/{budget}")
        carries_grade(W.rate_sessions([dict(SESSION), dict(ROUTINE_LONG)], state, budget=budget),
                      f"wochenansicht {state}/{budget}")

# the counter-proof: a hand-built payload with a verdict and a mismatched grade
# must be CAUGHT by the rule above, not shrugged at
before = len(FAILURES)
carries_grade([{"fit": "no", "fits_budget": True, "stage": {"key": "green"}}], "gegenprobe")
check(len(FAILURES) > before,
      "gegenprobe: Urteil 'no' mit grüner Stufe wird nicht erkannt — die Zusicherung ist blind")
del FAILURES[before:]   # the planted defect is not a real failure

before = len(FAILURES)
carries_grade([{"fit": "ok", "fits_budget": True}], "gegenprobe ohne Stufe")
check(len(FAILURES) > before,
      "gegenprobe: Urteil ganz ohne Stufe wird nicht erkannt — die Zusicherung ist blind")
del FAILURES[before:]

# the sentence for later weeks exists once, in the backend, and says why
check("Woche selbst" in W.NO_VERDICT_NOTE, "späte Wochen: der Satz nennt den Grund nicht")
check("sechs Tagen" in W.NO_VERDICT_NOTE, "späte Wochen: das Budgetfenster wird nicht genannt")


# --- 17  elasticity is a property of the SECTION (ausbau.md I12) --------------
# Warm-up, cool-down, intervals and rests are fixed; a steady block absorbs the
# difference. Written per session by the author, not derived from a threshold.
for entry in W.LIBRARY:
    for block in entry["blocks"]:
        check(len(block) in (3, 4), f"elastisch: {entry['key']} hat einen Block falscher Form")
        if len(block) == 4:
            check(block[3] is True, f"elastisch: {entry['key']} markiert einen Block anders als True")

# Every template is checked: it either HAS an elastic section, or it is never
# stretched. The second case is not a gap - a 40-minute recovery ride and every
# interval protocol ARE their duration - but it has to be visible, and the card
# then keeps both durations instead of quietly dehnen.
no_elastic = [entry["key"] for entry in W.LIBRARY
              if not any(W.is_elastic(block) for block in entry["blocks"])]
for key in no_elastic:
    check(W.stretch_blocks(W.BY_KEY[key], 3.0) is None,
          f"elastisch: {key} hat keinen dehnbaren Abschnitt, wird aber gestreckt")
check(set(no_elastic) >= {"recovery_40", "return_45", "sweetspot_2x20", "vo2_4x4"},
      f"elastisch: eine feste Dosierung gilt als dehnbar ({sorted(no_elastic)})")
for key in ("z2_60", "z2_90", "z2_150", "z2_210_late"):
    check(any(W.is_elastic(block) for block in W.BY_KEY[key]["blocks"]),
          f"elastisch: die lange Fahrt {key} hat keinen dehnbaren Abschnitt")

# the stretch itself: the total matches, and ONLY the elastic sections moved
stretched = W.stretch_blocks(W.BY_KEY["z2_90"], 4.0)
check(stretched is not None, "streckung: z2_90 auf 4 h wird gar nicht gestreckt")
stretched = stretched or []
eq(sum(block[0] for block in stretched), 240, "streckung: Gesamtdauer trifft die geplante nicht")
eq(stretched[0][0] if len(stretched) > 0 else None, 10, "streckung: das Einrollen wurde gedehnt")
eq(stretched[2][0] if len(stretched) > 2 else None, 5, "streckung: das Ausrollen wurde gedehnt")
eq(stretched[1][0] if len(stretched) > 1 else None, 225,
   "streckung: der gleichmäßige Abschnitt nimmt die Differenz nicht auf")
for before, after in zip(W.BY_KEY["z2_90"]["blocks"], stretched):
    eq(after[1], before[1], "streckung: die Intensität eines Abschnitts hat sich geändert")
    eq(after[2], before[2], "streckung: die Beschriftung eines Abschnitts hat sich geändert")

# the long ride with quality at the end: the END BLOCKS keep their length -
# that is the whole point of the session ("Qualität im ermüdeten Zustand")
big = W.stretch_blocks(W.BY_KEY["z2_210_late"], 5.0)
check(big is not None, "streckung: der große Tag wird gar nicht gestreckt")
big = big or []
eq(sum(block[0] for block in big), 300, "streckung: der große Tag trifft die geplante Dauer nicht")
for index, block in enumerate(W.BY_KEY["z2_210_late"]["blocks"]):
    if not W.is_elastic(block):
        eq(big[index][0] if index < len(big) else None, block[0],
           f"streckung: der feste Abschnitt '{block[2]}' des großen Tages wurde gedehnt")

# and it refuses where it must
check(W.stretch_blocks(W.BY_KEY["z2_90"], None) is None, "streckung: ohne Stunden gestreckt")
check(W.stretch_blocks(W.BY_KEY["z2_90"], 95 / 60) is None,
      "streckung: gleiche Dauer erzeugt trotzdem eine Streckung")
check(W.stretch_blocks(W.BY_KEY["z2_90"], 0.2) is None,
      "streckung: die festen Abschnitte allein füllen die Dauer schon — trotzdem gestreckt")
check(W.stretch_blocks({"blocks": []}, 3.0) is None, "streckung: leere Vorlage gestreckt")

# rounding never changes the total silently
for minutes in range(80, 400, 7):
    out = W.stretch_blocks(W.BY_KEY["z2_150"], minutes / 60)
    if out is not None:
        eq(sum(block[0] for block in out), minutes, f"streckung: Summe bei {minutes} min")

# what the session payload says about it
long_day = W.rate_sessions([{"title": "Langer Tag", "workout": "z2_90", "hours": 4.0}],
                           "ready", budget=400, ftp=215)[0]
check(long_day["stretched"] is True, "streckung: der lange Tag gilt als ungestreckt")
eq(long_day["minutes"], 240, "streckung: die Payload nennt nicht die gestreckte Dauer")
eq(long_day["template_minutes"], 95, "streckung: die Dauer der Vorlage fehlt in der Payload")
eq(long_day["elastic_sections"], ["gleichmäßig"], "streckung: der gedehnte Abschnitt wird nicht benannt")
note = long_day.get("stretch_note") or {}
for part in ("rule", "evidence", "limit"):
    check(bool(note.get(part)), f"streckung: der Hinweis hat kein Feld {part}")
check("absoluten Minuten" in note.get("evidence", ""),
      "streckung: der Beleg nennt nicht, dass Aufwärmen absolut verschrieben wird")
check("NICHT mitwächst" in note.get("evidence", ""),
      "streckung: der Beleg sagt nicht, dass das Einrollen nicht mitwächst")
check("Less is more" in note.get("evidence", "") or "50 Minuten" in note.get("evidence", ""),
      "streckung: der Befund zum zu langen Aufwärmen fehlt")
check("absolut" in note.get("evidence", ""),
      "streckung: dass Intervalle absolut stehen, fehlt im Beleg")
check("Setzung" in note.get("limit", ""),
      "streckung: die Verteilung auf den gleichmäßigen Block gilt nicht als Setzung")
check("nicht\ngemessen" in note.get("limit", "").replace(" ", "\n"),
      "streckung: die Setzung wird nicht gegen eine Messung abgegrenzt")
# und die beiden Aussagen stehen NICHT im selben Feld - sonst geht die eine
# für die andere durch
check("Setzung" not in note.get("evidence", ""),
      "streckung: die Setzung steht im Belegfeld")
check("Less is more" not in note.get("limit", ""),
      "streckung: der Beleg steht im Grenzfeld")

# the step list follows the stretched sections, not the template's own text
check("225m" in (long_day["text_w"] or ""), "streckung: die Schrittliste zeigt weiter die Vorlage")
check("80m" not in (long_day["text_w"] or ""), "streckung: die alte Dauer steht noch in der Schrittliste")

quality = W.rate_sessions([{"title": "SweetSpot", "workout": "sweetspot_2x20", "hours": 1.2}],
                          "ready", budget=400, ftp=215)[0]
check(quality["stretched"] is False, "streckung: eine Intervalleinheit wurde gestreckt")
eq(quality["minutes"], 70, "streckung: die Vorlage wurde verändert")
eq(quality["template_minutes"], 70, "streckung: die ungestreckte Einheit meldet zwei Dauern")
fixed_note = quality.get("stretch_note") or {}
check("kein" in fixed_note.get("rule", ""), "streckung: der Festfall wird nicht begründet")
check("absolut" in fixed_note.get("evidence", ""),
      "streckung: der Festfall nennt nicht, dass Intervalle absolut stehen")
check("erfinden" in fixed_note.get("limit", ""),
      "streckung: der Festfall begründet nicht, warum nicht gedehnt wird")
eq(quality["elastic_sections"], [], "streckung: eine Intervalleinheit meldet dehnbare Abschnitte")

# the load does NOT come from the stretched block list - it stays the linear
# scaling of the catalogue load, one place (Befund 3 aus Paket I)
eq(long_day["load"], W.session_load(W.BY_KEY["z2_90"], 4.0),
   "streckung: die Last wird jetzt aus den Blöcken gerechnet — zweiter Rechenweg")

# ==============================================================================
# Paket N - der Stufentest als Einheit (docs/ausbau.md N)
# ==============================================================================
# Das Durability-Protokoll ist in 0.51.0 entfallen. Was hier steht, prueft den
# Test, der an seine Stelle getreten ist - und die Regeln, die aus K
# uebernommen wurden, weil sie fuer JEDE Messeinheit gelten.

# --- 1 · EIN GEWOEHNLICHER KATALOGEINTRAG -------------------------------------
# Anders als das abgeloeste Protokoll hat der Stufentest eine FESTE Form: er
# braucht keinen Anker und keine abgeleitete Dauer. Deshalb steht er in
# LIBRARY/BY_KEY wie alles andere - und genau das muss zugesichert sein, sonst
# schleicht sich der Sonderweg wieder ein.
check("ramp_test" in W.BY_KEY, "N: der Stufentest steht nicht im Katalog")
check(W.BY_KEY["ramp_test"] in W.LIBRARY, "N: der Eintrag ist nicht in LIBRARY")
_fam = [f for f in W.FAMILIES if f[0] == "ramp_test"]
eq(len(_fam), 1, "N: der Stufentest hat keine eigene Familie")
eq(_fam[0][2], ["ramp_test"], "N: die Familie traegt einen fremden Eintrag")
# Eigene Familie und KEINE Spielart der langen Fahrt: eine Messung ist eine
# andere Art von Einheit als ein Training.
for _family, _label, _keys in W.FAMILIES:
    if _family != "ramp_test":
        check("ramp_test" not in _keys,
              f"N: der Stufentest haengt zusaetzlich in der Familie {_family}")

# --- 2 · DIE EINZIGEN FESTEN ZAHLEN SIND DIE DAUERN (N1) ----------------------
# Die Leistungen leiten sich aus den eigenen Werten ab; die Prozentwerte in
# `blocks` sind eine ERWARTUNG fuer die Lastschaetzung. Was fest steht, sind
# Einrollen, Ausrollen und die Rampensteigung - und die stehen in const.py,
# nicht im Katalogeintrag.
_ramp_src = _RAMP_SRC = (Path(__file__).resolve().parents[1] / "custom_components"
                         / "intervals_icu" / "workouts.py").read_text(encoding="utf-8")
# NUR DAS DICT, nicht alles bis LIBRARY.append (0.51.1). Die Textsuche nahm
# RAMP_TEST_STANDARD und die Kommentare mit - und schlug damit auf Prosa an
# ("im Fenster 0 bis 10 Minuten", ein Kommentar, der die alte Zeichenkette
# zitiert). Ein Waechter, der bei richtigem Text Alarm gibt, wird entschaerft
# statt befolgt; genau davor warnt der Kommentar an JUDGEMENT_INPUTS. Der AST
# trifft den Abschnitt, um den es geht, ohne zu raten.
_entry_src = next(
    _ast.get_source_segment(_ramp_src, _node.value)
    for _node in _ast.parse(_ramp_src).body
    if isinstance(_node, _ast.Assign)
    and any(getattr(t, "id", None) == "RAMP_TEST" for t in _node.targets))
check(_entry_src is not None and '"blocks"' in _entry_src and "RAMP_TEST_STANDARD = [" not in _entry_src,
      "N: der gescannte Abschnitt ist nicht der Katalogeintrag - der Waechter "
      "sieht woanders hin als er soll")
for _literal, _name in ((" 15 ", "Einrolldauer"), (" 10 ", "Ausrolldauer"),
                        (" 5 W", "Rampensteigung")):
    check(_literal not in _entry_src,
          f"N const: {_name} steht als Zahl im Katalogeintrag statt in const.py")
# Gegenprobe, gezaehlt und benannt: die Ausdruecke finden eine eingebaute Zahl.
check(" 5 W" in "- je Minute 5 W mehr", "N const Gegenprobe: eine eingebaute "
      "Zahl wird NICHT gefunden - der Waechter ist blind")
eq(W.BY_KEY["ramp_test"]["minutes"],
   W.RAMP_WARMUP_MIN + W.RAMP_EXPECTED_MIN + W.RAMP_COOLDOWN_MIN,
   "N: die Gesamtdauer ist nicht die Summe ihrer Abschnitte")

# --- 2a · UND DIE ANDERE HAELFTE VON N1: KEINE LEISTUNGSZAHLEN (0.51.1) ------
# Der Waechter darueber bewacht die AUSNAHME (die Dauern duerfen fest sein) und
# sagte nichts ueber die REGEL (die Leistungen duerfen es nicht). Genau deshalb
# ging "ramp 60-115%" durch: eine Rampe, die an der FTP haengt, endete bei
# diesem Athleten 27 W UNTER der Leistung, bei der er schon mit alpha 0,47
# misst - die zweite Schwelle war nicht erreichbar (§7, achtzehnter Fall).
# Die zwei Rueckfall-Prozente stehen jetzt in const.py und tragen dort ihren
# Grund; im Katalogeintrag darf keine nackte Leistungszahl mehr stehen.
for _literal, _name in ((" 60,", "Rueckfall-Startleistung"), (" 90,", "Rampenmitte"),
                        ("60-115", "die Rampenspanne"), (" 115,", "Rueckfall-Endleistung")):
    check(_literal not in _entry_src,
          f"N1: {_name} steht als Zahl im Katalogeintrag statt in const.py")
# Gegenprobe, gezaehlt und benannt: die Ausdruecke finden so eine Zahl auch.
check(" 90," in '    (RAMP_EXPECTED_MIN, 90, "Rampe"),',
      "N1 Gegenprobe: eine eingebaute Leistungszahl wird NICHT gefunden - "
      "der Waechter ist blind")
check("60-115" in "- 30m ramp 60-115% (5 W/min)",
      "N1 Gegenprobe: die Rampenspanne wird NICHT gefunden - der Waechter ist blind")

# --- 2b · DIE DAUER WIRD GERECHNET, NICHT GESETZT (0.51.1) -------------------
# Vorher standen Dauer (30 min), Steigung (5 W/min) und Spanne (55 % der FTP)
# nebeneinander und passten nur bei EINER einzigen FTP zusammen: 272,7 W. Bei
# 200 W behauptete die Karte 30 Minuten fuer eine Rampe, die nach 22 zu Ende
# ist. Die Zusicherung haelt jetzt alle drei gegeneinander - und weil die Dauer
# GERECHNET wird, ist der Widerspruch gar nicht mehr herstellbar.
_CURVE = {"measured": [{"hour": 1, "t": 0.5, "watts": 152.9, "n": 11},
                       {"hour": 2, "t": 1.5, "watts": 137.6, "n": 12}], "paired": [],
          # 0.67.4 (S3): die Kette der Kachel, wie fatigue.curve sie liefert
          "plan": [{"hours": 1, "watts": 152.9}, {"hours": 2, "watts": 137.6}]}
_BLOCKS = {"families": {"vo2max": {"source_ok": True, "sessions": 15,
    "from": "2026-06-03", "to": "2026-09-01",
    "latest": {"date": "2026-09-01", "first_watts": 257, "first_alpha": 0.472,
               "median_watts": 250, "median_alpha": 0.401, "n_blocks": 4}}}}


def _ramp_case(label, **kw):
    """Eine skalierte Karte plus ihre Zusicherung ueber die drei Zahlen."""
    entry = W.scaled(W.BY_KEY["ramp_test"], 200.0, 160, None,
                     kw.get("curve"), kw.get("blocks"), kw.get("ramp"), None, kw.get("ga"))
    proto = entry.get("ramp_protocol") or {}
    if not proto:
        check(False, f"N1 {label}: die Karte traegt kein ramp_protocol")
        return entry, proto
    span = proto["end_w"] - proto["start_w"]
    # TOLERANZ AUS DEM UNTERSCHIED DER RECHENWEGE, nicht aus Wunschgenauigkeit
    # (§7): die Dauer ist auf ganze Minuten gerundet, also darf sie um bis zu
    # eine halbe Schrittweite von der Spanne abweichen - mehr nicht.
    check(abs(span - proto["minutes"] * W.RAMP_STEP_W_PER_MIN) <= W.RAMP_STEP_W_PER_MIN / 2,
          f"N1 {label}: Spanne {span} W, Steigung {W.RAMP_STEP_W_PER_MIN} W/min und "
          f"Dauer {proto['minutes']} min passen nicht zusammen")
    eq(entry["minutes"], W.RAMP_WARMUP_MIN + proto["minutes"] + W.RAMP_COOLDOWN_MIN,
       f"N1 {label}: die Gesamtdauer ist nicht die Summe der Abschnitte")
    eq([b[1] for b in entry["blocks_w"]],
       [proto["start_w"], proto["end_w"], proto["start_w"]],
       f"N1 {label}: die Abschnitte tragen andere Zahlen als das Protokoll")
    return entry, proto


_ftp_only, _p_ftp = _ramp_case("Rueckfall")
# 0.68.0: der Start ist die Grundlagenvorgabe fuer eine Stunde - Ziel der
# Umkehrung (hier als Fixture 138 W), sonst ihre Grenze.
_GA_N2 = {"mid": 90.6, "limit_alpha": 1.0, "target_alpha": 1.3, "missing": None,
          "hours": [{"hours": 1, "n": 11, "load_w": 150.0, "alpha": 1.17, "limit_w": 165.4, "target_w": 138.0}]}
_full, _p_full = _ramp_case("gemessen", curve=_CURVE, blocks=_BLOCKS, ga=_GA_N2)

# --- 2c · JEDE SEITE IHRE EIGENE KETTE, JEDE STUFE BESCHRIFTET ---------------
eq(_p_ftp["start_source"]["kind"], "ftp", "N2 Rueckfall: der Start ist nicht die FTP")
eq(_p_ftp["end_source"]["kind"], "ftp", "N2 Rueckfall: das Ende ist nicht die FTP")
for _side in ("start_source", "end_source"):
    check("Rückfall" in _p_ftp[_side]["label"],
          f"N2 Rueckfall: {_side} ist nicht als Rueckfall beschriftet")
eq([b[1] for b in _ftp_only["blocks_w"]], [120, 230, 120],
   "N2 Rueckfall: der Einsteigerfall hat sich veraendert")

eq(_p_full["start_source"]["kind"], "ga",
   "N2: der Start kommt nicht aus der Umkehrung (Grundlagenvorgabe fuer eine Stunde)")
eq(_p_full["end_source"]["kind"], "blocks",
   "N2: das Ende kommt nicht aus der Blockmessung")
eq(_p_full["start_w"], 138, "N2: die Startleistung ist nicht die Grundlagenvorgabe")
eq(_p_full["end_w"], 307, "N2: die Endleistung ist nicht Leitzahl plus Reserve")
eq(_p_full["minutes"], 34, "N2: die Rampendauer ist nicht gerechnet")

# DIE LEITZAHL, NICHT DIE TRAININGSVORGABE (N2). Die Leitzahl steht am ersten
# eingeschwungenen Block (257 W bei alpha 0,47) und ist per Definition dieselbe
# Groesse wie HRVT2. Die Trainingsvorgabe steht am Median-alpha (250 W bei
# 0,40) und ist eine andere. Sie zu nehmen waere 0.49.2 in neuer Gestalt -
# deshalb wird hier nicht nur der Wert geprueft, sondern der FALSCHE
# ausdruecklich ausgeschlossen.
eq((_p_full["end_source"]["lead"] or {}).get("watts"), 257,
   "N2: das Ende haengt nicht an der Leitzahl")
check(_p_full["end_w"] != round(250 + W.RAMP_END_RESERVE_MIN * W.RAMP_STEP_W_PER_MIN),
      "N2: das Ende ist aus der TRAININGSVORGABE gerechnet statt aus der "
      "Leitzahl - das ist 0.49.2 in neuer Gestalt")

# UND DER GRUND, WARUM ES DIESE RESERVE GIBT: ohne sie endet die Rampe AUF der
# Leitzahl, und die flache Strecke unter 0,5 wird nie aufgezeichnet. Der Fall,
# den 0.51.0 ausgeliefert hat, wird hier namentlich ausgeschlossen.
check(_p_full["end_w"] > 257,
      "N1: die Rampe endet nicht ueber der eigenen Leitzahl - die zweite "
      "Schwelle waere nicht erreichbar, genau der Fehler aus 0.51.0")
eq(_p_full["end_source"]["reserve_w"], W.RAMP_END_RESERVE_MIN * W.RAMP_STEP_W_PER_MIN,
   "N1: die Reserve ist nicht die ausgewiesene Zeit mal die Steigung")

# --- 2d · DER GEMISCHTE FALL FAELLT GANZ ZURUECK, NICHT HALB ----------------
# Gemessener Start neben einem geratenen Ende waere derselbe Gleichstandsfehler
# wie in 0.47.1: eine Seite wandert mit der Messung, die andere nicht.
_hoch = {"measured": [{"hour": 1, "t": 0.5, "watts": 400.0, "n": 11}], "paired": []}
_gemischt, _p_mix = _ramp_case("gemischt", curve=_hoch)
eq(_p_mix["start_source"]["kind"], "ftp",
   "N2: der Start bleibt gemessen, obwohl das Ende auf die FTP zurueckfaellt")
eq(_p_mix["end_source"]["kind"], "ftp", "N2 gemischt: das Ende ist nicht die FTP")
check(_p_mix["end_w"] > _p_mix["start_w"],
      "N2 gemischt: das Ende liegt nicht ueber dem Start")

# --- 2e · DER STUFENTEST ALS ZWEITE STUFE, WENN KEINE BLOCKMESSUNG DA IST ----
_rt = {"date": "2026-09-20", "result": {
    "hrvt1": {"watts": 150, "alpha": 0.75, "hr": 152},
    "hrvt2": {"watts": 265, "alpha": 0.5, "hr": 178}}}
_aus_test, _p_test = _ramp_case("aus dem Test", ramp=_rt)
eq(_p_test["start_source"]["kind"], "ramp_hrvt1",
   "N2: ohne Kurve greift die zweite Stufe des Starts nicht")
eq(_p_test["end_source"]["kind"], "ramp_hrvt2",
   "N2: ohne Blockmessung greift die zweite Stufe des Endes nicht")
eq(_p_test["end_w"], 315, "N2: HRVT2 plus Reserve ergibt eine andere Zahl")

# --- 2f · KOMMT AN, WAS DIE KARTE ANZEIGEN SOLL? (0.51.1) -------------------
# Die neun Punkte der Beschreibung waren in 0.51.0 UNSICHTBAR: das Backend
# legte sie als `protocol` in die ramp_tests-Payload, das Panel liest sie als
# `entry.standard` an der EINHEIT - zwei Payloads, zwei Namen, und ein `|| []`
# hat die Luecke in eine leere Liste verwandelt. Kein Test schlug an, weil der
# eine Test die Liste im Bauteil prueft und der andere die Darstellung im
# Panel; dazwischen sah niemand hin (§7, neunzehnter Fall).
#
# DIESER WAECHTER SIEHT DAZWISCHEN. Er liest, welche Felder die Einheitenkarte
# aus `entry` holt, und haelt sie gegen die WIRKLICH gebaute Payload.
_PANEL_SRC = (Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"
              / "frontend" / "intervals-panel.js").read_text(encoding="utf-8")
_panel_fields = set(re.findall(r"\bentry\.(\w+)", _PANEL_SRC))
check(len(_panel_fields) > 20, "4: die Feldliste der Karte ist leer - der Ausdruck trifft nicht")

# Felder, die diese EINE Einheit nicht hat, jedes mit Grund. Handgepflegt, also
# mit Vollstaendigkeitspruefung darunter (vierte Bauregel).
_NOT_FOR_RAMP = {
    # 0.68.0: die Karte liest ga_blocks statt curve_blocks/curve_share; der
    # Stufentest traegt es nicht (er liest die Umkehrung nur fuer den Start).
    "baseline", "block_source", "catalogue_load", "catalogue_minutes", "ga_blocks",
    "ga_missing", "detail", "elastic_sections", "fit_reason", "fuel", "hr_source",
    "label", "note", "ramp_source", "stage", "stretch_note", "stretched", "tag",
    "unit", "value", "weight", "why", "z", "family", "family_label",
    # Seit 0.51.1 bewusst OHNE Pulsfenster: bei einer Rampe waere eine Spanne
    # ein ZIEL, und ein Ziel gibt es in diesem Test nicht (§7, zwanzigster
    # Fall). An seiner Stelle steht `hr_note`, und das wird oben geprueft.
    "hr_window",
    # Seit B2c: der Stufentest hat seine eigene Herleitung (`derivation`) und
    # bekommt keine zweite - `explain` ist fuer ihn bewusst None.
    "explain",
}
_card = W.scaled(W.BY_KEY["ramp_test"], 200.0, 160, None, _CURVE, _BLOCKS, None, None, _GA_N2)
for _field in sorted(_panel_fields - _NOT_FOR_RAMP):
    check(_field in _card,
          f"4: die Karte liest entry.{_field}, aber die Payload des Stufentests "
          f"traegt das Feld nicht - es kaeme als leerer Rueckfall an")
# DIE SCHAERFERE BAUART: den falschen Fall NAMENTLICH ausschliessen. Eine
# Ausnahmeliste, die ein vorhandenes Feld nennt, ist veraltet - und eine
# veraltete Ausnahmeliste deckt genau das naechste fehlende Feld zu.
for _field in sorted(_NOT_FOR_RAMP):
    check(_field not in _card,
          f"4: {_field} steht in der Ausnahmeliste, ist aber vorhanden - "
          f"die Liste ist veraltet und deckt das naechste fehlende Feld zu")
# Und die drei, um die es geht, einzeln und benannt.
eq(len(_card.get("standard") or []), len(W.RAMP_TEST_STANDARD),
   "4: die Beschreibung kommt nicht vollstaendig an der Einheit an")
check(len(_card.get("derivation") or []) >= 4,
   "4: der Rechenweg der Rampe fehlt an der Karte")
check(_card.get("hr_note") and "Ziel" in _card["hr_note"],
      "3: der Satz, der die Pulsspanne ersetzt, kommt nicht an der Karte an")
check("hr_note" in _PANEL_SRC, "3: die Karte liest hr_note gar nicht")
check("ramp_segment" in _PANEL_SRC and _card.get("ramp_segment"),
      "4: die Rampe wird nicht als Rampe gezeichnet - ramp_segment fehlt")
# UEBER .get(), nicht ueber [] - erste Bauregel (§9). Die erste Fassung dieser
# zwei Zeilen stand auf [] und ist bei der Gegenprobe ABGESTUERZT statt zu
# zaehlen: genau der Fall aus §7, sechzehnter Fall, und zwar in dem Test, der
# ihn aufgeschrieben hat. Die Regel ist nicht erzwungen; sie haelt nur, wo
# jemand sie anwendet.
eq((_card.get("ramp_segment") or {}).get("start_w"), _p_full.get("start_w"),
   "4: der gezeichnete Rampenanfang weicht vom Protokoll ab")
eq((_card.get("ramp_segment") or {}).get("end_w"), _p_full.get("end_w"),
   "4: das gezeichnete Rampenende weicht vom Protokoll ab")
check("standard" in _PANEL_SRC and "derivation" in _PANEL_SRC,
      "4: die Karte liest die beiden Felder gar nicht mehr")
# EINE Quelle: der Text darf nicht zusaetzlich in einer zweiten Payload liegen.
_WS_SRC = (Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"
           / "websocket.py").read_text(encoding="utf-8")
check('"protocol": workout_lib.RAMP_TEST_STANDARD' not in _WS_SRC,
      "4: die Beschreibung liegt wieder in ZWEI Payloads - eine davon liest niemand")

# --- 3 · DIE ZUSTANDSREGEL AUS PAKET I, MIT EIGENER BEGRUENDUNG (K4) ----------
# Uebernommen aus dem abgeloesten Protokoll, weil der Grund derselbe ist: bei
# gelbem oder rotem Zustand ist die Zahl FALSCH, nicht die Einheit zu teuer.
verdict, reason = W.fit_for("ramp_test", "ready", W.BY_KEY["ramp_test"]["intensity"])
eq(verdict, "ok", "N: der Test ist im gruenen Zustand nicht vorgesehen")
for _state in ("strained", "recovering", "slump"):
    verdict, reason = W.fit_for("ramp_test", _state, W.BY_KEY["ramp_test"]["intensity"])
    check(verdict != "ok", f"N: der Test wird im Zustand {_state} vorgeschlagen")
    check("Messfehler" in reason,
          f"N: im Zustand {_state} steht die uebliche Kostenbegruendung statt "
          f"der Messfehler-Begruendung")
# Gegenprobe: eine ANDERE Familie bekommt diese Begruendung NICHT - sonst
# prueft die Zeile darueber nur, dass der Satz irgendwo vorkommt.
_, _other = W.fit_for("vo2max", "strained", 95)
check("Messfehler" not in _other,
      "N Gegenprobe: die Messfehler-Begruendung steht auch bei einer "
      "Trainingsfamilie - der Test prueft nichts")

# --- 4 · DIE BESCHREIBUNG IST DER WICHTIGSTE TEIL (N5) ------------------------
# Sie entscheidet, ob jemand den Test richtig faehrt oder eine Stunde umsonst
# tritt. Geprueft wird nicht die Formulierung, sondern dass jeder Punkt
# VORKOMMT, den der Auftrag verlangt - und dass jede Zahl ihren Grund mitbringt.
_std = " ".join(W.RAMP_TEST_STANDARD)
for _pflicht, _was in (("BRUSTGURT", "der Brustgurt"),
                       ("Handgelenk", "warum die optische Messung nicht taugt"),
                       ("Ausgeruht", "der ausgeruhte Zustand"),
                       ("einrollen", "das Einrollen"),
                       ("GESETZT", "dass das Einrollen eine Setzung ist"),
                       ("Sauerstoffaufnahme", "warum die Rampe flach ist"),
                       ("nicht aus dem Sattel", "das Verhalten waehrend der Rampe"),
                       ("VORGESEHEN", "dass der Abbruch vorgesehen ist"),
                       ("NICHT abkürzen", "dass das Ausrollen nicht gekuerzt wird"),
                       ("Teil der Messung", "warum es nicht gekuerzt wird"),
                       ("MARKIEREN", "dass die Fahrt markiert werden muss"),
                       ("NICHT kann", "was der Test nicht kann")):
    check(_pflicht in _std, f"N Beschreibung: {_was} fehlt")
# Seit Rechenweg e1 (Schritt 3): was nicht nachgelesen ist, steht so da; das
# Einrollen ist Grenze der Hochpunktsuche; das Lastende haengt am Ausrollen.
check("nicht nachgelesen" in _std,
      "N Beschreibung e1: Ein-/Ausrollen als Quellenvorgabe behauptet statt 'nicht nachgelesen'")
check("Weder Rogers" not in _std and "nennt ein Einrollen" not in _std,
      "N Beschreibung e1: die unbelegte Behauptung 'nennt kein Einrollen' steht noch da")
check("keine der beiden Arbeiten" not in _std,
      "N Beschreibung e1: 'keine der beiden Arbeiten' (Ausrolldauer) ist nicht nachgelesen")
check("Rampenbeginn" in _std and "FLACH" in _std,
      "N Beschreibung e1: warum das Einrollen flach sein muss (Grenze der Hochpunktsuche), fehlt")
check("wichtig ist nur" not in _std and "solange dein" not in _std,
      "N Beschreibung e1: stabil unter 0,5 wird noch als einzige Bedingung dargestellt")
check("Fahrtlänge minus" in _std and "zwei Minuten" in _std,
      "N Beschreibung e1: der zweite Grund gegen ein veraendertes Ausrollen (Lastende) fehlt")
check("Rogers 2021a (Laufband) hieß das" in _std,
      "N Beschreibung e1: das Abbruchkriterium ist nicht auf Rogers 2021a praezisiert")
# Und die Zahlen kommen aus const.py, nicht aus dem Text.
for _zahl in (W.RAMP_WARMUP_MIN, W.RAMP_COOLDOWN_MIN, W.RAMP_STEP_W_PER_MIN):
    check(str(_zahl) in _std, f"N Beschreibung: {_zahl} wird gar nicht genannt")

# --- 5 · DAS ABGELOESTE PROTOKOLL IST WIRKLICH WEG ---------------------------
# Ein halb entfernter Sonderweg ist schlimmer als keiner: die Karte zeigte
# sonst eine Einheit, die es nicht mehr gibt.
for _weg in ("durability_test_fresh", "durability_test_fatigued"):
    check(_weg not in W.BY_KEY, f"N: {_weg} steht noch im Katalog")
for _weg in ("fatigued_session", "protocol_block", "protocol_load"):
    check(not hasattr(W, _weg), f"N: {_weg} existiert noch in workouts.py")
check("durability_test" not in _ramp_src,
      "N: die alte Familie steht noch im Quelltext")

# ==============================================================================
# Paket N2 - die Quellenkette je Familie
# ==============================================================================
# Die Rangfolge ist je Familie VERSCHIEDEN. Sie steht deshalb als EINE Tabelle
# in workouts.py, und dieser Abschnitt haelt sie gegen das, was `scaled()`
# tatsaechlich tut - eine Rangfolge in drei if-Zweigen driftet beim naechsten
# Umbau auseinander (§7, Listen-Klasse).
_RAMP = {"date": "2026-09-14",
         "result": {"hrvt1": {"alpha": 0.75, "watts": 196.0, "hr": 152.0},
                    "hrvt2": {"alpha": 0.5, "watts": 248.0, "hr": 171.0}}}
_BLOCKS = {"families": {"vo2max": {
    "source_ok": True, "sessions": 6, "from": "2026-07-23", "to": "2026-09-08",
    "hr_window": {"low": 176, "high": 185, "n": 6},
    "latest": {"date": "2026-09-08", "median_watts": 252, "median_alpha": 0.41,
               "n_blocks": 4}}}}
_CURVE = {"measured": [{"hour": 1, "t": 0.5, "watts": 152.5, "n": 26},
                       {"hour": 2, "t": 1.5, "watts": 142.2, "n": 23}],
          "literature": [{"hour": 1, "t": 0.5, "watts": 152.5},
                         {"hour": 2, "t": 1.5, "watts": 149.1}],
          "solid_until_hour": 2, "thin_until_hour": 2,
          "plan": [{"hours": 1, "watts": 152.5}, {"hours": 2, "watts": 142.2}]}

# --- 1 · DIE TABELLE IST VOLLSTAENDIG UND ENDET IMMER BEI DER FTP -------------
for _fam, _label, _keys in W.FAMILIES:
    if _fam in ("recovery", "return", "ramp_test"):
        continue   # keine Wattvorgabe aus einer Messung, das ist Absicht
    check(_fam in W.SOURCE_CHAIN, f"N2: Familie {_fam} steht in keiner Kette")
    _chain = W.SOURCE_CHAIN.get(_fam, ())
    eq(_chain[-1:] and _chain[-1], "ftp",
       f"N2: die Kette von {_fam} endet nicht auf dem Rueckfall")
    for _step in _chain:
        check(_step in W.SOURCE_LABEL,
              f"N2: die Stufe {_step} traegt keine Beschriftung — eine Zahl "
              f"ohne Herkunft ist in diesem Projekt zweimal als Messung "
              f"gelesen worden, die keine war")
check("nicht gemessen" in W.SOURCE_LABEL["ftp"],
      "N2: der Rueckfall ist nicht als Rueckfall beschriftet")

# --- 2 · DIE RANGFOLGE WIRD ERZWUNGEN, NICHT BESCHRIEBEN ---------------------
# Fuer jede Familie: die hoechste Stufe, die Daten hat, muss gewinnen. Geprueft
# wird nicht der Quelltext, sondern das ERGEBNIS von scaled().
_GA_N2b = {"mid": 90.6, "limit_alpha": 1.0, "target_alpha": 1.3, "missing": None,
           "hours": [{"hours": 1, "n": 11, "load_w": 150.0, "alpha": 1.17, "limit_w": 165.4, "target_w": 138.0}]}
for _fam, _first, _key in (("vo2max", "blocks", "vo2_4x4"),
                           ("endurance", "ga", "z2_90")):
    _entry = W.BY_KEY[_key]
    _alles = W.scaled(_entry, 215, 146, curve=_CURVE, blocks=_BLOCKS, ramp=_RAMP, ga=_GA_N2b)
    eq(_alles.get("watt_source"), _first,
       f"N2: bei {_fam} gewinnt nicht die erste Stufe der Kette")
    # Faellt die erste Stufe weg, muss GENAU die zweite greifen. Der Zugriff
    # ist null-geprueft: eine gekuerzte Kette ist genau das, was eine Mutation
    # herstellt, und mit [1] stuerzt der Test dann ab statt zu zaehlen (§9).
    _kette = W.SOURCE_CHAIN.get(_fam) or ()
    check(len(_kette) >= 2, f"N2: die Kette von {_fam} hat keine zweite Stufe")
    _zweite = _kette[1] if len(_kette) >= 2 else None
    _ohne = W.scaled(_entry, 215, 146, ramp=_RAMP) if _first != "ramp_hrvt2" else \
        W.scaled(_entry, 215, 146)
    eq(_ohne.get("watt_source"), _zweite,
       f"N2: bei {_fam} greift nach dem Wegfall der ersten Stufe nicht {_zweite}")

# Fixture-Beweis: die drei Quellen tragen UNTERSCHIEDLICHE Zahlen. Waeren sie
# gleich, pruefte der Abschnitt oben ueberhaupt keine Rangfolge.
check(len({252, 248, 215}) == 3,
      "N2 Fixture-Beweis: Blockmessung, Stufentest und FTP tragen dieselbe "
      "Zahl — die Rangfolge waere nicht pruefbar")

# --- 3 · DER STUFENTEST STEUERT VORERST NICHTS (Variante B, 16.09.2026) ------
# Der Zweig in `scaled()` setzte jeden Arbeitsblock auf HRVT2 x 1,0 (§7, Fall
# 38). Bis die Ablesung je alpha-Korridor gebaut ist (§10), steht der Test auf
# keiner Stufe - und ein GEFUELLTER Test aendert an keiner Einheit eine Zahl.
# Die Pruefungen zu Gleichstand und Anteil am Rampenzweig sind damit ohne
# Gegenstand und entfallen; sie kommen mit dem Neubau zurueck.
check(not any(s.startswith("ramp_") for c in W.SOURCE_CHAIN.values() for s in c),
      "N2 B: der Stufentest steht wieder in einer Quellenkette, obwohl die Ableitung "
      "zur Vorgabe nicht gebaut ist")
# TREFFERZUSICHERUNG FUER DIE FIXTURE: der Test traegt an BEIDEN Schwellen Watt
# und Puls, und seine Watt liegen weit neben der FTP-Rechnung - stuende er in
# einer Kette, aenderte er die Zahlen (so war es bis 0.59.0).
_ftp_vo2 = [b[1] for b in W.scaled(W.BY_KEY["vo2_4x4"], 215, 146).get("blocks_w") or []]
check(all((_RAMP["result"].get(k) or {}).get("watts") and (_RAMP["result"].get(k) or {}).get("hr")
          for k in ("hrvt1", "hrvt2")) and 248 not in _ftp_vo2 and 196 not in _ftp_vo2,
      "N2 B Fixture-Beweis: der Test ist nicht gefuellt oder faellt mit der FTP-Rechnung zusammen")
# AUSNAHME, bewusst: die Karte des Stufentests selbst liest ihre ERWARTETE
# Rampe (Start/Ende) ueber RAMP_START_CHAIN/RAMP_END_CHAIN aus dem letzten Test -
# beschriftet als Erwartung, keine Vorgabe, und nicht der Zweig aus Fall 38.
check("ramp_test" in W.BY_KEY and any(s.startswith("ramp_") for s in W.RAMP_END_CHAIN),
      "N2 B Ausnahme: die Stufentest-Karte liest ihre Erwartung nicht mehr aus dem Test - "
      "dann gehoert sie in die Schleife unten")
for _key in sorted(k for k in W.BY_KEY if k != "ramp_test"):
    _mit = W.scaled(W.BY_KEY[_key], 215, 146, ramp=_RAMP)
    _ohne_t = W.scaled(W.BY_KEY[_key], 215, 146)
    eq((_mit.get("blocks_w"), _mit.get("watt_source"), _mit.get("ramp_source")),
       (_ohne_t.get("blocks_w"), _ohne_t.get("watt_source"), _ohne_t.get("ramp_source")),
       f"N2 B: {_key} faehrt mit gefuelltem Stufentest andere Watt")
    eq((_mit.get("hr_window"), _mit.get("hr_point"), (_mit.get("hr_source") or {}).get("kind")),
       (_ohne_t.get("hr_window"), _ohne_t.get("hr_point"), (_ohne_t.get("hr_source") or {}).get("kind")),
       f"N2 B: {_key} traegt mit gefuelltem Stufentest einen anderen Puls")

# --- 4 · IM LEEREN ZUSTAND AENDERT SICH NICHTS -------------------------------
# Solange kein Stufentest markiert ist, muss die Kette EXAKT so entscheiden wie
# vor diesem Paket. Nicht "aehnlich" - Zahl fuer Zahl.
for _key in ("vo2_4x4", "sweetspot_2x20", "tempo_2x20", "threshold_4x10",
             "z2_90", "z2_210_late", "recovery_40", "z2_60"):
    _e = W.BY_KEY[_key]
    _ohne_alles = W.scaled(_e, 215, 146)
    for _leer in (None, {}, {"result": None}, {"result": {}},
                  {"result": {"hrvt1": None, "hrvt2": None}}):
        _mit_leer = W.scaled(_e, 215, 146, ramp=_leer)
        eq(_mit_leer.get("blocks_w"), _ohne_alles.get("blocks_w"),
           f"N2 Leerzustand: {_key} faehrt mit leerem Test andere Watt")
        eq(_mit_leer.get("watt_source"), _ohne_alles.get("watt_source"),
           f"N2 Leerzustand: {_key} nennt mit leerem Test eine andere Quelle")
        eq(_mit_leer.get("hr_window"), _ohne_alles.get("hr_window"),
           f"N2 Leerzustand: {_key} traegt mit leerem Test ein anderes HF-Fenster")
# Die Gegenprobe "ein gefuellter Test aendert etwas" entfaellt mit Variante B;
# ihre Rolle traegt der Fixture-Beweis in Abschnitt 3.

# --- 5 · (entfallen mit Variante B) ------------------------------------------
# Hier stand "share = 1,0 an der zweiten Schwelle" als PRUEFUNG - sie hielt genau
# den Zweig fest, der vier Familien auf dieselbe Wattzahl gesetzt haette (§7,
# Fall 38). Welcher Anteil oder welche Ablesung richtig ist, entscheidet der
# Neubau (§10), nicht eine Pruefung, die den alten Stand konserviert.

# --- L4: die Wattvorgabe kommt aus der eigenen Messung ------------------------
# Gestaffelt wird auf der GEPAARTEN Reihe; bis zur letzten gemessenen Stunde
# ist es Messung, darueber Studienform - und jeder Abschnitt sagt, welches.
CURVE = {
    "measured": [{"hour": 1, "t": 0.5, "watts": 153.0, "n": 11, "band": "solid"},
                 {"hour": 2, "t": 1.5, "watts": 138.0, "n": 12, "band": "solid"}],
    "paired": [{"from_hour": 1, "to_hour": 2, "delta": -11.0, "n": 10, "enough": True}],
    "literature": [{"hour": 1, "t": 0.5, "watts": 153.0},
                   {"hour": 2, "t": 1.5, "watts": 149.0},
                   {"hour": None, "t": 2.5, "watts": 143.0},
                   {"hour": None, "t": 3.5, "watts": 136.0}],
    # 0.67.4 (S3): die Einheit liest die KETTE DER KACHEL (Kette A, `plan`) -
    # die Fixture traegt sie wie fatigue.curve sie baut (153, dann -11 gepaart).
    "plan": [{"hours": 1, "watts": 153.0}, {"hours": 2, "watts": 142.0}],
}

# 0.67.4 (S3) -> 0.68.0: dieselbe Ablesestelle, jetzt in `ga_at` auf den Zeilen
# der Umkehrung (volle Stunden, belegt ab 3 Fahrten, sonst die letzte gut belegte).
_GA_S = {"mid": 90.6, "limit_alpha": 1.0, "target_alpha": None, "missing": None,
         "hours": [{"hours": 1, "n": 11, "load_w": 150.0, "alpha": 1.03, "limit_w": 153.0, "target_w": None},
                   {"hours": 2, "n": 12, "load_w": 150.0, "alpha": 0.91, "limit_w": 142.0, "target_w": None}]}
erste = W.ga_at(_GA_S, 60)
eq((erste["limit"], erste["hour"], erste["n"]), (153, 1, 11), "Stunde 1 kommt aus der Umkehrung, mit Belegung")
zweite = W.ga_at(_GA_S, 120)
eq((zweite["limit"], zweite["hour"]), (142, 2), "Stunde 2 liest die Zeile der Umkehrung")
spaet = W.ga_at(_GA_S, 210)
eq((spaet["hour"], spaet["limit"]), (2, 142), "jenseits des Belegten: die letzte gut belegte Stunde, nicht die Studienform")
duenn = {**_GA_S, "hours": [_GA_S["hours"][0], {**_GA_S["hours"][1], "n": 2}]}
eq(W.ga_at(duenn, 120)["hour"], 1, "zu wenige Fahrten in Stunde 2: die Einheit bleibt bei Stunde 1")
eq(W.ga_at(None, 90), None, "ohne Umkehrung gibt es keine Vorgabe daraus")

# --- 0.47.1 -> 0.68.0: DIE MESSUNG IST NICHT DIE VORGABE, und die Vorgabe der
# Grundlage ist seit 0.68.0 Ziel/Grenze der Umkehrung, nicht mehr 0,90 x
# Schwelle der p075-Kette. Die alten Wächter (Anteil der Schwelle, Studienform,
# Kurvenherkunft je Abschnitt) sind in den GA-Wächtern unten aufgegangen.
grund = W.scaled(W.BY_KEY["z2_60"], 200, 160, 185, CURVE)
eq(grund["watt_source"], "ftp", "ohne GA-Eingang (nur alte Kurve): die Grundlage faellt auf die FTP")
check("curve_blocks" not in grund and "curve_share" not in grund, "die p075-Kette rechnet nicht mehr in die Einheit")
sweet = W.scaled(W.BY_KEY["sweetspot_2x20"], 215, 160, 185, CURVE)
eq(sweet["watt_source"], "ftp", "SweetSpot bleibt bei der FTP")
eq(sweet["blocks_w"][1][1], round(215 * 90 / 100), "und behaelt seine Blockleistung")
eq(W.scaled(W.BY_KEY["z2_150"], 215, 160, 185, None)["watt_source"], "ftp", "ohne alles: Rueckfall auf die FTP")

_GA_A3 = {"mid": 90.6, "limit_alpha": 1.0, "target_alpha": 1.3, "missing": None,
          "hours": [{"hours": 1, "n": 18, "load_w": 139.6, "alpha": 1.336, "limit_w": 170.0, "target_w": 142.9}]}
# --- A3 · DIE WATTLISTE TRAEGT WATT - AUF JEDEM WEG, NICHT NUR AUF DEM FTP-WEG --
# Bis 0.56.0 druckte `steps_text(staged, None)` die gestaffelten WATT der
# gemessenen Wege mit Prozentzeichen: "45m 135%" fuer 135 W. Die Pruefung unter
# "10 Watt" oben lief nur ueber `scaled(entry, ftp, hr)` OHNE Messung - also
# ausschliesslich ueber den FTP-Weg, auf dem der Fehler nicht sitzt (§7).
_A3_FAELLE = (
    ("vo2_4x4", dict(curve=_CURVE, blocks=_BLOCKS, ramp=_RAMP), "blocks"),
    ("z2_60", dict(curve=_CURVE, blocks=_BLOCKS, ramp=_RAMP, ga=_GA_A3), "ga"),
    # Variante B: mit gefuelltem Test laufen beide ueber die FTP (§7, Fall 38).
    ("tempo_2x20", dict(curve=_CURVE, blocks=_BLOCKS, ramp=_RAMP), "ftp"),
    ("z2_90", dict(ramp=_RAMP), "ftp"),
    ("recovery_40", dict(curve=_CURVE, blocks=_BLOCKS, ramp=_RAMP), "ftp"),
)
_a3_quellen = set()
for _key, _kw, _soll in _A3_FAELLE:
    _e = W.scaled(W.BY_KEY[_key], 215, 146, **_kw)
    _quelle = _e.get("watt_source")
    _a3_quellen.add(_quelle)
    # TREFFERZUSICHERUNG FUER DIE FIXTURE: der Fall nimmt WIRKLICH den Weg,
    # fuer den er steht - sonst prueft die Zeile unten wieder nur den FTP-Weg.
    eq(_quelle, _soll, f"A3 Fixture: {_key} laeuft nicht ueber {_soll}")
    _text = _e.get("text_w") or ""
    check("%" not in _text, f"A3: {_key} ({_quelle}) druckt Prozent: {_text!r}")
    _zeilen = [z for z in _text.splitlines() if z.startswith("- ")]
    _watt = [b[1] for b in (_e.get("blocks_w") or [])]
    if _quelle != "ftp":
        # Nur die gestaffelten Wege schreiben Zeile fuer Zeile aus blocks_w;
        # der FTP-Weg rechnet die Vorlage um und behaelt ihre Wiederholungen.
        eq(len(_zeilen), len(_watt), f"A3: {_key} Zeilenzahl gegen blocks_w")
        for _z, _w in zip(_zeilen, _watt):
            check(f" {_w}w " in f"{_z} ", f"A3: {_key} Zeile traegt nicht {_w} W: {_z!r}")
    _ev = W.to_event(_e, "2026-09-17")
    check("%" not in _ev.get("description", ""),
          f"A3: {_key} ({_quelle}) Kalendereintrag traegt Prozent")
# Die Fixture deckt ALLE Stufen der Kette ab - fehlt eine, ist genau sie ungeprueft.
eq(sorted(_a3_quellen), sorted({"blocks", "ga", "ftp"}),
   "A3 Fixture-Beweis: nicht jede Quelle wird durchlaufen")
# Ohne FTP gibt es keine halbe Wattliste: Ein- und Ausrollen haetten keine Zahl.
_ohne_ftp = W.scaled(W.BY_KEY["vo2_4x4"], None, 146, curve=_CURVE, blocks=_BLOCKS, ramp=_RAMP)
check(any(b[1] is None for b in (_ohne_ftp.get("blocks_w") or [])),
      "A3 Fixture: ohne FTP traegt kein Abschnitt eine leere Zahl - der Fall ist nicht hergestellt")
check(_ohne_ftp.get("text_w") is None,
      f"A3: ohne FTP eine Wattliste mit Luecken erzeugt: {_ohne_ftp.get('text_w')!r}")
eq(W.watts_text([(10, 120, "a"), (5, None, "b")]), None,
   "A3: watts_text liefert eine Liste mit fehlender Zahl")
eq(W.watts_text([(10, 120, "a")]), "- 10m 120w  (a)", "A3: watts_text Form")

# --- B2b-2 · DER STUFENTEST NENNT JE ZAHL SEINE AUSWAHL ------------------------
# Start und Ende kommen von Natur aus aus zwei Ketten - entworfen, kein
# Widerspruch. Seit zwei Schaltern koennen die Ketten aus zwei AUSWAHLEN kommen
# („Marken / Namenserkennung"); dann steht es an der Zahl.
_mk = {"from_marks": True, "key": "marks", "label": "AUS DEN MARKEN"}
_nm = {"from_marks": False, "key": "names", "label": "AUS DEN NAMEN"}
_blk_lead = {"families": {"vo2max": {**_BLOCKS["families"]["vo2max"],
                                     "latest": {**_BLOCKS["families"]["vo2max"]["latest"],
                                                "first_watts": 257, "first_alpha": 0.47}}},
             "selection": _nm}
_rt_mix = W.scaled(W.BY_KEY["ramp_test"], 215, 146, curve={**_CURVE, "selection": _mk},
                   blocks=_blk_lead, ga=_GA_A3)
# TREFFERZUSICHERUNG: beide Enden laufen WIRKLICH ueber Kurve und Bloecke.
eq([((_rt_mix.get("ramp_protocol") or {}).get(k) or {}).get("kind") for k in ("start_source", "end_source")],
   ["ga", "blocks"], "B2b-2 Fixture: Start und Ende laufen nicht ueber Umkehrung und Bloecke")
_herl = " ".join(_rt_mix.get("derivation") or [])
# 0.68.0: der Start kommt aus der Umkehrung - die hat keine Namens/Marken-Auswahl,
# ihre Herkunft ist der Stufentest; die Herleitung nennt die Quelle.
eq(((_rt_mix.get("ramp_protocol") or {}).get("start_source") or {}).get("selection"), None,
   "B2b-2: der Start traegt keine Auswahl mehr (Umkehrung)")
eq(((_rt_mix.get("ramp_protocol") or {}).get("end_source") or {}).get("selection"), _nm,
   "B2b-2: das Ende traegt die Auswahl der Bloecke")
check("Start" in _herl and "Ermüdungskachel" in _herl.split("Ende")[0],
      f"B2b-2: die Herleitung nennt beim Start nicht seine Quelle ({_herl[:120]})")
check("AUS DEN NAMEN" in _herl.split("Ende", 1)[-1],
      "B2b-2: die Herleitung nennt beim Ende nicht seine Auswahl")
# SOURCE_LABEL bleibt der MESSWEG: die Auswahl steht daneben, nicht darin.
check(all("Markierung" not in v and "Namenserkennung" not in v for v in W.SOURCE_LABEL.values()),
      "B2b-2: die Auswahl ist in SOURCE_LABEL gewandert")
# Faellt eine Seite auf die FTP, traegt sie keine Auswahl - die FTP hat keine.
_rt_ftp = W.scaled(W.BY_KEY["ramp_test"], 215, 146)
eq([((_rt_ftp.get("ramp_protocol") or {}).get(k) or {}).get("selection") for k in ("start_source", "end_source")],
   [None, None], "B2b-2: der FTP-Rueckfall behauptet eine Auswahl")

# --- B2c · DIE KACHEL-ERKLAERUNG ----------------------------------------------
# Je Einheit: Zahl, Herkunft, Stufe im Kreislauf, gewertete Einheiten, Rechenweg -
# aus derselben Rechnung. Die Fixture traegt je Quelle beide Auswahlen, und das
# ZAEHLFELD weicht absichtlich von der Listenlaenge ab (sechste Bauregel).
_pts = [{"activity_id": f"a{i}", "date": f"2026-08-0{i}", "name": f"VO2 {i}",
         "median_watts": 250 + i, "median_alpha": 0.40} for i in range(1, 4)]
_b_fam = {**_BLOCKS["families"]["vo2max"], "points": _pts, "sessions": 9}
_bl = lambda marks: {"families": {"vo2max": _b_fam}, "selection": {"from_marks": marks, "label": "SEL-B" if marks else "SEL-N"}}
_cu = lambda marks: {**_CURVE, "selection": {"from_marks": marks, "label": "SEL-KURVE"}, "rides_used": 7,
                     "used": [{"activity_id": "r1", "date": "2026-08-01", "name": "Volumen", "hours_with_value": [1, 2]}]}
_quellen_b2c = {}
# 0.68.0: die Grundlage laeuft ueber "ga" (die Umkehrung, Stufe "marks" - sie
# steht auf den markierten Fahrten und dem Stufentest), nicht mehr ueber "curve".
for _key, _kw in (("vo2_4x4", dict(blocks=_bl(True))), ("vo2_4x4", dict(blocks=_bl(False))),
                  ("z2_60", dict(curve=_cu(True), ga=_GA_A3)), ("recovery_40", dict())):
    _e = W.scaled(W.BY_KEY[_key], 215, 146, **_kw)
    _x = W.explain(_e, 215, _kw.get("curve"), _kw.get("blocks"), _kw.get("ramp"))
    _quellen_b2c[(_e.get("watt_source"), (_kw.get("blocks") or _kw.get("curve") or {}).get("selection", {}).get("from_marks"))] = (_e, _x)
eq(sorted(str(k) for k in _quellen_b2c),
   sorted(str(k) for k in [("blocks", True), ("blocks", False), ("ga", True), ("ftp", None)]),
   "B2c Fixture: nicht jede Quelle und Auswahl wird durchlaufen")
_soll_stufe = {("blocks", True): "marks", ("blocks", False): "alpha", ("ga", True): "marks",
               ("ftp", None): "ftp"}
for _k, (_e, _x) in sorted(_quellen_b2c.items(), key=lambda kv: str(kv[0])):
    _x = _x or {}
    eq(_x.get("stage"), _soll_stufe[_k], f"B2c: Stufe im Kreislauf fuer {_k}")
    eq([c.get("key") for c in _x.get("cycle") or []], ["ftp", "alpha", "marks"],
       f"B2c: der Kreislauf steht nicht in seiner Reihenfolge ({_k})")
    eq([c.get("key") for c in _x.get("cycle") or [] if c.get("here")], [_soll_stufe[_k]],
       f"B2c: genau EINE Stufe traegt hier ({_k})")
    check(bool(_x.get("origin")) and bool(_x.get("steps")), f"B2c: Herkunft oder Rechenweg fehlen ({_k})")
    check("%" not in " ".join(_x.get("steps") or []) or _k[0] == "ftp",
          f"B2c: ein gemessener Rechenweg rechnet in Prozent ({_k})")
_eb, _xb = _quellen_b2c[("blocks", True)]
eq((_xb or {}).get("units_count"), 9, "B2c: gewertete Einheiten kommen aus dem Zaehlfeld, nicht aus der Liste")
eq([u.get("activity_id") for u in (_xb or {}).get("units") or []], ["a3", "a2", "a1"],
   "B2c: die Einheiten stehen nicht neuestes zuerst")
check(f"Vorgabe {(_eb.get('block_source') or {}).get('watts')} W" in " ".join((_xb or {}).get("steps") or []),
      "B2c: der Rechenweg nennt nicht die Vorgabe der Einheit")
check(f"± {W.BLOCK_HR_WINDOW_SD_FACTOR:g} ×" in " ".join((_xb or {}).get("steps") or []),
      "B2c: der Pulsfenster-Faktor kommt nicht aus der Konstante")
check("SEL-B" in (_xb or {}).get("origin", "") and "SEL-N" in ((_quellen_b2c[("blocks", False)][1]) or {}).get("origin", ""),
      "B2c: die Herkunft nennt ihre Auswahl nicht")
eq(((_xb or {}).get("headline") or {}).get("watts"), (_eb.get("block_source") or {}).get("watts"),
   "B2c: die Kopfzahl ist nicht die Vorgabe der Einheit")
_ec, _xc = _quellen_b2c[("ga", True)]
eq((_xc or {}).get("units_count"), 18, "B2c GA: Einheiten = Fahrten der gelesenen Stunde")
check(f"Ziel {(_ec.get('ga_blocks') or [{}])[0].get('target')} W" in " ".join((_xc or {}).get("steps") or [])
      and f"Grenze {(_ec.get('ga_blocks') or [{}])[0].get('limit')} W" in " ".join((_xc or {}).get("steps") or []),
      "B2c GA: der Rechenweg nennt Ziel und Grenze nicht")
_ef, _xf = _quellen_b2c[("ftp", None)]
eq((_xf or {}).get("units_count"), 0, "B2c FTP: keine gewerteten Einheiten")
check("FTP 215 W" in " ".join((_xf or {}).get("steps") or []), "B2c FTP: der Rechenweg nennt die FTP nicht")
eq(W.explain(W.scaled(W.BY_KEY["ramp_test"], 215, 146), 215, None, None, None), None,
   "B2c: der Stufentest bekommt keine zweite Herleitung")
eq(W.explain(W.BY_KEY["vo2_4x4"], 215, None, None, None), None,
   "B2c: ein ungerechneter Katalogeintrag wird erklaert")
for _wort in ("zu locker", "Fehler", "Mangel", "leider", "nicht ausreich"):
    check(all(_wort not in t + x for _, t, x in W.CYCLE), f"B2c: gesperrtes Wort im Kreislauf ({_wort})")


# --- S4 · EINE Wattzahl je Karte (F3.3): text_w folgt blocks_w, auch gestreckt --
# Karte 3, F3.3 / Sollzustand S4: `rate_sessions` ueberschrieb text_w bei einer
# gestreckten Wocheneinheit mit steps_text(stretched, ftp) - also FTP x Prozent -,
# waehrend blocks_w die Kurve trug (S3: 130 gegen 134 W auf einer Karte). Rot an
# 0.67.1: Treffer faellt, Gegenprobe (ungestreckt) ist gruen.
_curveS4 = {"measured": [{"hour": 1, "t": 0.5, "watts": 150.0, "n": 12}, {"hour": 2, "t": 1.5, "watts": 145.0, "n": 10}],
            "paired": [{"from_hour": 1, "to_hour": 2, "delta": -6.0, "n": 8, "enough": True}],
            "literature": [{"hour": 2, "t": 1.5, "watts": 146.0}, {"hour": None, "t": 3.0, "watts": 138.0}],
            "plan": [{"hours": 1, "watts": 150.0}, {"hours": 2, "watts": 144.0}]}
_gestreckt = W.rate_sessions([{"workout": "z2_150", "hours": 4.0}], "ready", ftp=200, aerobic_hr=140, ga=_GA_A3)[0]
_ungestreckt = W.rate_sessions([{"workout": "z2_150", "hours": 2.5}], "ready", ftp=200, aerobic_hr=140, ga=_GA_A3)[0]
check(_gestreckt.get("stretched") is True, "S4 Fixture: die Einheit ist gestreckt")
check(any(b[1] != round(200 * pct / 100) for b, (_, pct, *_r) in zip(_gestreckt["blocks_w"], _gestreckt["blocks"])),
      "S4 Fixture: blocks_w traegt die Umkehrung, nicht die FTP")
eq(_gestreckt["text_w"], W.watts_text(_gestreckt["blocks_w"]), "S4 Treffer: text_w der gestreckten Karte ist die Wattliste von blocks_w")
eq(_ungestreckt["text_w"], W.watts_text(_ungestreckt["blocks_w"]), "S4 Gegenprobe: ungestreckt war es schon so")
check(sum(b[0] for b in _gestreckt["blocks_w"]) == _gestreckt["minutes"], "S4 Eigenschaft: die gestreckten Minuten stehen in blocks_w")


# --- S3 · WAHL 2 MIT SCHRANKE (24.09.) -> 0.68.0: die Ablesestelle lebt in ga_at
# (oben geprueft: volle Stunden, belegt ab 3 Fahrten, sonst die letzte gut
# belegte, keine Studienform). Die Rundung bleibt benannt:
eq(getattr(W, "CURVE_HOUR_MIN_RIDES", None), 3, "S3 Schranke: benannte Konstante, drei Fahrten")
eq([W.planned_hour(m) for m in (30, 60, 95, 150, 210, 330, 360)], [1, 1, 1, 2, 3, 5, 6], "S3 Rundung: nur volle Stunden, mindestens eine")

# --- 0.68.0 · scaled() liest die GA-Ziele der Umkehrung -------------------------
_GA = {"mid": 90.6, "limit_alpha": 1.0, "target_alpha": 1.3, "missing": None,
       "hours": [{"hours": h, "n": n, "load_w": w, "alpha": a, "limit_w": l, "target_w": t} for h, n, w, a, l, t in
                 [(1, 18, 139.6, 1.336, 170.0, 142.9), (2, 13, 139.6, 1.259, 163.1, 135.9),
                  (3, 4, 139.8, 1.107, 149.5, 122.3), (4, 3, 138.7, 1.078, 145.8, 118.6), (5, 1, 146.8, 0.834, 131.8, 104.6)]]}
def _ga_card(key, ga=_GA, minutes=None):
    e = W.BY_KEY[key]
    if minutes:
        e = {**e, "blocks": W.stretch_blocks(e, minutes / 60) or e["blocks"], "minutes": minutes}
    return W.scaled(e, 200, 140, ga=ga)
for key, minutes, want in (("z2_60", None, (1, 143, 170)), ("z2_90", None, (1, 143, 170)), ("z2_150", None, (2, 136, 163)),
                           ("z2_210_late", None, (3, 122, 150)), ("z2_150", 330, (4, 119, 146)), ("z2_150", 360, (4, 119, 146))):
    c = _ga_card(key, minutes=minutes); g = (c.get("ga_blocks") or [{}])[0]
    eq((g.get("hour"), g.get("target"), g.get("limit")), want, f"GA {key} {minutes or ''}: Stunde / Ziel / Grenze")
    eq(c.get("watt_source"), "ga", f"GA {key}: Quelle")
    check(all(b[1] == want[1] for b in c["blocks_w"] if str(b[2]).startswith("gleich")), f"GA {key}: der Hauptteil traegt das Ziel")
_ohne_ziel = W.scaled(W.BY_KEY["z2_60"], 200, 140, ga={**_GA, "target_alpha": None, "hours": [{**h, "target_w": None} for h in _GA["hours"]]})
g0 = (_ohne_ziel.get("ga_blocks") or [{}])[0]
eq((g0.get("target"), g0.get("limit")), (None, 170), "GA ohne Ziel: nur die Grenze")
check(all(b[1] == 170 for b in _ohne_ziel["blocks_w"] if str(b[2]).startswith("gleich")), "GA ohne Ziel: der Hauptteil traegt die Grenze")
_kein = W.scaled(W.BY_KEY["z2_60"], 200, 140, ga={**_GA, "hours": [], "missing": "kein Stufentest"})
eq(_kein.get("watt_source"), "ftp", "GA ohne Stufentest: Rueckfall auf die FTP")
check(_kein.get("ga_missing") == "kein Stufentest", "GA ohne Stufentest: der Grund steht an der Karte")
# 0.68.0 · AB 3 H UNGEPRUEFT: die Abnahmefahrt (3 h bei ~122 W) steht aus, also
# traegt jede Einheit ab drei geplanten Stunden das Feld `unverified` - der
# Rechner setzt es, nicht die Karte. Unter 3 h fehlt es. Die Schwelle ist eine
# benannte Konstante.
eq(getattr(W, "GA_UNVERIFIED_FROM_HOUR", None), 3, "GA ungeprueft: benannte Schwelle, drei Stunden")
for key, minutes, want in (("z2_60", None, False), ("z2_150", None, False), ("z2_150", 170, False),
                           ("z2_210_late", None, True), ("z2_150", 330, True)):
    g = (_ga_card(key, minutes=minutes).get("ga_blocks") or [{}])[0]
    eq(bool(g.get("unverified")), want, f"GA ungeprueft {key} {minutes or ''}: Feld")
# Gegenprobe: eine 3-h-Einheit, die mangels Belegung auf Stunde 2 zurueckfaellt,
# bleibt trotzdem ungeprueft - gefahren werden drei Stunden, nicht zwei.
_duenn3 = {**_GA, "hours": [h if h["hours"] < 3 else {**h, "n": 1} for h in _GA["hours"]]}
_g3 = (_ga_card("z2_210_late", ga=_duenn3).get("ga_blocks") or [{}])[0]
eq((_g3.get("hour"), bool(_g3.get("unverified"))), (2, True), "GA ungeprueft: Rueckfall auf Stunde 2 bei 3 h geplant")
check("curve_share" not in _ga_card("z2_60") and all(b[1] != round(0.9 * 170) for b in _ga_card("z2_60")["blocks_w"]), "GA: die 0,90 ist weg")

print(f"test_workouts: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
sys.exit(1 if FAILURES else 0)
