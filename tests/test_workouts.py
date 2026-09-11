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

# --- 2  the picker respects the state -----------------------------------------
easy = {"recovery_40", "return_45", "z2_60", "z2_90"}

slump = W.suggest("slump", ftp=215, aerobic_hr=157)
check(all(entry["key"] in easy for entry in slump),
      f"2 Einbruch: harte Einheit empfohlen ({[e['key'] for e in slump]})")
check(all(entry["intensity"] <= 60 for entry in slump), "2 Einbruch: zu intensiv")

recovering = W.suggest("recovering", ftp=215, aerobic_hr=157)
check(all(entry["intensity"] < 70 for entry in recovering), "2 noch im Einbruch: zu intensiv")

ready = W.suggest("ready", ftp=215, aerobic_hr=157)
check(any(entry["intensity"] >= 85 for entry in ready), "2 Normalbereich: kein harter Reiz angeboten")
# Without a goal the ladder starts at the entry dose, not at the hardest
# protocol: the recommended progression is 4x4 first, 5x4 after two weeks,
# 30/15 only for well-trained riders.
eq(ready[0]["key"], "vo2_4x4", "2 Normalbereich: nicht die Einstiegsdosis zuerst")
check(len(ready) == 5, f"2 Normalbereich: {len(ready)} Vorschläge statt fünf")
keys_ready = [e["key"] for e in ready]
check("vo2_3015" in keys_ready or "vo2_5x4" in keys_ready,
      "2 Normalbereich: keine Steigerung im Angebot")
# the goal reorders without emptying the shelf
long_goal = [e["key"] for e in W.suggest("ready", ftp=215, goal="long_ride")]
check(long_goal[0].startswith("z2"), f"2 Langfahrt-Ziel: harte Einheit zuerst ({long_goal})")
check(any(k.startswith("vo2") for k in long_goal),
      "2 Langfahrt-Ziel: harte Einheit ganz verschwunden")
ftp_goal = [e["key"] for e in W.suggest("ready", ftp=215, goal="ftp")]
check(ftp_goal[0].startswith("threshold"), f"2 FTP-Ziel: keine Schwellenarbeit zuerst ({ftp_goal})")

# --- 3  a break overrides the state ------------------------------------------
after_break = W.suggest("ready", ftp=215, aerobic_hr=157, layoff_days=7)
check(all(entry["intensity"] < 70 for entry in after_break),
      f"3 nach Pause: harte Einheit trotz Pause ({[e['key'] for e in after_break]})")
eq(after_break[0]["key"], "return_45", "3 nach Pause: kein Wiedereinstieg zuerst")
# ... but a slump still wins over the break ladder
check(all(entry["key"] in easy for entry in W.suggest("slump", layoff_days=7)),
      "3 Einbruch plus Pause: Einbruch wird überstimmt")

# --- 4  two hard days in a week block a third --------------------------------
capped = W.suggest("ready", ftp=215, aerobic_hr=157, hard_days_last_7=2)
check(all(entry["intensity"] < 80 for entry in capped),
      f"4 zwei harte Tage: dritter angeboten ({[(e['key'], e['intensity']) for e in capped]})")
check(capped, "4 zwei harte Tage: gar nichts mehr angeboten")

# --- 5  the athlete's own numbers ---------------------------------------------
scaled = W.suggest("ready", ftp=215, aerobic_hr=157)[0]
check("blocks_w" in scaled, "5 keine Wattzahlen trotz FTP")
first_block = scaled["blocks_w"][0]
eq(first_block[1], round(215 * scaled["blocks"][0][1] / 100), "5 Watt falsch gerechnet")
check(scaled["hr_window"][0] < scaled["hr_window"][1], "5 Pulsfenster verdreht")
check(scaled["hr_window"][0] > 157, "5 Pulsfenster einer harten Einheit unter der Schwelle")
bare = W.suggest("ready")[0]
check("blocks_w" not in bare, "5 Wattzahlen ohne FTP erfunden")
check(bare.get("hr_window") is None, "5 Pulsfenster ohne Anker erfunden")

# --- 6  budget is marked, not hidden ------------------------------------------
tight = W.suggest("ready", ftp=215, aerobic_hr=157, budget=50)
check(any(entry["fits_budget"] is False for entry in tight), "6 Budget: Überschreitung nicht markiert")
check(len(tight) >= 2, "6 Budget: Vorschläge werden weggefiltert statt markiert")
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
    check(all(entry["intensity"] < 85 for entry in picks), f"9 {state}: harter Reiz geraten")

print(f"test_workouts: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
sys.exit(1 if FAILURES else 0)
