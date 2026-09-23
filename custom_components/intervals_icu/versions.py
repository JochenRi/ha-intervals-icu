"""Versionsmarken im Archiv: EINE Vergleichsregel fuer alle Zaehler.

Warum ein eigenes Modul (0.66.3, Karte F1.5 / Sollzustand S8): das Paket
fuehrt vier Marken, die im LADEWEG entscheiden, ob ein Bestand faellt -
`dfa_version`, `fields_version`, `section_marks[].v`, `ramp_tests[].v`. Bis
0.66.2 verglichen drei davon auf UNGLEICH und eine (die Marken, seit 0.63.3)
auf AELTER. Ungleich trifft auch den NEUEREN Stand - und genau der entsteht
auf dem Rueckweg, den die Richtungsentscheidung vom 19.09. vorsieht: das
HACS-Downgrade. Wer zurueckrollte, haette `dfa` ganz und jedes
Stufentest-Ergebnis verloren, obwohl die Zeilen unter einer hoeheren Marke
geschrieben waren (§7, vierzigster Fall, dort nur fuer die Marken behoben).

Zwei Regeln, beide hier und nirgends sonst:

* `is_older(stored, current)`: verwerfen nur, was AELTER ist. Fehlend, None
  oder nicht als Zahl lesbar heisst 0 - "aelter als alles" (die Lehre aus
  0.9.0: ein fehlender Zaehler ist ein uralter, kein aktueller).
* `keep_newest(stored, current)`: eine Marke wird NIE nach unten
  geschrieben. Ein Bestand, der unter einer hoeheren Marke steht, behaelt
  sie - sonst schriebe der Rueckweg ihn herunter, und der naechste echte
  Bump loeschte ihn doch noch.

Was das NICHT loest: nach einem Downgrade stehen Zeilen der neueren
Rechnung neben Zeilen der aelteren, bis der naechste Bump alles neu holt.
Das ist dieselbe Mischung, die 0.63.3 fuer die Marken in Kauf genommen hat,
und sie ist hier so gewollt: Daten behalten schlaegt Daten reinhalten.
"""

from __future__ import annotations

from typing import Any


def as_mark(value: Any) -> int:
    """Eine Versionsmarke als Zahl - fehlend, None oder Unsinn heisst 0."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def is_older(stored: Any, current: int) -> bool:
    """True, wenn der Bestand unter einer AELTEREN Marke steht als der Code."""
    return as_mark(stored) < int(current)


def keep_newest(stored: Any, current: int) -> int:
    """Die Marke, die nach dem Schreiben steht: nie kleiner als die gespeicherte."""
    return max(as_mark(stored), int(current))
