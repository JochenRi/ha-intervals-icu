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
check("z2_90" not in keys_break, "3 nach Pause: lange Grundlage statt Wiedereinstieg")
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

print(f"test_workouts: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
sys.exit(1 if FAILURES else 0)
