"""Turning a goal into weeks.

The coach was paused for a reason: it recommended sessions without knowing
what they were for. This module is the missing half - the athlete's goal, the
time they actually have, and the constraints they cannot move - and the logic
that turns those into a block structure and a week.

What the literature actually supports, and where it stops:

  DURABILITY   Maunder's definition: the time of onset and magnitude of
               deterioration in physiological characteristics during prolonged
               exercise. It is a quality of its own - WorldTour riders beat
               ProTeam riders not on fresh power but on how much they keep
               late in a race - and it is trainable. For a six-hour goal it is
               THE target, not FTP.
  HOW          Long rides near but below the aerobic threshold build the fat
               oxidation and fatigue resistance behind it; from roughly six to
               eight weeks out, quality work placed LATE in a long ride trains
               the specific thing the goal asks for. Fuel it properly: the
               stimulus should be fatigue from effort, not from running empty.
  BIG DAY      Long-distance practice (audax/randonneur progression): the
               weekly rides stay ordinary, and a SINGLE big day every few
               weeks does the growing - by roughly 10-15% per step, only in
               loading weeks. That rhythm is a convention from practice, not
               a trial result, and it is named as such wherever it appears.
               The old version planned the long ride as a fixed share of
               every week (0.6) - which mathematically forbade any ride
               longer than 60% of the weekly budget and produced eight
               identical capped weeks. A six-hour ride out of a 5.5-hour
               week is normal audax practice; a 60%-per-week rule calls it
               impossible.
  BLOCKS       Block periodization does NOT beat traditional periodization.
               Twelve weeks, trained cyclists, load-matched: no difference in
               time-trial performance. Its real advantage is practical - one
               stimulus per block simplifies planning and lets training fit
               the weeks life actually leaves.
  LOADING      3:1 or 2:1 - progressive weeks then a recovery week at roughly
               60-70% of the volume. The cycle counts CALENDAR weeks from a
               persisted start date: a plan that restarts "from today" on
               every view keeps the recovery week forever four weeks away.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any

# The routine weekly long ride: steady, roughly half the week. It does not
# grow - growing is the big day's job. This share bounds only the ROUTINE
# ride; the big day deliberately lives outside it.
ROUTINE_LONG_SHARE = 0.5

# How the big day grows per step, and only in loading weeks. 10-15% is the
# convention long-distance practice uses; 1.12 sits in the middle. A
# convention, not a finding.
BIG_DAY_STEP = 1.12

GOALS: dict[str, dict[str, Any]] = {
    "long_ride": {
        "label": "Lange Fahrten durchstehen",
        "detail": "Sechs Stunden und mehr, ohne im letzten Drittel einzubrechen.",
        "target": "Durability — Ermüdungswiderstand",
        "why": (
            "Das ist eine eigene Eigenschaft, nicht einfach viel Grundlage. Maunder "
            "definiert sie als Zeitpunkt und Ausmaß der Verschlechterung physiologischer "
            "Merkmale während langer Belastung. Profifahrer schlagen ihre Konkurrenz "
            "nicht über die frische Leistung, sondern darüber, wie viel davon nach "
            "Stunden noch übrig ist."
        ),
        "mix": {"long": 1, "endurance": 2, "quality": 1},
        "key_session": "der große Tag — er wächst alle paar Wochen, alles andere stützt ihn",
    },
    "ftp": {
        "label": "Schwellenleistung heben",
        "detail": "Mehr Watt über eine Stunde.",
        "target": "FTP",
        "why": "Klassische Schwellenarbeit plus SweetSpot, getragen von aerober Grundlage.",
        "mix": {"long": 0, "endurance": 2, "quality": 2},
        "key_session": "die Schwellen- oder SweetSpot-Einheit",
    },
    "vo2max": {
        "label": "Spitzenleistung heben",
        "detail": "Die Pyramide oben breiter machen.",
        "target": "VO2max",
        "why": (
            "Kurze harte Intervalle. Rønnestads 30/15 brachte über zehn Wochen gegen "
            "aufwandsgleiche 4×5 min signifikant größere Zuwächse."
        ),
        "mix": {"long": 0, "endurance": 2, "quality": 2},
        "key_session": "die VO2max-Einheit",
    },
    "health": {
        "label": "Fit bleiben",
        "detail": "Kein Wettkampf, kein Aufbau — Form halten.",
        "target": "Erhalt",
        "why": "Gleichmäßige Grundlage mit gelegentlichem Reiz reicht dafür aus.",
        "mix": {"long": 0, "endurance": 3, "quality": 1},
        "key_session": "die regelmäßige Grundlageneinheit",
    },
}

PHASES = (
    ("base", "Grundlage", "Umfang und aerobe Basis. Der große Tag wächst, hart wird wenig gefahren."),
    ("build", "Aufbau", "Der Rhythmus bleibt, dazu kommt Qualität — erst getrennt, später hinein."),
    ("specific", "Spezifisch", "Qualität wandert ans Ende der langen Fahrt: genau das, was das Ziel verlangt."),
    ("taper", "Anspitzen", "Umfang runter, Intensität bleibt. Die Form kommt aus der Erholung."),
)


def default_goal() -> dict[str, Any]:
    return {
        "goal": None, "target_hours": None, "target_date": None,
        "days_per_week": None, "hours_per_week": None, "longest_day_hours": None,
        "hard_days": [], "long_day": None, "indoor_only": False, "notes": "",
        # The Monday the plan is counted from. Persisted with the profile so
        # the 3:1 cycle is anchored to CALENDAR weeks - without it the plan
        # restarts on every view and the recovery week never arrives.
        "plan_start": None,
    }


def _phase_for(weeks_left: int | None, goal: str) -> tuple[str, str, str]:
    """Which phase this week belongs to, counting back from the target."""
    if weeks_left is None:
        return PHASES[0] if goal == "long_ride" else PHASES[1]
    if weeks_left <= 1:
        return PHASES[3]
    if weeks_left <= 7:
        return PHASES[2]
    if weeks_left <= 16:
        return PHASES[1]
    return PHASES[0]


def _week_kind(index: int, pattern: int) -> str:
    """3:1 or 2:1 - the last week of each cycle is the recovery week."""
    return "recovery" if (index + 1) % (pattern + 1) == 0 else "load"


def _h(value: float) -> str:
    """A German decimal comma for user-facing hour figures."""
    return f"{value:.1f}".replace(".", ",")


def _monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def anchor_stamp(today: date | str | None = None) -> str:
    """The Monday a plan is counted from, as ISO text.

    ONE place decides which Monday. set_goal used to compute it inline and the
    migration below would have been a second copy of the same rule - the error
    class that cost 0.11.0 and 0.27.0 a release each.
    """
    day = date.fromisoformat(today) if isinstance(today, str) else (today or date.today())
    return _monday(day).isoformat()


def has_anchor(profile: Any) -> bool:
    """True when the profile carries a calendar anchor that actually parses."""
    if not isinstance(profile, dict):
        return False
    try:
        date.fromisoformat(str(profile.get("plan_start") or ""))
    except ValueError:
        return False
    return True


def migrate_goal(profile: Any, today: date | str | None = None) -> dict[str, Any] | None:
    """Bring a stored goal record up to the current shape.

    Returns the repaired record, or None when nothing had to change.

    Why this exists: the archive fills in keys added by later versions at the
    TOP level only, so a goal profile written before 0.33.0 keeps its old shape
    forever - no `plan_start`. The plan then falls back to the Monday of the
    current week, which is stable within the week and moves every Monday, so
    the 3:1 recovery week stays four weeks away for good. Nothing tells the
    athlete; the only cure was re-saving the goal by chance.

    A record without a goal is left alone: stamping an anchor onto an empty
    profile would invent a plan start for someone who never set a goal.
    """
    if not isinstance(profile, dict) or not profile.get("goal"):
        return None
    merged = {**default_goal(), **profile}
    if not has_anchor(merged):
        # Missing, empty or unparsable - all three leave the plan drifting, so
        # all three get today's Monday, the same rule set_goal applies.
        merged["plan_start"] = anchor_stamp(today)
    return merged if merged != profile else None


def plan(profile: dict[str, Any], state: dict[str, Any] | None = None,
         weeks: int = 8, today: str | None = None) -> dict[str, Any]:
    """Build the coming weeks from the goal, the available time and the state.

    `state` carries what the archive already knows: the longest ride so far,
    the current weekly load, the measured durability. Without it the plan
    still stands, it just cannot say how big a step the big day is.
    """
    goal_key = profile.get("goal")
    goal = GOALS.get(goal_key or "")
    if not goal:
        return {"ready": False, "missing": ["goal"]}

    # Two questions, not seven. Everything else is already in the archive:
    # how many hours this athlete actually rides, how long their longest ride
    # was. Asking for numbers the data already holds is how forms get abandoned.
    if not profile.get("days_per_week"):
        return {"ready": False, "missing": ["days_per_week"], "goal": goal_key}

    days = int(profile["days_per_week"])
    hours = float(profile.get("hours_per_week")
                  or (state or {}).get("typical_hours") or days * 1.6)
    longest_now = float(profile.get("longest_day_hours")
                        or (state or {}).get("longest_ride_hours") or 0)
    # The default target is the GOAL, not an extrapolation. "Lange Fahrten
    # durchstehen" says six hours and more in its own description - so six
    # hours it is, or the athlete's own longest ride where that is already
    # beyond six. The old default (longest x 1.6) turned a 5.5-hour rider
    # into a nine-hour target with a demoralising budget note attached.
    target_hours = float(profile.get("target_hours") or 0)
    if goal_key == "long_ride" and not target_hours:
        target_hours = max(6.0, math.ceil(longest_now * 2) / 2)
    pattern = 3 if days >= 4 else 2

    # How many hard sessions a week - the one number that actually follows
    # from the day count, and it has to say what the note next to it says.
    # 80/20 counts SESSIONS, not minutes: up to four riding days that is ONE
    # hard session (the old code said two at four days - half the sessions
    # hard, against its own text). Two hard sessions is the standard for
    # 8-14 hour amateur weeks, and even World Tour riders at 25+ hours
    # rarely exceed three. The caveat travels with it: 80/20 is a useful
    # description, not a universal weekly prescription, and a 2023 review
    # found no evidence that one distribution model always wins.
    hard_per_week = 1 if days <= 4 else 2 if days <= 6 else 3
    if goal_key == "long_ride":
        hard_per_week = min(hard_per_week, 2)

    start = date.fromisoformat(today) if today else date.today()
    weeks_left = None
    if profile.get("target_date"):
        try:
            weeks_left = max(0, (date.fromisoformat(profile["target_date"]) - start).days // 7)
        except ValueError:
            weeks_left = None

    # The calendar anchor. Weeks are counted from the Monday of the persisted
    # plan start, not from "today": a plan that restarts on every view keeps
    # the recovery week forever four weeks away. Without a stored start the
    # anchor falls back to the current Monday - stable within the week, and
    # set_goal persists it on the next save.
    week_start = _monday(start)
    anchor = week_start
    if profile.get("plan_start"):
        try:
            stored = _monday(date.fromisoformat(str(profile["plan_start"])))
            if stored <= week_start:
                anchor = stored
        except ValueError:
            pass
    weeks_since = (week_start - anchor).days // 7

    # The two long-ride volumes. The ROUTINE long ride is steady - roughly
    # half the week, never growing. The BIG day starts at the longest ride
    # the archive knows and grows by BIG_DAY_STEP once per cycle, in the last
    # loading week before the recovery week (every 3 weeks at 2:1, every 4 at
    # 3:1 - inside the 2-4 week rhythm of long-distance practice), capped at
    # the target. It is allowed to exceed the weekly budget: that week is
    # simply a bigger week, marked as the exception it is.
    routine_long = min(longest_now or hours * 0.45,
                       max(1.5, hours * ROUTINE_LONG_SHARE))
    routine_long = round(routine_long, 1)
    big_level = round(max(longest_now, routine_long) or max(2.0, hours * 0.45), 1)

    out_weeks: list[dict[str, Any]] = []
    for index in range(weeks):
        abs_index = weeks_since + index
        kind = _week_kind(abs_index, pattern)
        left = None if weeks_left is None else max(0, weeks_left - index)
        phase_key, phase_label, phase_note = _phase_for(left, goal_key)

        big_week = (goal_key == "long_ride" and kind == "load"
                    and abs_index % (pattern + 1) == pattern - 1
                    and phase_key != "taper")
        if big_week:
            big_level = round(min(target_hours or big_level * BIG_DAY_STEP,
                                  big_level * BIG_DAY_STEP), 1)

        week_hours = hours * (0.65 if kind == "recovery" else 1.0)
        if phase_key == "taper":
            week_hours *= 0.7

        hours_long = None
        if goal_key == "long_ride":
            if big_week:
                hours_long = big_level
                if big_level > routine_long:
                    # the exception is added openly: the big-day week IS a
                    # bigger week, it does not pretend to fit the usual budget
                    week_hours = week_hours - routine_long + big_level
            elif kind == "recovery":
                # the long day stays in the rhythm, but shorter - shortened
                # BEFORE the remaining hours are dealt out
                hours_long = round(routine_long * 0.7, 1)
            else:
                hours_long = round(min(routine_long, week_hours), 1)

        sessions = _sessions(goal, goal_key, days, week_hours, hours_long, kind,
                             phase_key, big_week, pattern + 1, hard_per_week)
        out_weeks.append({
            "index": index + 1,
            "start": (week_start + timedelta(days=7 * index)).isoformat(),
            "kind": kind,
            "phase": phase_key, "phase_label": phase_label, "phase_note": phase_note,
            "weeks_left": left,
            "hours": round(week_hours, 1),
            "long_day_hours": hours_long,
            "big_day": big_week,
            "sessions": sessions,
        })

    gap = None
    if goal_key == "long_ride" and target_hours and longest_now:
        gap = round(target_hours - longest_now, 1)

    # The arithmetic the athlete needs before anything else. The old note
    # demanded target/0.6 weekly hours ("you need 15 hours a week") because
    # the long ride was a fixed weekly share. With the big day as a single
    # exception every few weeks, the honest statement is different: the
    # target does not have to fit the week - it has to fit ONE week per
    # cycle, and that week runs larger. Said openly, with the numbers.
    budget_note = None
    if goal_key == "long_ride" and target_hours and target_hours > hours * 0.6:
        cycle = pattern + 1
        big_week_hours = round(hours - routine_long + target_hours, 1)
        budget_note = {
            "kind": "big_day_exception",
            "target_hours": round(target_hours, 1),
            "typical_hours": round(hours, 1),
            "cycle_weeks": cycle,
            "big_week_hours": big_week_hours,
            "text": (
                f"Die {_h(target_hours)}-Stunden-Fahrt passt nicht als fester Anteil in "
                f"eine {_h(hours)}-Stunden-Woche — sie ist auch nicht so geplant. Sie ist "
                f"der einzelne große Tag: alle {cycle} Wochen einer, der um rund 12 % "
                f"wächst, während die Wochen dazwischen normal bleiben. Die Woche des "
                f"großen Tages läuft dann auf bis zu {_h(big_week_hours)} Stunden — als "
                "bewusste Ausnahme, danach kommt die Entlastungswoche. So bauen "
                "Langstreckenfahrer lange Distanzen auch mit kleinen Wochenbudgets auf "
                "(Audax-Praxis — eine Konvention, kein Studienergebnis)."
            ),
        }

    return {
        "ready": True,
        "goal": goal_key, "goal_label": goal["label"], "target": goal["target"],
        "why": goal["why"], "key_session": goal["key_session"],
        "pattern": f"{pattern}:1",
        "hard_per_week": hard_per_week,
        "hard_note": (
            f"{hard_per_week} harte Einheit{'en' if hard_per_week != 1 else ''} pro Woche. "
            "Die 80/20-Verteilung zählt Einheiten, nicht Minuten: bis vier Fahrtage ist "
            "das eine harte, die übrigen locker. Zwei harte Einheiten sind der Standard "
            "für Wochen von 8 bis 14 Stunden, und selbst WorldTour-Fahrer mit 25 Stunden "
            "gehen selten über drei. Einschränkung: 80/20 ist eine nützliche Beschreibung, "
            "keine allgemeine Wochenvorschrift — ein Review von 2023 fand nur sieben "
            "geeignete Studien und keinen Beleg, dass ein Verteilungsmodell immer gewinnt."
        ),
        "hours_source": ("angegeben" if profile.get("hours_per_week")
                         else "aus deinen letzten Wochen gerechnet"),
        "pattern_note": (
            f"{pattern} Belastungswochen, dann eine Entlastungswoche mit rund einem "
            "Drittel weniger Umfang — fest an Kalenderwochen verankert, damit sie auch "
            "kommt. Ob die Wochen in Blöcken oder gemischt liegen, ändert nachweislich "
            "nichts am Ergebnis — lastgleich verglichen fanden zwölf Wochen bei "
            "trainierten Radfahrern keinen Unterschied. Blöcke haben einen anderen "
            "Vorteil: ein Reiz je Block macht die Planung einfach und lässt sie sich an "
            "die Wochen anpassen, die das Leben übrig lässt."
        ),
        "longest_now": round(longest_now, 1) or None,
        "target_hours": target_hours or None,
        "gap_hours": gap,
        "weeks_left": weeks_left,
        "anchor": anchor.isoformat(),
        "weeks_since_start": weeks_since,
        "weeks": out_weeks,
        "budget_note": budget_note,
        "caveat": (
            "Der große Tag alle paar Wochen mit rund 12 % Zuwachs je Schritt ist eine "
            "verbreitete Konvention aus der Langstreckenpraxis, kein Studienergebnis. "
            "Die Wochen sind ein Vorschlag auf Basis deiner Angaben — die "
            "Zustandserkennung aus HRV und Ruhepuls hat am Tag selbst Vorrang: ein "
            "Einbruch schlägt jeden Plan."
        ),
    }


def _sessions(goal: dict[str, Any], goal_key: str, days: int, week_hours: float,
              hours_long: float | None, kind: str, phase: str,
              big_week: bool = False, cycle: int = 4,
              hard_per_week: int = 2) -> list[dict[str, Any]]:
    """The sessions of one week, fitted into the days AND the hours available.

    The arithmetic contract: the hours of the sessions returned here never
    exceed week_hours (plus rounding). An earlier version broke it twice in
    one function - a 1.0 h floor inflated small weeks, and the recovery-week
    shortening of the long day happened AFTER the rest had already been
    dealt out. The long ride's hours now arrive RESOLVED from the caller
    (routine, big day, or recovery-shortened), so there is exactly one place
    that decides them.
    """
    sessions: list[dict[str, Any]] = []
    remaining_hours = week_hours
    slots = days

    if goal_key == "long_ride" and slots > 0 and hours_long:
        recovery_week = kind == "recovery"
        late_quality = phase in ("specific",) and kind == "load"
        if big_week:
            title = f"Großer Tag — {_h(hours_long)} h"
            workout = "z2_210_late" if late_quality else "z2_150"
            detail = (
                f"Der große Tag — die Ausnahme, die wächst: alle {cycle} Wochen rund "
                "12 % länger, dazwischen bleibt der lange Tag gewöhnlich. Gleichmäßig "
                "knapp unter der aeroben Schwelle. "
                + ("Die letzten 30–40 Minuten mit 2×10 min zügig — Qualität im "
                   "ermüdeten Zustand ist genau das, was das Ziel verlangt."
                   if late_quality else
                   "Noch ohne harte Anteile; erst geht es um die Dauer.")
            )
        else:
            title = (f"Langer Tag (verkürzt) — {_h(hours_long)} h" if recovery_week
                     else f"Langer Tag — {_h(hours_long)} h")
            workout = "z2_90"
            detail = (
                "Entlastungswoche: der lange Tag bleibt im Rhythmus, aber kürzer. "
                "Der Zuwachs macht hier Pause."
                if recovery_week else
                "Der wöchentliche lange Tag bleibt gleich — gewachsen wird am großen "
                "Tag alle paar Wochen, nicht hier. Gleichmäßig knapp unter der "
                "aeroben Schwelle."
                + ("" if not late_quality else
                   " Die letzten 20–30 Minuten dürfen zügig sein.")
            )
        sessions.append({
            "role": "long",
            "title": title,
            "workout": workout,
            "detail": detail,
            "why": (
                "Ab etwa sechs bis acht Wochen vor dem Ziel gehört harte Arbeit ans ENDE "
                "der langen Fahrt, nicht an den Anfang — ein frischer Intervallblock "
                "trainiert nicht, was im letzten Drittel gebraucht wird."
                if late_quality else
                "Lange Einheiten nahe unter der aeroben Schwelle bauen Fettoxidation und "
                "Ermüdungswiderstand — die Grundlagen der Durability. Der Rhythmus des "
                "großen Tages (alle 2–4 Wochen ein Schritt) ist Langstreckenpraxis, "
                "keine Studie."
            ),
            "fuel": ("Durchgehend essen und trinken. Der Reiz soll aus der Belastung kommen, "
                     "nicht aus leeren Speichern — das ist der häufigste Fehler bei langen "
                     "Einheiten."),
            "hours": round(hours_long, 1),
        })
        remaining_hours = max(0.0, remaining_hours - hours_long)
        slots -= 1

    quality_slots = 0 if kind == "recovery" else min(
        hard_per_week, max(0, slots - 1) if goal_key == "long_ride" else slots)
    if phase == "taper":
        quality_slots = min(1, quality_slots)
    # a quality session needs its 1.2 h to exist - a week too small to carry
    # one gets none instead of hours the budget does not hold
    quality_slots = min(quality_slots, int(remaining_hours // 1.2))

    for number in range(quality_slots):
        # Where a week carries a second quality session it VARIES - two
        # copies of the same protocol in one week are one stimulus twice,
        # not two sessions (threshold progression: frequency first, then
        # duration, intensity last).
        if goal_key == "vo2max":
            workout, title = ("vo2_3015", "VO2max — 30/15") if number == 0 else ("vo2_4x8", "VO2max — 4×8 min")
        elif goal_key == "ftp":
            workout, title = ("threshold_3x12", "Schwelle 3×12") if number == 0 else ("sweetspot_2x20", "SweetSpot 2×20")
        elif goal_key == "long_ride":
            workout, title = (("sweetspot_2x20", "SweetSpot 2×20") if number == 0
                              else ("tempo_2x20", "Tempo 2×20"))
        else:
            workout, title = ("tempo_2x20", "Tempo 2×20")
        sessions.append({
            "role": "quality", "title": title, "workout": workout,
            "detail": "Die harte Einheit der Woche — nur an einem Tag mit grünem Zustand.",
            "why": ("Hält die Schwelle oben, während der Umfang wächst. Beim Ziel lange "
                    "Fahrten ist sie Beiwerk, nicht Hauptsache."
                    if goal_key == "long_ride" else goal["why"]),
            "hours": 1.2,
        })
        remaining_hours = max(0.0, remaining_hours - 1.2)
        slots -= 1

    # base rides fill what is left. Under 45 minutes a ride is movement, not
    # a stimulus (the catalogue says so itself) - such a slot is dropped, not
    # padded up to a fantasy hour.
    while slots > 0:
        hours_each = remaining_hours / slots
        if hours_each < 0.75 and slots > 1:
            slots -= 1
            continue
        if hours_each < 0.5:
            break
        hours_each = round(hours_each, 1)
        sessions.append({
            "role": "endurance",
            "title": f"Grundlage — {_h(hours_each)} h",
            "workout": "z2_60" if hours_each < 1.4 else "z2_90",
            "detail": "Gleichmäßig, DFA über 0,75. Kein Reiz, sondern Substanz.",
            "why": "Der Anteil, der im Dreizonenmodell 75–80 % der Einheiten ausmacht.",
            "hours": hours_each,
        })
        remaining_hours = max(0.0, remaining_hours - hours_each)
        slots -= 1

    return sessions
