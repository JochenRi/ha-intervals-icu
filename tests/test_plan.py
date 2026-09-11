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
for days, expect in ((2, 1), (3, 1), (4, 2), (5, 2), (6, 2), (7, 3)):
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

# --- 3  the long day grows, but only in loading weeks -------------------------
longs = [w["long_day_hours"] for w in built["weeks"]]
check(longs[1] > longs[0], f"3 langer Tag wächst nicht ({longs})")
rec_index = kinds.index("recovery")
check(longs[rec_index] < longs[rec_index - 1],
      f"3 Entlastungswoche verkürzt den langen Tag nicht ({longs})")
check(max(longs) <= 6.5 + 0.01, f"3 langer Tag übersteigt das Ziel ({max(longs)})")
# Each step is a growth convention, not a leap. Compared LOADING week against
# LOADING week: the recovery week deliberately shortens the long day, so the
# step back out of it is not a jump in the progression.
load_longs = [longs[i] for i, kind in enumerate(kinds) if kind == "load"]
steps = [round(load_longs[i + 1] / load_longs[i], 2)
         for i in range(len(load_longs) - 1) if load_longs[i]]
check(all(s <= 1.2 for s in steps), f"3 Sprung im langen Tag zu groß ({steps})")
check(any(s > 1.0 for s in steps), f"3 langer Tag wächst über die Belastungswochen nicht ({steps})")

# --- 4  a week that cannot carry the goal has to SAY so -----------------------
tight = P.plan(profile(goal="long_ride", target_hours=6.5, days_per_week=4,
                       hours_per_week=8, longest_day_hours=3.5), weeks=8, today=TODAY)
note = tight["budget_note"]
check(note is not None, "4 zu knappes Zeitbudget nicht gemeldet")
check(note["kind"] == "too_little_time", "4 falsche Art der Meldung")
check(note["reachable_long_day"] < 6.5, "4 erreichbare Dauer nicht genannt")
check(note["needed_hours"] > 8, "4 benötigte Wochenzeit nicht genannt")
# ... and the printed long day must never exceed what the week can carry
for week in tight["weeks"]:
    check(week["long_day_hours"] <= week["hours"] * P.LONG_DAY_SHARE + 0.05,
          f"4 langer Tag ({week['long_day_hours']}) über dem Wochenbudget ({week['hours']})")
check(any(w["long_day_capped"] for w in tight["weeks"]), "4 Deckelung nicht markiert")
# with enough hours, no warning and the target is reached
roomy = P.plan(profile(goal="long_ride", target_hours=6.5, days_per_week=5,
                       hours_per_week=13, longest_day_hours=3.5), weeks=14, today=TODAY)
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

print(f"test_plan: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
sys.exit(1 if FAILURES else 0)
