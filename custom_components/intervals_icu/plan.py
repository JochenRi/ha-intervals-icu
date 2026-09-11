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
  BLOCKS       Block periodization does NOT beat traditional periodization.
               Twelve weeks, trained cyclists, load-matched: no difference in
               time-trial performance. Its real advantage is practical - one
               stimulus per block simplifies planning and lets training fit
               the weeks life actually leaves.
  LOADING      3:1 or 2:1 - progressive weeks then a recovery week at roughly
               60-70% of the volume.
  PROGRESSION  The long ride grows by about 10-15% per step, and only in the
               loading weeks. That is a convention, not a finding; it is named
               as such wherever it appears.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

# A long ride may take at most this share of the week. Beyond that there is no
# week left to recover in, and the rest of the training disappears.
LONG_DAY_SHARE = 0.6

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
        "key_session": "der lange Tag — er wächst, alles andere stützt ihn",
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
    ("base", "Grundlage", "Umfang und aerobe Basis. Der lange Tag wächst, hart wird wenig gefahren."),
    ("build", "Aufbau", "Der lange Tag bleibt, dazu kommt Qualität — erst getrennt, später hinein."),
    ("specific", "Spezifisch", "Qualität wandert ans Ende des langen Tages: genau das, was das Ziel verlangt."),
    ("taper", "Anspitzen", "Umfang runter, Intensität bleibt. Die Form kommt aus der Erholung."),
)


def default_goal() -> dict[str, Any]:
    return {
        "goal": None, "target_hours": None, "target_date": None,
        "days_per_week": None, "hours_per_week": None, "longest_day_hours": None,
        "hard_days": [], "long_day": None, "indoor_only": False, "notes": "",
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


def plan(profile: dict[str, Any], state: dict[str, Any] | None = None,
         weeks: int = 8, today: str | None = None) -> dict[str, Any]:
    """Build the coming weeks from the goal, the available time and the state.

    `state` carries what the archive already knows: the longest ride so far,
    the current weekly load, the measured durability. Without it the plan
    still stands, it just cannot say how big a step the long day is.
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
    # For the long-ride goal, the target defaults to the round number above
    # what they already manage - a goal they can change, not a form field.
    target_hours = float(profile.get("target_hours") or 0)
    if goal_key == "long_ride" and not target_hours:
        target_hours = max(4.0, round(longest_now * 1.6 * 2) / 2)
    pattern = 3 if days >= 4 else 2

    # How many hard sessions a week - the one number that actually follows from
    # the day count. 80/20 counts SESSIONS, not minutes: at five riding days,
    # four easy and one hard. Two hard sessions is the standard for 8-14 hour
    # amateur weeks, and even World Tour riders at 25+ hours rarely exceed
    # three. The caveat travels with it: 80/20 is a useful description, not a
    # universal weekly prescription, and a 2023 review found no evidence that
    # one distribution model always wins.
    hard_per_week = 1 if days <= 3 else 2 if days <= 6 else 3
    if goal_key == "long_ride":
        hard_per_week = min(hard_per_week, 1 if days <= 3 else 2)

    start = date.fromisoformat(today) if today else date.today()
    weeks_left = None
    if profile.get("target_date"):
        try:
            weeks_left = max(0, (date.fromisoformat(profile["target_date"]) - start).days // 7)
        except ValueError:
            weeks_left = None

    # how the long day grows: about 10-15% per loading week, capped at the goal
    step = 1.12
    long_day = longest_now or max(2.0, hours * 0.45)
    out_weeks: list[dict[str, Any]] = []
    for index in range(weeks):
        kind = _week_kind(index, pattern)
        left = None if weeks_left is None else max(0, weeks_left - index)
        phase_key, phase_label, phase_note = _phase_for(left, goal_key)

        if kind == "load" and goal_key == "long_ride" and phase_key != "taper":
            long_day = min(target_hours or long_day * step, long_day * step)
        week_hours = hours * (0.65 if kind == "recovery" else 1.0)
        if phase_key == "taper":
            week_hours *= 0.7
        # A long day cannot eat the whole week. If the weekly budget will not
        # carry the target ride, the plan says so instead of printing a number
        # it then quietly fails to deliver.
        ceiling = week_hours * LONG_DAY_SHARE
        capped = goal_key == "long_ride" and long_day > ceiling + 0.05

        sessions = _sessions(goal, goal_key, days, week_hours, long_day, kind, phase_key,
                             profile, target_hours, hard_per_week)
        out_weeks.append({
            "index": index + 1,
            "start": (start + timedelta(days=7 * index)).isoformat(),
            "kind": kind,
            "phase": phase_key, "phase_label": phase_label, "phase_note": phase_note,
            "weeks_left": left,
            "hours": round(week_hours, 1),
            "long_day_hours": round(min(long_day, ceiling), 1) if goal_key == "long_ride" else None,
            "long_day_capped": capped,
            "sessions": sessions,
        })

    gap = None
    if goal_key == "long_ride" and target_hours and longest_now:
        gap = round(target_hours - longest_now, 1)

    # the arithmetic the athlete needs before anything else
    budget_note = None
    if goal_key == "long_ride" and target_hours:
        needed = target_hours / LONG_DAY_SHARE
        if hours < needed - 0.2:
            budget_note = {
                "kind": "too_little_time",
                "needed_hours": round(needed, 1),
                "have_hours": round(hours, 1),
                "reachable_long_day": round(hours * LONG_DAY_SHARE, 1),
                "text": (
                    f"Mit {hours:.0f} Stunden pro Woche ist eine {target_hours:.1f}-Stunden-Fahrt "
                    f"nicht aufzubauen: sie wäre {target_hours / hours * 100:.0f} % deiner "
                    "Wochenzeit, und dann bleibt für alles andere nichts. Erreichbar sind "
                    f"aus dieser Woche etwa {hours * LONG_DAY_SHARE:.1f} Stunden am Stück. "
                    f"Für das Ziel brauchst du rund {needed:.0f} Wochenstunden — oder eine "
                    "einzelne lange Woche, in der die Fahrt Platz hat."
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
            "Die 80/20-Verteilung zählt Einheiten, nicht Minuten: bei fünf Fahrtagen vier "
            "lockere und eine harte. Zwei harte Einheiten sind der Standard für Wochen von "
            "8 bis 14 Stunden, und selbst WorldTour-Fahrer mit 25 Stunden gehen selten über "
            "drei. Einschränkung: 80/20 ist eine nützliche Beschreibung, keine allgemeine "
            "Wochenvorschrift — ein Review von 2023 fand nur sieben geeignete Studien und "
            "keinen Beleg, dass ein Verteilungsmodell immer gewinnt."
        ),
        "hours_source": ("angegeben" if profile.get("hours_per_week")
                         else "aus deinen letzten Wochen gerechnet"),
        "pattern_note": (
            f"{pattern} Belastungswochen, dann eine Entlastungswoche mit rund einem "
            "Drittel weniger Umfang. Ob die Wochen in Blöcken oder gemischt liegen, "
            "ändert nachweislich nichts am Ergebnis — lastgleich verglichen fanden "
            "zwölf Wochen bei trainierten Radfahrern keinen Unterschied. Blöcke haben "
            "einen anderen Vorteil: ein Reiz je Block macht die Planung einfach und "
            "lässt sie sich an die Wochen anpassen, die das Leben übrig lässt."
        ),
        "longest_now": round(longest_now, 1) or None,
        "target_hours": target_hours or None,
        "gap_hours": gap,
        "weeks_left": weeks_left,
        "weeks": out_weeks,
        "budget_note": budget_note,
        "caveat": (
            "Der Zuwachs des langen Tages von rund 12 % je Belastungswoche ist eine "
            "verbreitete Konvention, kein Studienergebnis. Die Wochen sind ein Vorschlag "
            "auf Basis deiner Angaben — die Zustandserkennung aus HRV und Ruhepuls hat "
            "am Tag selbst Vorrang: ein Einbruch schlägt jeden Plan."
        ),
    }


def _sessions(goal: dict[str, Any], goal_key: str, days: int, week_hours: float,
              long_day: float, kind: str, phase: str, profile: dict[str, Any],
              target_hours: float, hard_per_week: int = 2) -> list[dict[str, Any]]:
    """The sessions of one week, fitted into the days that are available."""
    sessions: list[dict[str, Any]] = []
    remaining_hours = week_hours
    slots = days

    if goal_key == "long_ride" and slots > 0:
        hours_long = min(long_day, week_hours * 0.6)
        late_quality = phase in ("specific",) and kind == "load"
        sessions.append({
            "role": "long",
            "title": f"Langer Tag — {hours_long:.1f} h",
            "workout": "z2_90",
            "detail": (
                "Gleichmäßig knapp unter der aeroben Schwelle. "
                + ("Die letzten 30–40 Minuten mit 2×10 min zügig — Qualität im ermüdeten "
                   "Zustand ist genau das, was das Ziel verlangt."
                   if late_quality else
                   "Noch ohne harte Anteile; erst geht es um die Dauer.")
            ),
            "why": (
                "Ab etwa sechs bis acht Wochen vor dem Ziel gehört harte Arbeit ans ENDE "
                "der langen Fahrt, nicht an den Anfang — ein frischer Intervallblock "
                "trainiert nicht, was im letzten Drittel gebraucht wird."
                if late_quality else
                "Lange Einheiten nahe unter der aeroben Schwelle bauen Fettoxidation und "
                "Ermüdungswiderstand — die Grundlagen der Durability."
            ),
            "fuel": ("Durchgehend essen und trinken. Der Reiz soll aus der Belastung kommen, "
                     "nicht aus leeren Speichern — das ist der häufigste Fehler bei langen "
                     "Einheiten."),
            "hours": round(hours_long, 1),
        })
        remaining_hours -= hours_long
        slots -= 1

    quality_slots = 0 if kind == "recovery" else min(
        hard_per_week, max(0, slots - 1) if goal_key == "long_ride" else slots)
    if phase == "taper":
        quality_slots = min(1, quality_slots)

    for number in range(quality_slots):
        if goal_key == "vo2max":
            workout, title = ("vo2_3015", "VO2max — 30/15") if number == 0 else ("vo2_4x8", "VO2max — 4×8 min")
        elif goal_key == "ftp":
            workout, title = ("threshold_3x12", "Schwelle 3×12") if number == 0 else ("sweetspot_2x20", "SweetSpot 2×20")
        elif goal_key == "long_ride":
            workout, title = ("sweetspot_2x20", "SweetSpot 2×20")
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
        remaining_hours -= 1.2
        slots -= 1

    while slots > 0:
        hours_each = max(1.0, remaining_hours / slots) if slots else 1.0
        sessions.append({
            "role": "endurance",
            "title": f"Grundlage — {hours_each:.1f} h",
            "workout": "z2_60" if hours_each < 1.4 else "z2_90",
            "detail": "Gleichmäßig, DFA über 0,75. Kein Reiz, sondern Substanz.",
            "why": "Der Anteil, der im Dreizonenmodell 75–80 % der Einheiten ausmacht.",
            "hours": round(hours_each, 1),
        })
        remaining_hours -= hours_each
        slots -= 1

    if kind == "recovery":
        for session in sessions:
            if session["role"] == "long":
                session["hours"] = round(session["hours"] * 0.7, 1)
                session["title"] = f"Langer Tag (verkürzt) — {session['hours']:.1f} h"
                session["detail"] = ("Entlastungswoche: der lange Tag bleibt im Rhythmus, "
                                     "aber kürzer. Der Zuwachs macht hier Pause.")
    return sessions
