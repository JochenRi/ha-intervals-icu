"""Plans: the goal has to survive the constraints.

Two failure modes matter here. A plan that promises a six-hour ride out of an
eight-hour week is a lie the athlete only discovers after weeks of following
it. And a plan that keeps loading without a recovery week is a plan that ends
in a hole. Both are checked.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"))

import plan as P  # noqa: E402

FAILURES: list[str] = []
CHECKS = 0


def check(condition: bool, label: str) -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILURES.append(label)


def eq(got, want, label: str) -> None:
    check(got == want, f"{label}: {got!r} statt {want!r}")


def profile(**kwargs):
    base = P.default_goal()
    base.update(kwargs)
    return base


TODAY = "2026-09-12"

# --- 1  nothing is invented without the answers -------------------------------
eq(P.plan({})["ready"], False, "1 leeres Profil ergibt einen Plan")
eq(P.plan({})["missing"], ["goal"], "1 fehlendes Ziel nicht benannt")
# Only ONE thing must be asked: the days. Hours and the longest ride are in
# the archive, and a target duration defaults to a round number above what the
# athlete already manages - every field not asked is a field not got wrong.
partial = P.plan(profile(goal="long_ride"))
eq(partial["ready"], False, "1 Plan ohne Tagesangabe")
eq(partial["missing"], ["days_per_week"], "1 mehr als die Tagesangabe verlangt")
from_data = P.plan(profile(goal="long_ride", days_per_week=4),
                   {"typical_hours": 8.5, "longest_ride_hours": 3.5}, weeks=4, today=TODAY)
eq(from_data["ready"], True, "1 Plan trotz Archivdaten verweigert")
check(from_data["weeks"][0]["hours"] > 7, "1 Wochenstunden nicht aus dem Archiv übernommen")
check(from_data["target_hours"] and from_data["target_hours"] > 3.5,
      "1 kein Ziel aus dem bisher Erreichten abgeleitet")
eq(from_data["hours_source"], "aus deinen letzten Wochen gerechnet", "1 Herkunft der Stunden unklar")

# the number of hard sessions follows from the days - 80/20 counts SESSIONS
# up to FOUR days it is ONE hard session - the code has to say what its own
# note says (0.32.x said two at four days: half the sessions hard)
for days, expect in ((2, 1), (3, 1), (4, 1), (5, 2), (6, 2), (7, 3)):
    result = P.plan(profile(goal="ftp", days_per_week=days), {"typical_hours": 9},
                    weeks=2, today=TODAY)
    got = result["hard_per_week"]
    check(got == expect or (days >= 7 and got >= 2),
          f"1 {days} Tage ergeben {got} harte Einheiten statt {expect}")
    hard = [s for s in result["weeks"][0]["sessions"] if s["role"] == "quality"]
    check(len(hard) <= got, f"1 {days} Tage: mehr harte Einheiten geplant als vorgesehen")
check("zählt Einheiten, nicht Minuten" in from_data["hard_note"], "1 80/20-Regel nicht erklärt")
check("keinen Beleg" in from_data["hard_note"], "1 Einschränkung der 80/20-Regel fehlt")
# for a goal that needs no target duration, that field must NOT be demanded
ftp_partial = P.plan(profile(goal="ftp", days_per_week=4, hours_per_week=8))
eq(ftp_partial["ready"], True, "1 FTP-Ziel verlangt eine Zieldauer")

full = profile(goal="long_ride", target_hours=6.5, days_per_week=4,
               hours_per_week=11, longest_day_hours=3.5, target_date="2027-05-01")
built = P.plan(full, {"longest_ride_hours": 3.5}, weeks=12, today=TODAY)
eq(built["ready"], True, "1 vollständiges Profil ergibt keinen Plan")

# --- 2  the loading pattern -----------------------------------------------------
kinds = [w["kind"] for w in built["weeks"]]
eq(kinds[:4], ["load", "load", "load", "recovery"], "2 Muster 3:1 nicht eingehalten")
check(kinds.count("recovery") == 3, f"2 zu wenige Entlastungswochen ({kinds})")
rec = next(w for w in built["weeks"] if w["kind"] == "recovery")
load = built["weeks"][0]
check(rec["hours"] < load["hours"] * 0.8,
      f"2 Entlastungswoche kaum leichter ({rec['hours']} vs {load['hours']})")
# fewer available days -> 2:1, because three loading weeks on two days is thin
few = P.plan(profile(goal="long_ride", target_hours=5, days_per_week=3,
                     hours_per_week=6, longest_day_hours=2.5), weeks=6, today=TODAY)
eq(few["pattern"], "2:1", "2 Muster bei wenigen Tagen nicht angepasst")

# --- 3  the PROGRESSION contract: the big day grows, the routine week does not
# The long-distance rhythm: one big day per cycle (the last loading week
# before recovery) that grows ~12% per step and is capped at the target;
# the routine weekly long ride stays put, the recovery week shortens it.
longs = [w["long_day_hours"] for w in built["weeks"]]
bigs = [w["long_day_hours"] for w in built["weeks"] if w["big_day"]]
check(len(bigs) >= 2, f"3 kein großer Tag je Zyklus geplant ({bigs})")
check(bool(bigs) and (all(b2 > b1 for b1, b2 in zip(bigs, bigs[1:])) or bigs[-1] == 6.5),
      f"3 der große Tag wächst nicht über die Zyklen ({bigs})")
steps = [round(b2 / b1, 2) for b1, b2 in zip(bigs, bigs[1:]) if b1]
check(all(s <= 1.2 for s in steps), f"3 Sprung des großen Tages zu groß ({steps})")
check(max(longs) <= 6.5 + 0.01, f"3 großer Tag übersteigt das Ziel ({max(longs)})")
check(bool(bigs) and bigs[0] > built["longest_now"],
      f"3 erster großer Tag wächst nicht über das bisher Gefahrene ({bigs[:1]})")
rec_index = kinds.index("recovery")
check(longs[rec_index] < longs[0],
      f"3 Entlastungswoche verkürzt den langen Tag nicht ({longs})")
routine = [w["long_day_hours"] for w in built["weeks"]
           if w["kind"] == "load" and not w["big_day"]]
check(len(set(routine)) == 1,
      f"3 der wöchentliche lange Tag soll NICHT wachsen — der große Tag wächst ({routine})")
# the big-day week is openly a bigger week, not a lie about the budget
big_weeks = [w for w in built["weeks"] if w["big_day"]]
for w in big_weeks:
    check(w["hours"] >= w["long_day_hours"],
          f"3 Woche des großen Tages kleiner als der große Tag selbst (W{w['index']})")
# the default target follows the GOAL (six hours and more), not longest x 1.6
default_target = P.plan(profile(goal="long_ride", days_per_week=4),
                        {"typical_hours": 5.5, "longest_ride_hours": 5.5},
                        weeks=8, today=TODAY)
eq(default_target["target_hours"], 6.0,
   "3 Ziel-Default folgt nicht dem Ziel (6 h), sondern einer Hochrechnung")
tall = P.plan(profile(goal="long_ride", days_per_week=4),
              {"typical_hours": 9.0, "longest_ride_hours": 7.2}, weeks=4, today=TODAY)
check(tall["target_hours"] >= 7.2, "3 Ziel-Default unter dem bereits Gefahrenen")

# --- 4  a target beyond the weekly budget is an EXCEPTION, not an impossibility
# The old note demanded target/0.6 weekly hours ("you need 15 hours a week").
# The honest statement: the big day does not have to fit the week - it has to
# fit ONE week per cycle, and that week is openly larger.
# one growth step per CYCLE (not per week) - the horizon has to be long
# enough to see the progression pass the old 60% ceiling
tight = P.plan(profile(goal="long_ride", target_hours=6.5, days_per_week=4,
                       hours_per_week=8, longest_day_hours=3.5), weeks=20, today=TODAY)
note = tight["budget_note"]
check(note is not None, "4 Ausnahme-Mechanik nicht erklärt")
check(note["kind"] == "big_day_exception", "4 falsche Art der Meldung")
check(note["cycle_weeks"] in (3, 4), "4 Zyklus nicht genannt")
check(note["big_week_hours"] > 8, "4 Umfang der Ausnahme-Woche nicht genannt")
check("Ausnahme" in note["text"], "4 der große Tag nicht als Ausnahme erklärt")
check("Konvention" in note["text"], "4 Audax-Rhythmus nicht als Konvention benannt")
check("nicht aufzubauen" not in note["text"],
      "4 die alte Unmöglichkeits-Botschaft steht noch da")
# the plan itself still GROWS toward the target instead of capping at 60%
tight_bigs = [w["long_day_hours"] for w in tight["weeks"] if w["big_day"]]
check(bool(tight_bigs) and tight_bigs[-1] > tight_bigs[0],
      f"4 großer Tag wächst trotz kleinem Wochenbudget nicht ({tight_bigs})")
check(bool(tight_bigs) and max(tight_bigs, default=0) > 8 * 0.6,
      f"4 großer Tag weiter von der alten 60-Prozent-Regel gedeckelt ({tight_bigs})")
# with a big weekly budget the target fits the ordinary rhythm - no note
roomy = P.plan(profile(goal="long_ride", target_hours=6.5, days_per_week=5,
                       hours_per_week=13, longest_day_hours=3.5), weeks=26, today=TODAY)
check(roomy["budget_note"] is None, "4 Warnung trotz ausreichender Zeit")
check(max(w["long_day_hours"] for w in roomy["weeks"]) >= 6.4,
      "4 Ziel trotz ausreichender Zeit nicht erreicht")

# --- 5  quality belongs late in the long ride, but only near the goal ---------
near = P.plan(profile(goal="long_ride", target_hours=6, days_per_week=4, hours_per_week=11,
                      longest_day_hours=5, target_date="2026-10-20"), weeks=4, today=TODAY)
long_sessions = [s for w in near["weeks"] for s in w["sessions"] if s["role"] == "long"]
check(any("letzten" in s["detail"] for s in long_sessions),
      "5 spezifische Phase ohne Qualität im ermüdeten Zustand")
far = P.plan(profile(goal="long_ride", target_hours=6, days_per_week=4, hours_per_week=11,
                     longest_day_hours=3, target_date="2027-08-01"), weeks=4, today=TODAY)
far_long = [s for w in far["weeks"] for s in w["sessions"] if s["role"] == "long"]
check(all("letzten" not in s["detail"] for s in far_long),
      "5 Qualität am Ende der langen Fahrt zu früh im Aufbau")
# fuelling must travel with every long ride - the classic mistake
check(all(s.get("fuel") for s in long_sessions), "5 Verpflegungshinweis fehlt")

# --- 6  the sessions fit the days, and hard days stay countable ---------------
for week in built["weeks"]:
    eq(len(week["sessions"]), 4, f"6 Woche {week['index']} hat nicht vier Einheiten")
    hard = [s for s in week["sessions"] if s["role"] == "quality"]
    check(len(hard) <= 2, f"6 Woche {week['index']}: {len(hard)} harte Einheiten")
    if week["kind"] == "recovery":
        eq(len(hard), 0, f"6 Entlastungswoche {week['index']} enthält Qualität")

# --- 6b  a second quality session VARIES instead of duplicating ---------------
for goal_key in ("long_ride", "ftp", "vo2max"):
    two = P.plan(profile(goal=goal_key, days_per_week=6, hours_per_week=12,
                         target_hours=6.0 if goal_key == "long_ride" else None),
                 {"longest_ride_hours": 4.0}, weeks=3, today=TODAY)
    for week in two["weeks"]:
        hard = [s["workout"] for s in week["sessions"] if s["role"] == "quality"]
        check(len(hard) == len(set(hard)),
              f"6b {goal_key} W{week['index']}: doppelte Qualitätseinheit ({hard})")

# --- 6c  the CALENDAR anchor contract -----------------------------------------
# With a persisted plan_start the recovery week reaches a FIXED date: viewed
# on any day, the week starting 2026-09-28 (abs week 4 of a 3:1 cycle from
# Monday 2026-09-07) is the recovery week. Without the anchor the plan slid
# forward daily and the recovery week never arrived.
anchored = profile(goal="long_ride", target_hours=6.0, days_per_week=4,
                   hours_per_week=10, longest_day_hours=4.0,
                   plan_start="2026-09-07")
kind_by_date = {}
for view_day in ("2026-09-08", "2026-09-12", "2026-09-16", "2026-09-25"):
    viewed = P.plan(anchored, {}, weeks=8, today=view_day)
    eq(viewed["anchor"], "2026-09-07", f"6c Anker verrutscht ({view_day})")
    for week in viewed["weeks"]:
        prior = kind_by_date.get(week["start"])
        check(prior is None or prior == week["kind"],
              f"6c Wochenart für {week['start']} wechselt je nach Blickdatum "
              f"({prior} vs {week['kind']})")
        kind_by_date[week["start"]] = week["kind"]
eq(kind_by_date.get("2026-09-28"), "recovery",
   "6c Entlastungswoche erreicht ihr festes Datum nicht")
# week starts are calendar weeks (Mondays), not "today plus n*7"
from datetime import date as _date
for day_iso, kind in kind_by_date.items():
    check(_date.fromisoformat(day_iso).weekday() == 0,
          f"6c Wochenstart {day_iso} ist kein Montag")
# a plan_start mid-cycle: the FIRST shown week may already be the recovery
# week - that is the point of the anchor
late_view = P.plan(anchored, {}, weeks=4, today="2026-09-29")
eq(late_view["weeks"][0]["kind"], "recovery",
   "6c laufende Entlastungswoche beim Öffnen nicht erkannt")
# an anchor in the future or garbage falls back to the current week
odd = P.plan({**anchored, "plan_start": "kein-datum"}, {}, weeks=2, today=TODAY)
check(odd["ready"], "6c kaputter Anker verhindert den Plan")
future = P.plan({**anchored, "plan_start": "2027-01-04"}, {}, weeks=2, today=TODAY)
eq(future["weeks_since_start"], 0, "6c Anker in der Zukunft nicht abgefangen")

# --- 6d  the live case, end to end --------------------------------------------
# 4 riding days, ~5.5 h typical, longest ride 5.5 h, goal long_ride 6 h+.
# The old plan showed eight identical capped 3.3 h weeks and demanded 15
# weekly hours. Now: routine weeks stay ~5.5 h, ONE hard session, and the
# big day reaches the 6 h target as the marked exception.
live = P.plan(profile(goal="long_ride", days_per_week=4),
              {"typical_hours": 5.5, "longest_ride_hours": 5.5},
              weeks=8, today=TODAY)
check(live["ready"], "6d Livefall ergibt keinen Plan")
eq(live["hard_per_week"], 1, "6d Livefall: mehr als eine harte Einheit")
eq(live["target_hours"], 6.0, "6d Livefall: Ziel nicht 6 h")
live_longs = [w["long_day_hours"] for w in live["weeks"]]
check(len(set(live_longs)) > 1,
      f"6d Livefall: wieder acht identische Wochen ({live_longs})")
check(max(live_longs) >= 6.0, f"6d Livefall: großer Tag erreicht 6 h nicht ({live_longs})")
live_note = live["budget_note"]
check(live_note is not None and live_note["kind"] == "big_day_exception",
      "6d Livefall: Ausnahme-Mechanik nicht erklärt")
check("15" not in (live_note or {}).get("text", ""),
      "6d Livefall: die 15-Stunden-Forderung steht noch da")
for week in live["weeks"]:
    if week["big_day"]:
        check(week["hours"] > 5.5 + 0.05,
              f"6d Livefall: Woche des großen Tages nicht als größere Woche geführt "
              f"(W{week['index']}: {week['hours']} h)")

# --- 7  different goals produce different weeks -------------------------------
vo2 = P.plan(profile(goal="vo2max", days_per_week=4, hours_per_week=8), weeks=4, today=TODAY)
titles = [s["title"] for w in vo2["weeks"] for s in w["sessions"]]
check(any("30/15" in title for title in titles), "7 VO2max-Ziel ohne 30/15")
check(not any(s["role"] == "long" for w in vo2["weeks"] for s in w["sessions"]),
      "7 VO2max-Ziel plant einen langen Tag als Hauptsache")
ftp = P.plan(profile(goal="ftp", days_per_week=4, hours_per_week=8), weeks=4, today=TODAY)
check(any("Schwelle" in s["title"] for w in ftp["weeks"] for s in w["sessions"]),
      "7 FTP-Ziel ohne Schwellenarbeit")
health = P.plan(profile(goal="health", days_per_week=3, hours_per_week=5), weeks=4, today=TODAY)
check(all(s["role"] != "long" for w in health["weeks"] for s in w["sessions"]),
      "7 Erhaltungsziel mit langem Tag")

# --- 8  every claim carries its source and its limit --------------------------
check("kein Studienergebnis" in built["caveat"], "8 Wachstumsregel nicht als Konvention benannt")
check("Einbruch schlägt jeden Plan" in built["caveat"], "8 Vorrang des Zustands nicht benannt")
check("keinen Unterschied" in built["pattern_note"],
      "8 Blockperiodisierung fälschlich als überlegen dargestellt")
check("Maunder" in P.GOALS["long_ride"]["why"], "8 Durability ohne Quelle")
check("Rønnestad" in P.GOALS["vo2max"]["why"], "8 VO2max ohne Quelle")

# --- 9  degenerate input must not crash ---------------------------------------
for bad in ({"goal": "quatsch"}, profile(goal="long_ride", days_per_week=0, hours_per_week=0),
            profile(goal="long_ride", target_hours=6, days_per_week=1, hours_per_week=2,
                    longest_day_hours=0), profile(goal="ftp", days_per_week=7, hours_per_week=25)):
    result = P.plan(bad, weeks=6, today=TODAY)
    check(isinstance(result, dict), "9 kein Ergebnis")
    if result.get("ready"):
        for week in result["weeks"]:
            check(week["sessions"], "9 Woche ohne Einheiten")
            check(all(s["hours"] > 0 for s in week["sessions"]), "9 Einheit ohne Dauer")
bad_date = P.plan(profile(goal="long_ride", target_hours=6, days_per_week=4,
                          hours_per_week=11, target_date="kein-datum"), weeks=4, today=TODAY)
check(bad_date["ready"], "9 kaputtes Datum verhindert den Plan")
check(bad_date["weeks_left"] is None, "9 kaputtes Datum ergibt Wochenzahl")

# --- the hours contract: sessions never exceed the week ----------------------
# 0.31.0 dealt 4.5 h of sessions into a 3.6 h recovery week: a 1.0 h floor
# inflated small weeks, and the recovery shortening of the long day happened
# after the rest was already distributed. The contract now: for every week of
# every plan, the session hours sum to at most the week's hours - including
# the exact live case (4 days, 5.5 h typical, 5.5 h longest ride).
for label, profile, state in (
    ("livefall", {"goal": "long_ride", "days_per_week": 4},
     {"typical_hours": 5.5, "longest_ride_hours": 5.5}),
    ("kleine woche", {"goal": "long_ride", "days_per_week": 3},
     {"typical_hours": 3.0, "longest_ride_hours": 2.0}),
    ("grosse woche", {"goal": "long_ride", "days_per_week": 6, "hours_per_week": 14,
                      "target_hours": 6.0}, {"longest_ride_hours": 4.0}),
    ("ftp", {"goal": "ftp", "days_per_week": 4, "hours_per_week": 7}, {}),
    ("health", {"goal": "health", "days_per_week": 3}, {"typical_hours": 4.0}),
):
    out = P.plan(profile, state, weeks=8, today="2026-09-11")
    check(out["ready"], f"stunden {label}: Plan nicht bereit")
    for week in out["weeks"]:
        total = sum(s["hours"] for s in week["sessions"])
        check(total <= week["hours"] + 0.05,
              f"stunden {label} W{week['index']} ({week['kind']}): "
              f"{total:.1f} h Einheiten in {week['hours']:.1f} h Budget")
        for s in week["sessions"]:
            check(s["hours"] >= 0.5,
                  f"stunden {label} W{week['index']}: Einheit unter 30 min ({s['hours']} h)")


# --- 10  the calendar anchor survives an old archive --------------------------
# Records written before 0.33.0 carry no plan_start, and the archive fills in
# missing keys at the TOP level only - so the anchor never appeared, the plan
# fell back to "Monday of this week", and the 3:1 recovery week stayed four
# weeks away for good. Nothing told the athlete. migrate_goal repairs the
# record when the archive is loaded.
LEGACY = {"goal": "long_ride", "target_hours": None, "target_date": None,
          "days_per_week": 4, "hours_per_week": None, "longest_day_hours": None,
          "hard_days": [], "long_day": None, "indoor_only": False, "notes": ""}
SAT = "2026-09-12"      # a Saturday; its Monday is the 7th
NEXT = "2026-09-21"     # the Monday nine days later

fixed = P.migrate_goal(LEGACY, SAT)
# An abort here would skip every check below it and still print "0 Fehler" -
# the very defect this release removes. So the failure is counted, not raised.
check(isinstance(fixed, dict), "10 Altprofil: Migration liefert kein Profil")
fixed = fixed if isinstance(fixed, dict) else {}
eq(fixed.get("plan_start"), "2026-09-07", "10 Altprofil: Anker nicht auf den Montag gestempelt")
eq(fixed.get("days_per_week"), 4, "10 Altprofil: Antwort beim Migrieren verloren")
eq(LEGACY.get("plan_start"), None, "10 Migration schreibt ins übergebene Profil zurück")

# nothing to repair, nothing returned - the archive must not save on every load
eq(P.migrate_goal(fixed, SAT), None, "10 gestempeltes Profil wird erneut migriert")
eq(P.migrate_goal({**LEGACY, "plan_start": "2026-08-31"}, SAT), None,
   "10 fremder gültiger Anker wird überschrieben")

# no goal, no anchor: stamping an empty profile invents a plan start
eq(P.migrate_goal({}, SAT), None, "10 leeres Profil bekommt einen Anker")
eq(P.migrate_goal({"goal": None, "days_per_week": 4}, SAT), None,
   "10 Profil ohne Ziel bekommt einen Anker")
eq(P.migrate_goal(None, SAT), None, "10 None ergibt ein Profil")
eq(P.migrate_goal("kein profil", SAT), None, "10 Text ergibt ein Profil")

# a broken anchor drifts exactly like a missing one, so it is replaced
eq((P.migrate_goal({**LEGACY, "plan_start": "kein-datum"}, SAT) or {}).get("plan_start"),
   "2026-09-07", "10 kaputter Anker bleibt kaputt")
eq((P.migrate_goal({**LEGACY, "plan_start": ""}, SAT) or {}).get("plan_start"),
   "2026-09-07", "10 leerer Anker bleibt leer")

# keys the record does not know yet are filled, unknown ones survive
eq((P.migrate_goal({"goal": "ftp", "extra": 7}, SAT) or {}).get("extra"), 7,
   "10 Migration wirft unbekannte Felder weg")
check("indoor_only" in (P.migrate_goal({"goal": "ftp"}, SAT) or {}),
      "10 Migration füllt neue Schlüssel nicht auf")

# one rule for which Monday - anchor_stamp is the only place that decides
eq(P.anchor_stamp("2026-09-07"), "2026-09-07", "10 Montag verschoben")
eq(P.anchor_stamp("2026-09-13"), "2026-09-07", "10 Sonntag auf den falschen Montag")
eq(P.anchor_stamp("2026-09-14"), "2026-09-14", "10 neuer Montag nicht erkannt")
check(P.has_anchor({"plan_start": "2026-09-07"}), "10 gültiger Anker nicht erkannt")
check(not P.has_anchor({"plan_start": "kein-datum"}), "10 kaputter Anker gilt als gültig")
check(not P.has_anchor({}), "10 fehlender Anker gilt als gültig")
check(not P.has_anchor(None), "10 None gilt als Anker")

# the symptom itself: with the anchor the recovery week stops moving, without
# it the plan restarts every Monday. The second check keeps this test honest -
# if the drift ever disappears on its own, the migration is being duplicated
# somewhere and this file has to say so.
STATE = {"typical_hours": 5.5, "longest_ride_hours": 5.5}
kept = {P.plan(fixed, STATE, weeks=8, today=day).get("anchor") for day in (SAT, NEXT)}
eq(len(kept), 1, f"10 migrierter Anker wandert trotzdem: {sorted(kept)}")
drift = {P.plan(LEGACY, STATE, weeks=8, today=day).get("anchor") for day in (SAT, NEXT)}
eq(len(drift), 2, "10 Gegenprobe: Altprofil wandert nicht mehr - der Test ist stumpf")
eq(P.plan(fixed, STATE, weeks=8, today=NEXT).get("weeks_since_start"), 2,
   "10 Wochen seit Planstart falsch gezählt")

print(f"test_plan: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
sys.exit(1 if FAILURES else 0)
