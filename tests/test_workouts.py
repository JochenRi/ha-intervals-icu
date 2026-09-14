"""Sessions: the right one for the state, and a payload Intervals can parse.

Two things can go badly wrong here. A hard session recommended on the wrong
day is a training error. A malformed payload silently puts a broken workout
on the calendar, which is worse than none. Both are checked below.
"""

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
_entry_src = _ramp_src[_ramp_src.index("RAMP_TEST = {"):_ramp_src.index("LIBRARY.append(RAMP_TEST)")]
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
          "solid_until_hour": 2, "thin_until_hour": 2}

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
for _fam, _first, _key in (("vo2max", "blocks", "vo2_4x4"),
                           ("endurance", "curve", "z2_90"),
                           ("tempo", "ramp_hrvt2", "tempo_2x20")):
    _entry = W.BY_KEY[_key]
    _alles = W.scaled(_entry, 215, 146, curve=_CURVE, blocks=_BLOCKS, ramp=_RAMP)
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

# --- 3 · DER GLEICHSTAND AUS 0.47.1 GILT WEITER ------------------------------
# Watt- und Pulsseite derselben Einheit kommen aus DERSELBEN Quelle. Der
# Stufentest als zweite Stufe darf das nicht aufbrechen.
_ramp_only = W.scaled(W.BY_KEY["vo2_4x4"], 215, 146, ramp=_RAMP)
eq(_ramp_only.get("watt_source"), "ramp_hrvt2", "N2: der Test greift gar nicht")
eq((_ramp_only.get("hr_source") or {}).get("kind"), "ramp_hrvt2",
   "N2 Gleichstand: die Wattseite kommt aus dem Test, die Pulsseite nicht")
check(_ramp_only.get("hr_window") is None,
      "N2 Gleichstand: neben dem gemessenen Punkt steht zusaetzlich ein "
      "Fenster aus der aeroben Schwelle — zwei Quellen in einer Karte")
eq((_ramp_only or {}).get("hr_point"), 171,
   "N2 Gleichstand: der Puls kommt nicht aus demselben Messpunkt wie die Watt")
# Und die Gegenprobe: OHNE Puls am Messpunkt faellt AUCH die Wattseite zurueck.
_kein_puls = {"date": "2026-09-14",
              "result": {"hrvt2": {"alpha": 0.5, "watts": 248.0, "hr": None}}}
_halb = W.scaled(W.BY_KEY["vo2_4x4"], 215, 146, ramp=_kein_puls)
eq(_halb.get("watt_source"), "ftp",
   "N2 Gleichstand: die Wattseite nimmt den Test, obwohl die Pulsseite dort "
   "nichts hergibt — genau der Fehler aus 0.47.1")
check(_halb.get("hr_window") is not None,
   "N2 Gleichstand: nach dem Rueckfall fehlt auch das gewohnte HF-Fenster")

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
# Gegenprobe, gezaehlt und benannt: mit einem GEFUELLTEN Test aendert sich
# sehr wohl etwas - sonst prueft der Abschnitt oben nur, dass nie etwas
# passiert.
check(W.scaled(W.BY_KEY["vo2_4x4"], 215, 146).get("blocks_w")
      != W.scaled(W.BY_KEY["vo2_4x4"], 215, 146, ramp=_RAMP).get("blocks_w"),
      "N2 Leerzustand Gegenprobe: auch ein gefuellter Test aendert nichts — "
      "die Pruefung ist blind")

# --- 5 · DIE MESSUNG IST NICHT IMMER DIE VORGABE -----------------------------
# An der zweiten Schwelle ist die gemessene Leistung dieselbe Groesse wie die
# Leitzahl und wird direkt uebernommen. An der ERSTEN ist sie eine Schwelle -
# gefahren wird derselbe Anteil davon wie bei der Kurve, eine Regel und nicht
# zwei.
eq((_ramp_only.get("ramp_source") or {}).get("share"), 1.0,
   "N2: an der zweiten Schwelle wird ein Anteil abgezogen")
_lang = W.scaled(W.BY_KEY["z2_90"], 215, 146, ramp=_RAMP)
eq((_lang.get("ramp_source") or {}).get("share"), W.CURVE_TARGET_SHARE,
   "N2: an der ersten Schwelle wird NICHT derselbe Anteil benutzt wie bei der "
   "Kurve — zwei Regeln fuer dieselbe Groesse")
check(max(b[1] for b in _lang["blocks_w"] if b[1]) < 196,
      "N2: die Grundlageneinheit sitzt AUF der gemessenen Schwelle statt "
      "darunter")

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
}

erste = W.curve_watts(CURVE, 0.5)
eq((erste["watts"], erste["source"]), (153, "measured"), "Stunde 1 kommt aus der Messung")
eq(erste["n"], 11, "und traegt ihre Belegung")
zweite = W.curve_watts(CURVE, 1.5)
eq(zweite["watts"], 142, "Stunde 2 folgt der GEPAARTEN Reihe (-11), nicht der ungepaarten (-15)")
eq(zweite["source"], "measured", "auch sie ist Messung")
spaet = W.curve_watts(CURVE, 3.5)
eq(spaet["source"], "literature", "jenseits des Gemessenen: Studienform")
eq(spaet["n"], None, "und ohne Belegung, weil es keine gibt")
check(spaet["watts"] < zweite["watts"], "die Studienform faellt weiter")

# --- 0.47.1: DIE MESSUNG IST NICHT DIE VORGABE -------------------------------
# Die Kurve liefert die SCHWELLE. Wer dort faehrt, faehrt an der Schwelle und
# nicht darunter - und die Wattseite widerspraeche der Pulsseite DERSELBEN
# Karte. Gefahren wird ein Anteil, aus denselben Studien wie die Kurvenform.
from const import CURVE_TARGET_SHARE  # noqa: E402

grund = W.scaled(W.BY_KEY["z2_60"], 200, 160, 185, CURVE)
haupt_w = [b for b in grund["blocks_w"] if len(b) > 3 and b[3]][0][1]
eq(haupt_w, round(153 * CURVE_TARGET_SHARE), "die Vorgabe ist ein Anteil der Schwelle")
eq(grund["curve_blocks"][0]["threshold"], 153.0,
   "die gemessene Schwelle reist getrennt mit")
eq(grund["curve_share"], CURVE_TARGET_SHARE, "der Anteil reist in der Payload")
check(haupt_w < 153, "die Vorgabe sitzt auf der Schwelle statt darunter")

# DIE GEGENPROBE, DIE IN 0.47.0 GEFEHLT HAT: Watt- und Pulsseite derselben
# Einheit muessen denselben relativen Abstand zu IHRER Schwelle haben. Genau
# ihr Auseinanderlaufen war der Fehler - Puls bei 88-97 %, Watt bei 100 %.
for key in ("z2_60", "z2_90", "z2_150", "z2_210_late"):
    entry = W.BY_KEY[key]
    lo, hi = entry["hr_hint"]
    check(lo <= CURVE_TARGET_SHARE <= hi,
          f"{key}: der Wattanteil {CURVE_TARGET_SHARE} liegt ausserhalb des "
          f"HF-Fensters {lo}-{hi} - beide Seiten meinen verschiedene Intensitaeten")
# und die Gegenprobe zur Gegenprobe: die Schwelle SELBST faellt durch
_lo, _hi = W.BY_KEY["z2_60"]["hr_hint"]
check(not (_lo <= 1.0 <= _hi),
      "Gegenprobe: ein Anteil von 100 % waere im HF-Fenster - die Pruefung ist blind")

# --- 0.49.0: Watt UND Puls aus DERSELBEN Quelle ------------------------------
BLK = {"families": {"vo2max": {
    "source_ok": True, "sessions": 15, "from": "2026-06-03", "to": "2026-09-01",
    "min_for_source": 3,
    "latest": {"date": "2026-09-01", "median_alpha": 0.405, "n_blocks": 4, "median_watts": 250},
    "hr_window": {"low": 171, "high": 186, "median": 178.5, "sd": 3.6, "n": 15,
                  "source": "measured"}}}}
vo = W.scaled(W.BY_KEY["vo2_4x4"], 200, 160, 195, None, BLK)
eq(vo["watt_source"], "blocks", "VO2max: die Watt kommen aus der Blockmessung")
eq([b[1] for b in vo["blocks_w"] if b[1] == 250].__len__(), 4, "alle vier Bloecke tragen die Messung")
eq(vo["hr_window"], (171, 186), "und das Pulsfenster ebenfalls")
eq(vo["hr_source"]["source"], "measured", "die Herkunft des Fensters reist mit")
eq(vo["block_source"]["date"], "2026-09-01", "die Einheit, aus der die Zahl stammt")

# DER GLEICHSTANDSTEST, umgeschrieben: er prueft die QUELLE, nicht zwei
# verschiedene Bezugsgroessen. Bis 0.48.1 verglich er den Wattanteil mit dem
# HF-Faktor - bei den harten Familien sind das Aepfel und Birnen, weil die
# Watt aus der Messung und der Puls aus der aeroben Schwelle kaemen.
check(vo.get("watt_source") == "blocks" and vo.get("hr_source", {}).get("source") == "measured",
      "Gleichstand: Watt gemessen, Puls aber nicht - die Seiten laufen auseinander")
# GEGENPROBE, GEZAEHLT UND BENANNT: faellt eine Seite auf die FTP zurueck,
# muss die andere mitfallen. Ein halb umgestelltes Paar waere genau der Fehler.
duenn = {"families": {"vo2max": {**BLK["families"]["vo2max"], "source_ok": False}}}
zurueck = W.scaled(W.BY_KEY["vo2_4x4"], 200, 160, 195, None, duenn)
eq(zurueck["watt_source"], "ftp", "zu duenn belegt: die Watt fallen auf die FTP zurueck")
check("hr_source" not in zurueck,
      "Gleichstand: die Watt fielen zurueck, das Pulsfenster blieb gemessen")
check(zurueck.get("hr_window") != (171, 186),
      "Gleichstand: das gemessene Fenster steht noch, obwohl die Watt zurueckfielen")
# Und ohne jede Messung bleibt alles wie bisher.
ohne = W.scaled(W.BY_KEY["vo2_4x4"], 200, 160, 195, None, None)
eq(ohne["watt_source"], "ftp", "ohne Blockmessung: unveraendert FTP")

# Gegenprobe, GEZAEHLT UND BENANNT: traegt der gepaarte Schritt nicht, wird er
# NICHT verwendet - sonst staffelte die Vorgabe auf einer Zahl, die die Kachel
# selbst nicht zeigen darf.
duenn = {**CURVE, "paired": [{**CURVE["paired"][0], "n": 3, "enough": False}]}
# Traegt der gepaarte Schritt nicht, wird NICHT auf ihm gestaffelt - die
# Vorgabe faellt dann auf die Studienform mit Kennzeichnung, nicht auf eine
# Zahl, die die Kachel selbst nicht zeigen darf.
eq(W.curve_watts(duenn, 1.5)["source"], "literature",
   "zu wenige Paare: es wird trotzdem gestaffelt")
eq(W.curve_watts(duenn, 0.5)["watts"], 153, "die erste Stunde bleibt Messung")
eq(W.curve_watts(None, 1.5), None, "ohne Kurve gibt es keine Vorgabe daraus")

# Und am Katalog: die Grundlage bekommt Kurvenwatt, die harten Familien nicht.
lang = W.scaled(W.BY_KEY["z2_150"], 215, 160, 185, CURVE)
eq(lang["watt_source"], "curve", "lange Fahrt: Vorgabe aus der Kurve")
haupt = [b for b in lang["blocks_w"] if len(b) > 3 and b[3]]
eq(haupt[0][1], round(142 * CURVE_TARGET_SHARE),
   "der gleichmaessige Hauptteil traegt den Anteil des Kurvenwerts")
eq(lang["blocks_w"][0][1], round(215 * 55 / 100), "Ein- und Ausrollen bleiben Prozent der FTP")
sweet = W.scaled(W.BY_KEY["sweetspot_2x20"], 215, 160, 185, CURVE)
eq(sweet["watt_source"], "ftp", "SweetSpot bleibt bei der FTP - dort traegt der Fit nicht")
eq(sweet["blocks_w"][1][1], round(215 * 90 / 100), "und behaelt seine Blockleistung")
# Ohne Kurve faellt die Grundlage sichtbar auf die FTP zurueck.
eq(W.scaled(W.BY_KEY["z2_150"], 215, 160, 185, None)["watt_source"], "ftp", "ohne Kurve: Rueckfall auf die FTP")
# Die Herkunft reist je Abschnitt mit - sonst stuende in der Karte eine Zahl
# ohne Auskunft, woher sie kommt.
eq(sorted({b["source"] for b in lang["curve_blocks"]}), ["measured"], "jeder Kurven-Abschnitt nennt seine Herkunft")

print(f"test_workouts: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
sys.exit(1 if FAILURES else 0)
