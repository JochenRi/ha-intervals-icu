"""The §9 table is held against a real suite run.

Twice now the table in PROJEKTSTAND §9 has been pulled up by hand, and twice
it has gone stale: at 0.44.0 it summed to 4.185 while the suite counted 4.518.
Four rows were low, eleven were right, and nothing said so. A number nobody
checks is a number nobody can rely on - and the header quotes it too, so the
document contradicted itself on its first page.

WHY THIS RUNS THE SUITE INSTEAD OF READING IT
test_suite_hygiene counts CALL SITES with a regex, which is the right tool for
its question ("is anything counted after the summary?"). It is the wrong tool
for this one: most checks in test_workouts and test_panel_views sit inside
loops over truth tables, so the number of call sites and the number of executed
checks are different quantities by construction. The table states executed
checks. So the suite is run, as subprocesses, and the printed numbers are read.
Cost: about five seconds on top of the suite's own five.

WHY ITS OWN ROW IS NOT A CIRCULAR ARGUMENT
This file cannot run itself - that would recurse - so its own row is compared
against its own CHECKS counter, as the LAST counted check in the file. That is
a fixed point, not a circle: at that moment CHECKS has a definite value, and
the hygiene rule "nothing counted after the summary" is what keeps it definite.
Add a check anywhere in this file and the number moves, the comparison fails,
and the table gets pulled up - which is exactly the behaviour wanted. Anyone
tempted to "fix" this into a real self-run should read this paragraph first.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
PROJEKTSTAND = ROOT / "PROJEKTSTAND.md"
SELF = Path(__file__).name

FAILURES: list[str] = []
CHECKS = 0


def check(condition: bool, label: str) -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILURES.append(label)


def eq(got, want, label: str) -> None:
    check(got == want, f"{label}: {got!r} statt {want!r}")


# --- run every other suite file and read the number it prints -----------------
COUNT = re.compile(r"(\d+)\s+Prüfungen")

files = sorted(p.name for p in TESTS.glob("test_*.py")) + \
        sorted(p.name for p in TESTS.glob("test_*.js"))
files = [f for f in files if f != SELF]
check(len(files) >= 14, f"Prüfstand: nur {len(files)} Testdateien gefunden")

measured: dict[str, int] = {}
for name in files:
    runner = [sys.executable, name] if name.endswith(".py") else ["node", name]
    proc = subprocess.run(runner, cwd=TESTS, capture_output=True, text=True, timeout=600)
    hits = COUNT.findall(proc.stdout or "")
    # A file that runs checks without reporting a number is a FINDING, not a
    # blemish - that is the 0.36.0 lesson, where five files ran 187 unreported
    # checks and the hygiene guard let it pass because "at most one summary"
    # also permits none.
    check(bool(hits), f"Prüfstand: {name} meldet keine Zahl")
    eq(proc.returncode, 0, f"Prüfstand: {name} läuft nicht grün")
    if hits:
        measured[name] = int(hits[-1])


# --- read the table in §9 -----------------------------------------------------
text = PROJEKTSTAND.read_text(encoding="utf-8")
section = text.split("## 9. Prüfstand", 1)
check(len(section) == 2, "Prüfstand: §9 nicht gefunden")
body = section[1].split("\n## ", 1)[0] if len(section) == 2 else ""

ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|.*\|\s*(\d+)\s*\|\s*$", re.MULTILINE)
tabled = {name: int(count) for name, count in ROW.findall(body)}
check(bool(tabled), "Prüfstand: die §9-Tabelle hat keine lesbaren Zeilen")

# --- hold one against the other, row by row, GEZÄHLT UND BENANNT -------------
# SELF is compared against its own counter further down, not run - so it is
# taken out here, or it would count as "in the table but never runs".
for name in sorted(set(measured) | (set(tabled) - {SELF})):
    if name not in tabled:
        check(False, f"§9-Tabelle: {name} läuft im Prüfstand, steht aber nicht in der Tabelle")
    elif name not in measured:
        check(False, f"§9-Tabelle: {name} steht in der Tabelle, läuft aber nicht")
    else:
        eq(tabled[name], measured[name], f"§9-Tabelle: {name}")

# The header quotes the same figure, so a table that is right while the header
# is stale would still leave the document contradicting itself.
grand = re.search(r"\*\*([\d.]+)\*\* gezählten Einzelprüfungen", text) or \
        re.search(r"mit \*\*([\d.]+)\*\* gezählten", text)
check(grand is not None, "Prüfstand: die Gesamtzahl steht nicht im Kopf von PROJEKTSTAND")

files_claim = re.search(r"\*\*(\w+) Dateien, ([\d.]+) gezählte Einzelprüfungen", body)
check(files_claim is not None, "Prüfstand: §9 nennt Dateizahl und Summe nicht")


def _int(value: str) -> int:
    return int(value.replace(".", ""))


# The count of files is spelled out in German in §9's opening sentence.
WORDS = {14: "Vierzehn", 15: "Fünfzehn", 16: "Sechzehn", 17: "Siebzehn"}


# --- this file's own row, and the two totals ---------------------------------
# See the docstring: a fixed point, not a circle. Everything that counts must
# already have happened here EXCEPT the four checks below, which are therefore
# added by hand. Get that number wrong and this block fails and says so - the
# arithmetic checks itself.
REMAINING = 4
own_count = CHECKS + REMAINING
expected_total = sum(measured.values()) + own_count

eq(_int(grand.group(1)) if grand else None, expected_total,
   "Kopfzeile von PROJEKTSTAND: Gesamtzahl der Prüfungen")
eq(_int(files_claim.group(2)) if files_claim else None, expected_total,
   "§9: Summe im Einleitungssatz")
eq(files_claim.group(1) if files_claim else None, WORDS.get(len(files) + 1),
   "§9: Dateizahl im Einleitungssatz")
eq(tabled.get(SELF), own_count,
   f"§9-Tabelle: {SELF} (eigene Zeile, gegen den eigenen Zähler)")

print(f"test_projektstand: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
sys.exit(1 if FAILURES else 0)
