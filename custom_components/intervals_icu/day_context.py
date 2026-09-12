"""Day context: hand-set labels for the measurement condition of a night.

Why labels and not free numbers: HRV4Training (Altini/Plews, Sensors 2021,
21:7932) collects context AFTER each measurement - training, alcohol,
sickness, cycle - and analyses the conditions separately. Oura's Rest Mode
reweights contributions instead of inventing a number. And the night-shift
case is a MEASUREMENT condition, not a state: sleep algorithms are built for
nocturnal sleep, and in non-adapted shift workers the LF/HF ratio during
daytime sleep is significantly elevated (Boudreau/Boivin, PLOS ONE 2013;
van Amelsvoort 2001). The value after a night shift is not "bad" - it
measures something else.

The weights themselves are a STIPULATION, not a finding - a bridge until the
per-condition baseline (Paket B4) has enough labelled days to stand on. The
panel says so next to the numbers.

This block is written by the panel only, never by the API, and never leaves
the archive. Data keys are ASCII slugs; the German display labels live in
TAGS so there is exactly one source for both.

Level rules (docs/ausbau.md B3), enforced in coach.py and guarded by tests:
  1. baselines are weighted through this vocabulary,
  2. the warning lamp NEVER excludes a day - a labelled extreme day is
     marked "explained" but keeps triggering,
  3. analytics (ACWR, monotony, load budget) never reads these weights.
"""

from __future__ import annotations

from typing import Any

# slug -> display label and default weight. The label is the rule, the
# number the exception (0-1 in steps of 0.25, set per day if needed).
TAGS: dict[str, dict[str, Any]] = {
    "normal": {"label": "Normal", "weight": 1.0,
               "read": "voller Beitrag zur Basislinie"},
    "nachtschicht": {"label": "Nachtschicht", "weight": 0.0,
                     "read": "Tagschlaf ist eine andere Messbedingung — "
                             "zählt nicht in die Basislinie"},
    "spaetschicht": {"label": "Spätschicht", "weight": 0.5,
                     "read": "verschobener, aber nächtlicher Schlaf"},
    "alkohol": {"label": "Alkohol", "weight": 0.5,
                "read": "belegter akuter Stressor, der Wert bleibt echt"},
    "reise": {"label": "Reise", "weight": 0.5,
              "read": "akuter Stressor, klingt meist nach einem Tag ab"},
    "krank": {"label": "Krank", "weight": 0.0,
              "read": "für die Basislinie null — für die Warnlampe voll"},
    "uhr_nicht_getragen": {"label": "Uhr nicht getragen", "weight": 0.0,
                           "read": "Messfehler, kein Zustand"},
}

VALID_WEIGHTS = (0.0, 0.25, 0.5, 0.75, 1.0)
NOTE_LIMIT = 256
# weighted baselines need this much effective history before they replace
# the unweighted band - half of the 60-value window. A stipulation.
MIN_WEIGHT_SUM = 30.0


def _valid_day(day: Any) -> bool:
    if not isinstance(day, str) or len(day) != 10:
        return False
    try:
        from datetime import date
        date.fromisoformat(day)
    except (ValueError, TypeError):
        return False
    return True


def entry_for(data: dict[str, Any], day: str) -> dict[str, Any] | None:
    """The stored context of one day, or None."""
    block = data.get("day_context")
    entry = (block or {}).get(day)
    return entry if isinstance(entry, dict) else None


def weight_for(data: dict[str, Any], day: str) -> float:
    """The day's baseline weight. An unlabelled day weighs 1.0 by definition."""
    entry = entry_for(data, day)
    if not entry:
        return 1.0
    weight = entry.get("weight")
    if isinstance(weight, (int, float)) and 0.0 <= float(weight) <= 1.0:
        return float(weight)
    return float(TAGS.get(entry.get("tag", ""), {}).get("weight", 1.0))


def migrate(block: Any) -> dict[str, Any] | None:
    """Bring a stored day_context block up to the current shape.

    Returns the repaired block, or None when nothing had to change - the
    same contract as plan.migrate_goal(). For this TOP-LEVEL key the
    empty_data() entry already covers old archives (async_load fills missing
    top-level keys), so unlike the nested goal profile the usual case here
    is a no-op. What this migration actually earns its keep with is
    normalisation: entries written by hand, by a broken client or by a
    future version are clamped into shape instead of poisoning a baseline.
    An UNKNOWN tag with a valid weight is kept - deleting it would destroy
    user data on a downgrade from a version with a larger vocabulary.
    """
    if not isinstance(block, dict):
        return {}
    repaired: dict[str, Any] = {}
    changed = False
    for day, entry in block.items():
        if not _valid_day(day) or not isinstance(entry, dict):
            changed = True
            continue
        tag = entry.get("tag")
        if not isinstance(tag, str) or not tag:
            changed = True
            continue
        weight = entry.get("weight")
        if not isinstance(weight, (int, float)) or not 0.0 <= float(weight) <= 1.0:
            if tag in TAGS:
                weight = TAGS[tag]["weight"]
                changed = True
            else:
                changed = True
                continue
        note = entry.get("note")
        if not isinstance(note, str):
            note = ""
            if entry.get("note") is not None:
                changed = True
        set_at = entry.get("set_at")
        if not isinstance(set_at, str):
            set_at = ""
            if entry.get("set_at") is not None:
                changed = True
        clean = {"tag": tag, "weight": float(weight),
                 "note": note[:NOTE_LIMIT], "set_at": set_at}
        if clean != entry:
            changed = True
        repaired[day] = clean
    return repaired if changed else None
