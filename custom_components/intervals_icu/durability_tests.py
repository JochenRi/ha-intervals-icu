"""Durability test protocol: which rides were tests, and what they measured.

Why this block exists at all (docs/ausbau.md J1): performance retention is NOT
computable from ordinary rides. The number that falls out of them measures the
lengths of the sections, not the fatigue - see PROJEKTSTAND 7, "die Messung
misst etwas anderes als behauptet". So the values come from a PROTOCOL, and a
protocol needs an athlete who says "this ride was the test".

Three rules this module exists to enforce (docs/ausbau.md K2):

  1. **No recognition.** "Long ride with two hard blocks at the end, that will
     have been the fatigued test" is a claim about a ride the system knows
     nothing about - the exact error class J1 measured. The athlete marks.
  2. **No automatic pairing.** A fatigued test names its fresh partner. With
     exactly one candidate it is SUGGESTED and confirmed, never set. Taking the
     nearest earlier one would be the pairing test_analytics forbids elsewhere.
  3. **Retractable.** A mis-marked test must not mean repairing the archive by
     hand.

What is stored and what is not: only the measured numbers, never streams
(J7). The STATE on the test day is not stored either - it is recomputed from
state_series() for the date, because it is derivable. Same rule as the streams.

The anchor for everything downstream is `p20` of the newest FRESH test. NOT
the FTP field: on this account the profile carries 215 W while the measured
20-minute best is 192 (docs/ausbau.md K0). A protocol tempo derived from 215
would sit 35 W above the measured aerobic threshold - a time trial to
exhaustion, not a fatigue block.
"""

from __future__ import annotations

from typing import Any

BLOCK = "durability_tests"

# Bumped when the measurement changes. Stored records carrying an older
# version are dropped and recomputed - the streams are not in the archive, so
# a correction would otherwise never reach the values already stored.
MEASURE_VERSION = 1

KINDS: dict[str, dict[str, str]] = {
    "fresh": {
        "label": "Termin 1 — frisch",
        "read": "Einrollen, 5 min all-out, 20 min all-out. Liefert die beiden "
                "Bezugswerte, aus denen alles Weitere folgt.",
    },
    "fatigued": {
        "label": "Termin 2 — ermüdet",
        "read": "Ermüdungsblock bei 80 % der frischen 20-Minuten-Leistung bis "
                "1.000 kJ, dann dieselben beiden All-outs.",
    },
}

NOTE_LIMIT = 256


def _valid_day(day: Any) -> bool:
    if not isinstance(day, str) or len(day) != 10:
        return False
    try:
        from datetime import date

        date.fromisoformat(day)
    except (ValueError, TypeError):
        return False
    return True


def _watts(value: Any) -> float | None:
    """A power value that is actually a power value. 0 and negatives are not."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if number > 0 else None


def entry_for(data: dict[str, Any], activity_id: Any) -> dict[str, Any] | None:
    """The stored test record of one activity, or None."""
    block = data.get(BLOCK)
    entry = (block or {}).get(str(activity_id))
    return entry if isinstance(entry, dict) else None


def entries(data: dict[str, Any], kind: str | None = None) -> list[dict[str, Any]]:
    """All test records, newest first, each carrying its own activity_id."""
    block = data.get(BLOCK)
    if not isinstance(block, dict):
        return []
    out = []
    for activity_id, entry in block.items():
        if not isinstance(entry, dict):
            continue
        if kind is not None and entry.get("kind") != kind:
            continue
        out.append({**entry, "activity_id": str(activity_id)})
    return sorted(out, key=lambda e: (str(e.get("date") or ""), str(e["activity_id"])),
                  reverse=True)


def set_entry(data: dict[str, Any], activity_id: Any, kind: str, date: str,
              p5: Any = None, p20: Any = None, paired_with: Any = None,
              note: str = "", set_at: str = "") -> dict[str, Any]:
    """Mark one activity as a protocol test. Writing is STRICT.

    The tolerance of migrate() is for reading foreign data, not for producing
    it - same split as day_context. Raises ValueError with a reason the panel
    can show.

    `paired_with` is only meaningful on a fatigued test and is only ever
    written from an explicit confirmation (K2): the suggestion is made in the
    panel, the confirmation arrives here as a value.
    """
    if kind not in KINDS:
        raise ValueError(f"unbekannte Testart: {kind!r}")
    if not _valid_day(date):
        raise ValueError(f"kein gültiges Datum: {date!r}")
    if not isinstance(note, str):
        raise ValueError("Notiz muss Text sein")
    if paired_with is not None and kind != "fatigued":
        raise ValueError("nur ein ermüdeter Test hat einen Partner")
    entry: dict[str, Any] = {
        "kind": kind,
        "date": date,
        "p5": _watts(p5),
        "p20": _watts(p20),
        "paired_with": None if paired_with is None else str(paired_with),
        "note": note[:NOTE_LIMIT],
        "set_at": set_at,
        "v": MEASURE_VERSION,
    }
    data.setdefault(BLOCK, {})[str(activity_id)] = entry
    return entry


def remove_entry(data: dict[str, Any], activity_id: Any) -> bool:
    """Withdraw a marking COMPLETELY.

    A retraction, not a statement: afterwards the ride must compute exactly
    like one that was never marked, so no stub stays behind. A fatigued test
    pointing at the removed fresh one loses its partner, not its own record -
    deleting the partner's data because its anchor went away would destroy
    something the athlete entered.
    """
    block = data.get(BLOCK)
    if not isinstance(block, dict) or str(activity_id) not in block:
        return False
    del block[str(activity_id)]
    for entry in block.values():
        if isinstance(entry, dict) and entry.get("paired_with") == str(activity_id):
            entry["paired_with"] = None
    return True


def migrate(block: Any) -> dict[str, Any] | None:
    """Bring a stored durability_tests block up to the current shape.

    Returns the repaired block, or None when nothing had to change - the same
    contract as plan.migrate_goal() and day_context.migrate(). A no-op must
    return None, because store.async_load turns anything else into a write,
    and a load that saves is a load that rewrites the archive on every start.

    For this TOP-LEVEL key the empty_data() entry already covers old archives.
    What this earns its keep with is the version mark: a record measured by an
    older algorithm has its NUMBERS dropped while the marking survives. The
    athlete said this ride was a test; that statement does not expire because
    the maths changed. The values do.
    """
    if not isinstance(block, dict):
        return {}
    repaired: dict[str, Any] = {}
    changed = False
    for activity_id, entry in block.items():
        if not isinstance(activity_id, str) or not activity_id or not isinstance(entry, dict):
            changed = True
            continue
        kind = entry.get("kind")
        if kind not in KINDS:
            changed = True
            continue
        date = entry.get("date")
        if not _valid_day(date):
            changed = True
            continue
        out: dict[str, Any] = {"kind": kind, "date": date}
        stale = entry.get("v") != MEASURE_VERSION
        for field in ("p5", "p20"):
            value = None if stale else _watts(entry.get(field))
            if value != entry.get(field):
                changed = True
            out[field] = value
        partner = entry.get("paired_with")
        if kind != "fatigued" and partner is not None:
            partner, changed = None, True
        elif partner is not None and not isinstance(partner, str):
            partner, changed = str(partner), True
        out["paired_with"] = partner
        note = entry.get("note")
        if not isinstance(note, str):
            note, changed = "", True
        elif len(note) > NOTE_LIMIT:
            note, changed = note[:NOTE_LIMIT], True
        out["note"] = note
        out["set_at"] = entry.get("set_at") if isinstance(entry.get("set_at"), str) else ""
        if out["set_at"] != entry.get("set_at"):
            changed = True
        if stale:
            changed = True
        out["v"] = MEASURE_VERSION
        repaired[activity_id] = out
    # a partner that no longer exists is a dangling pointer, not a pairing
    for entry in repaired.values():
        if entry["paired_with"] is not None and entry["paired_with"] not in repaired:
            entry["paired_with"] = None
            changed = True
    return repaired if changed else None


def anchor(data: dict[str, Any]) -> dict[str, Any] | None:
    """The reference values from the newest fresh test that actually measured.

    A marking without numbers (stream fetch failed, version bumped) is a
    marking, not an anchor - it is skipped, and the next one down is used.
    Returning the marking anyway would hand a None into the protocol maths.
    """
    for entry in entries(data, "fresh"):
        if entry.get("p20"):
            return {
                "activity_id": entry["activity_id"],
                "date": entry.get("date"),
                "p20": float(entry["p20"]),
                "p5": float(entry["p5"]) if entry.get("p5") else None,
            }
    return None


def pairs(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Confirmed fresh/fatigued pairs, newest fatigued first.

    Only EXPLICIT pairings count. There is deliberately no fallback that takes
    the nearest earlier fresh test: that is the automatic pairing K2 forbids,
    and it would quietly turn two unrelated rides into a measurement.
    """
    by_id = {entry["activity_id"]: entry for entry in entries(data)}
    out = []
    for entry in entries(data, "fatigued"):
        partner = by_id.get(str(entry.get("paired_with") or ""))
        if not partner or partner.get("kind") != "fresh":
            continue
        if not (entry.get("p20") and partner.get("p20")):
            continue
        out.append({"fresh": partner, "fatigued": entry})
    return out


SOURCES: dict[str, Any] = {
    "belegt": [
        {"text": "Heimtest an zwei Terminen, ausdrücklich für Amateure: 5 und "
                 "20 min all-out frisch, dann dieselben beiden nach einem "
                 "Ermüdungsblock über 1.000 kJ bei 80 % der frischen "
                 "20-Minuten-Leistung. Validiert an 20 gut trainierten "
                 "Amateuren.",
         "source": "Barsumyan/Soost/Burchard, BMC Sports Sci Med Rehabil 17:192 (2025)"},
        {"text": "Erfolgreiche Amateure verlieren nach 1.000 kJ 6,5 % über "
                 "20 min, weniger erfolgreiche 12,5 % — der Maßstab gilt NUR "
                 "für die 20-Minuten-Zeile, für 5 min fand die Studie keinen "
                 "Gruppenunterschied.",
         "source": "Frontiers in Sports and Active Living 2025"},
    ],
    "setzung": [
        "Die 10 Minuten Erholung zwischen den beiden All-outs sind gewählt — "
        "das Protokoll nennt keine Dauer. Sie müssen an beiden Terminen gleich "
        "sein, sonst vergleicht Termin 2 etwas anderes.",
        "Der Faktor 1,30 zwischen erwarteter 5- und 20-Minuten-Leistung geht "
        "nur in die VORAB geschätzte Last ein, nie in eine Vorgabe. Am eigenen "
        "Bestand gemessen (251 W gegen 192 W), für künftige Termine gesetzt.",
    ],
    "fix": "Der Anker kommt aus Termin 1, nicht aus dem FTP-Feld. Auf diesem "
           "Konto trägt das Profil 215 W, während die datengetriebene Schätzung "
           "bei 193 und die gemessene 20-Minuten-Bestleistung bei 192 liegt. "
           "Aus den 215 ergäbe sich ein Protokolltempo von rund 181 W — 35 W "
           "über der gemessenen aeroben Schwelle, also kein Ermüdungsblock, "
           "sondern ein Tempotest bis zum Abbruch.",
    "read": "Leistungserhalt lässt sich aus gewöhnlichen Fahrten nicht "
            "rechnen — nicht wegen zu weniger Daten, sondern weil die Zahl "
            "dabei die Abschnittslängen misst und nicht die Ermüdung. Deshalb "
            "kommen diese Werte aus zwei Terminen, die du selbst markierst. "
            "Das System erkennt keinen Test von allein und paart auch nichts "
            "von allein: beides wäre wieder eine Behauptung über eine Fahrt, "
            "über die es nichts weiß.",
}
