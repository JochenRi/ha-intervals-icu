"""Sessions: the right one for the state, and a payload Intervals can parse.

Two things can go badly wrong here. A hard session recommended on the wrong
day is a training error. A malformed payload silently puts a broken workout
on the calendar, which is worse than none. Both are checked below.
"""

import re
import sys
from pathlib import Path

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
check("Autors" in long_day["stretch_note"],
      "streckung: die Angabe wird nicht als Autorenangabe beschriftet")
check("gemessene" in long_day["stretch_note"],
      "streckung: der Hinweis grenzt nicht gegen eine Messung ab")
# the step list follows the stretched sections, not the template's own text
check("225m" in (long_day["text_w"] or ""), "streckung: die Schrittliste zeigt weiter die Vorlage")
check("80m" not in (long_day["text_w"] or ""), "streckung: die alte Dauer steht noch in der Schrittliste")

quality = W.rate_sessions([{"title": "SweetSpot", "workout": "sweetspot_2x20", "hours": 1.2}],
                          "ready", budget=400, ftp=215)[0]
check(quality["stretched"] is False, "streckung: eine Intervalleinheit wurde gestreckt")
eq(quality["minutes"], 70, "streckung: die Vorlage wurde verändert")
eq(quality["template_minutes"], 70, "streckung: die ungestreckte Einheit meldet zwei Dauern")
check("kein" in quality["stretch_note"], "streckung: der Festfall wird nicht begründet")
eq(quality["elastic_sections"], [], "streckung: eine Intervalleinheit meldet dehnbare Abschnitte")

# the load does NOT come from the stretched block list - it stays the linear
# scaling of the catalogue load, one place (Befund 3 aus Paket I)
eq(long_day["load"], W.session_load(W.BY_KEY["z2_90"], 4.0),
   "streckung: die Last wird jetzt aus den Blöcken gerechnet — zweiter Rechenweg")

print(f"test_workouts: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
sys.exit(1 if FAILURES else 0)
