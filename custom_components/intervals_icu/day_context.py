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
    # 0.72.1 (Skizze 3): Cannabis wie Alkohol - ein akuter Stressor, der Wert
    # bleibt echt. Das Gewicht 0,5 ist eine SETZUNG (wie bei Alkohol), der Beleg
    # steht am Etikett.
    "cannabis": {"label": "Cannabis", "weight": 0.5,
                 "read": "akuter Stressor, senkt die nächtliche HRV — der Wert bleibt echt",
                 "source": ("Gonzalez et al. 2026, J Sleep Res, doi 10.1111/jsr.70298, "
                            "PMID 41692699 — Pilotstudie, 18 Erwachsene: 10 mg THC oral vor dem "
                            "Schlaf senkte die nächtliche HRV deutlich (Zeit- und Frequenzbereich). "
                            "Gewicht 0,5 = Setzung, wie bei Alkohol.")},
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


# What the panel's source block says about this feature - ONE place, so the
# panel cannot drift from the module that defines the rules (Auflage A:
# belegt oder als Setzung gekennzeichnet, kein Drittes).
SOURCES: dict[str, Any] = {
    "belegt": [
        {"text": "Etikettieren und bedingtes Vergleichen von Messungen "
                 "(Training, Alkohol, Zyklus, Krankheit als Kontext-Tags, "
                 "9 Mio. Nächte)",
         "source": "Altini/Plews, Sensors 2021, 21:7932"},
        {"text": "Tagschlaf ist eine andere Messbedingung: bei nicht "
                 "adaptierten Nachtschichtlern ist das LF/HF-Verhältnis im "
                 "Tagschlaf signifikant erhöht",
         "source": "Boudreau/Boivin, PLOS ONE 2013; gestützt von "
                    "van Amelsvoort 2001"},
        {"text": "THC vor dem Schlaf senkt die nächtliche HRV (Etikett Cannabis; "
                 "Pilotstudie, 18 Erwachsene, 10 mg oral)",
         "source": "Gonzalez et al. 2026, J Sleep Res, PMID 41692699"},
    ],
    "setzung": [
        "Die Gewichtszahlen je Etikett (0 / 0,5 / 1) sind eine Setzung, "
        "keine Studienzahl.",
        "Die Schwelle Σw ≥ 30 belastbare Tage im 60er-Fenster ist eine "
        "Setzung — halbe Fensterbreite, damit die gewichtete Linie nicht "
        "auf dünnem Bestand steht.",
        "Ab etwa 15 etikettierten Tagen je Bedingung kann eine eigene "
        "Basislinie je Bedingung stehen (Paket B4) — auch diese Zahl ist "
        "eine Setzung.",
    ],
    "fix": "Die gewichtete Basislinie ist eine Brücke. Die saubere, belegte "
           "Lösung heißt B4: getrennte Basislinien je Messbedingung, wie es "
           "die HRV4Training-Arbeiten tun. Ein Zyklus-Etikett fehlt noch — "
           "offener Punkt für die Veröffentlichung, nicht für diesen Stand.",
    "read": "Nach einer Nachtschicht sieht der Wert oft schlechter aus. Das "
            "ist die Messbedingung, nicht dein Zustand: die Schlafalgorithmen "
            "sind für Nachtschlaf gebaut, und Tagschlaf misst sich anders. "
            "Deshalb zählt so ein Tag nicht in deine Basislinie — aber er "
            "wird nie weggerechnet: ein extremer Wert löst die Warnung "
            "weiter aus und trägt dann sein Etikett. „Erklärt“ "
            "heißt hier: gesehen, benannt, nicht verschwunden. Bei "
            "regelmäßigen Nachtschichten steigt die Basislinie auf "
            "deine guten Nächte — Tage nach der Schicht laufen dann "
            "öfter als erklärte Ausreißer. Das ist gewollt "
            "und sichtbar, kein Fehler.",
}


def set_entry(data: dict[str, Any], day: str, tag: str,
              weight: Any = None, note: str = "",
              set_at: str = "") -> dict[str, Any]:
    """Validate and store one day's context. Writing is STRICT - the
    tolerance of migrate() is for reading foreign data, not for producing
    it. Raises ValueError with a reason the panel can show."""
    if not _valid_day(day):
        raise ValueError(f"kein gültiges Datum: {day!r}")
    if tag not in TAGS:
        raise ValueError(f"unbekanntes Etikett: {tag!r}")
    if weight is None:
        weight = TAGS[tag]["weight"]
    if not isinstance(weight, (int, float)) or float(weight) not in VALID_WEIGHTS:
        raise ValueError(f"Gewicht außerhalb {VALID_WEIGHTS}: {weight!r}")
    if not isinstance(note, str):
        raise ValueError("Notiz muss Text sein")
    entry = {"tag": tag, "weight": float(weight),
             "note": note[:NOTE_LIMIT], "set_at": set_at}
    data.setdefault("day_context", {})[day] = entry
    return entry


def remove_entry(data: dict[str, Any], day: str) -> bool:
    """Delete a day's context COMPLETELY. Removing is a retraction, not a
    statement - the day must afterwards compute byte-identically to a day
    that was never labelled, so no stub of any kind stays behind."""
    block = data.get("day_context")
    if isinstance(block, dict) and day in block:
        del block[day]
        return True
    return False


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
