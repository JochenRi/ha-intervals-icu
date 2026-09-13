"""Reconcile the local archive against what Intervals still holds.

The importer only ever ADDS. An activity deleted on intervals.icu stays in the
archive for good and keeps counting - as a peer in every comparison, as a row
in every list. There is no deletion feed and no timestamp that would reveal a
removal: a deletion leaves nothing behind, so no ``updated`` field could ever
find one. What remains is the window comparison - the answer for a window is
authoritative, and an id missing from it does not exist any more.

This is NOT a delete function. There is no operation here that removes one
chosen activity; removal is a consequence of the comparison and has exactly
one outcome - parity with Intervals. Nothing is ever sent to intervals.icu.

The comparison is split in two on purpose:

``plan()`` reads and decides, ``apply()`` writes. A failure can therefore only
ever happen before anything was touched - that is lock 1, expressed as
architecture instead of as a promise. ``plan()`` raises on anything it cannot
vouch for; the caller that never reaches ``apply()`` has already done the safe
thing.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Iterable

# All the comparison needs. The payload is trimmed server side, so the whole
# history fits into a single request. start_date_local is not decoration: it
# tells us which span the answer actually covers.
RECONCILE_FIELDS: tuple[str, ...] = ("id", "start_date_local")

# Lock 3. More than this share of a window missing at once is not a tidy-up,
# it is a broken fetch that happens to parse.
MAX_MISSING_SHARE = 0.20


def _day(value: Any) -> str | None:
    """Return the calendar day of an Intervals timestamp, or None.

    ``start_date_local`` carries a time ("2026-09-04T17:32:00"), the window
    bounds are plain dates - comparing the two as strings would drop every
    activity recorded on the last day of the window.
    """
    if not isinstance(value, str) or len(value) < 10:
        return None
    day = value[:10]
    try:
        date.fromisoformat(day)
    except ValueError:
        return None
    return day


def remote_index(rows: Any) -> dict[str, str]:
    """Return {id: day} for a fetched window, or raise.

    Deliberately stricter than ``importer.merge_activities``, which skips a
    malformed row and carries on. Here a skipped row would read as "this
    activity is gone" - so anything the answer cannot fully account for aborts
    the whole comparison instead.
    """
    if not isinstance(rows, list):
        raise ValueError(f"Antwort ist keine Liste, sondern {type(rows).__name__}")
    index: dict[str, str] = {}
    for position, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"Zeile {position} ist kein Datensatz")
        key = row.get("id")
        if key is None or str(key) == "":
            raise ValueError(f"Zeile {position} hat keine id")
        index[str(key)] = _day(row.get("start_date_local")) or ""
    return index


def activity_day(data: dict[str, Any], key: str) -> str | None:
    """Return the archived day of one activity, or None when unknown."""
    activity = (data.get("activities") or {}).get(key)
    if not isinstance(activity, dict):
        return None
    return _day(activity.get("start_date_local"))


def in_window(day: str | None, oldest: date, newest: date) -> bool:
    """Return True when a day falls inside the fetched window, bounds included.

    An activity whose day cannot be read is never inside: lock 2 has to be
    provable, and an unreadable date proves nothing.
    """
    if day is None:
        return False
    return oldest.isoformat() <= day <= newest.isoformat()


def covers_history(data: dict[str, Any], oldest: date, newest: date) -> bool:
    """Return True when the window demonstrably spans the whole archive.

    Two of the three tidy-up sites carry no date at all: ``unavailable`` is a
    bare list of ids, and a DFA summary whose activity is already gone has
    nothing left to date it by. Lock 2 cannot be checked there - so those two
    are only ever touched when the window covers everything anyway, and that
    is decided here rather than assumed from the caller's good intentions.
    """
    for key, activity in (data.get("activities") or {}).items():
        day = _day(activity.get("start_date_local")) if isinstance(activity, dict) else None
        if day is None:
            # An activity without a usable date could sit anywhere, including
            # before the window. Then the window is not provably complete.
            return False
        if not in_window(day, oldest, newest):
            return False
    return True


def _orphan_dfa(data: dict[str, Any]) -> set[str]:
    """Return DFA keys whose activity is no longer in the archive."""
    activities = data.get("activities") or {}
    return {key for key in (data.get("dfa") or {}) if key not in activities}


def plan(
    data: dict[str, Any],
    rows: Any,
    oldest: date,
    newest: date,
) -> dict[str, Any]:
    """Compare a fetched window against the archive without changing anything.

    Raises ValueError when the answer is not fully accountable - the caller
    then never reaches apply(), and the archive is untouched (lock 1).
    """
    remote = remote_index(rows)
    full_history = covers_history(data, oldest, newest)

    activities = data.get("activities") or {}
    unavailable = list(data.get("unavailable") or [])
    orphans = _orphan_dfa(data)

    # Lock 2: only what the window can speak for.
    candidates: list[tuple[str, str, str | None]] = []  # (id, kind, day)
    for key in activities:
        day = activity_day(data, key)
        if in_window(day, oldest, newest):
            candidates.append((key, "activity", day))
    if full_history:
        for key in unavailable:
            candidates.append((str(key), "unavailable", None))
        for key in sorted(orphans):
            candidates.append((key, "dfa", None))

    missing = []
    for key, kind, day in candidates:
        if key in remote:
            continue
        activity = activities.get(key) if isinstance(activities.get(key), dict) else {}
        missing.append(
            {
                "id": key,
                "kind": kind,
                "date": day,
                "name": activity.get("name") or "",
                "type": activity.get("type") or "",
                "dfa": key in (data.get("dfa") or {}),
            }
        )
    missing.sort(key=lambda item: (item["date"] or "", item["id"]))

    checked = len(candidates)
    # Lock 3. An empty window has nothing to be a share OF - and nothing can
    # be missing from it either, so zero is the honest answer, not a division.
    share = (len(missing) / checked) if checked else 0.0
    capped = share > MAX_MISSING_SHARE

    return {
        "oldest": oldest.isoformat(),
        "newest": newest.isoformat(),
        "full_history": full_history,
        "checked": checked,
        "remote": len(remote),
        "missing": missing,
        "share": share,
        "capped": capped,
        "cap_limit": MAX_MISSING_SHARE,
        # What may actually be handed to apply(). Empty while capped: the
        # report is then a report, not a pending operation.
        "removable": [] if capped else [item["id"] for item in missing],
    }


def apply(data: dict[str, Any], ids: Iterable[str]) -> dict[str, int]:
    """Remove the given ids from all three tidy-up sites.

    ``activities`` is the obvious one. The DFA block hangs off the activity id
    and the ``unavailable`` list holds ids too - leave either standing and the
    header counts two numbers that do not add up.
    """
    wanted = {str(key) for key in ids}
    removed = {"activities": 0, "dfa": 0, "unavailable": 0}
    if not wanted:
        return removed

    activities = data.get("activities")
    if isinstance(activities, dict):
        for key in wanted & set(activities):
            del activities[key]
            removed["activities"] += 1

    dfa = data.get("dfa")
    if isinstance(dfa, dict):
        for key in wanted & set(dfa):
            del dfa[key]
            removed["dfa"] += 1

    unavailable = data.get("unavailable")
    if isinstance(unavailable, list):
        kept = [key for key in unavailable if str(key) not in wanted]
        removed["unavailable"] = len(unavailable) - len(kept)
        data["unavailable"] = kept

    return removed


def changed(removed: dict[str, int]) -> bool:
    """Return True when apply() actually took something out.

    The no-op case has to stay a no-op all the way down: a comparison without
    a difference must not trigger a save, or every click rewrites the archive
    for nothing.
    """
    return any(removed.values())
