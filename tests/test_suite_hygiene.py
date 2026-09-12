"""The test suite checks itself.

Twice now a suite has counted checks it never reported. In 0.34.0
test_workouts.py carried two summary blocks: everything added behind the first
ran, but was neither counted nor printed - only the exit code knew, so the file
announced "0 Fehler" and exited 1. The same defect sat in test_plan.py, where
the hours contract (the very check written after the 0.31.0 budget error) ran
behind the summary and could not report a failure.

Fixing the two files does not remove the failure mode - the next block appended
to any suite lands behind its summary again. So the rule is enforced here:

  1. one summary line per file, and nothing counted after it,
  2. failures are printed, not just counted,
  3. the file ends by turning failures into a non-zero exit code.

Checked on the source text, because that is the format the defect lives in.
"""

import re
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parent
FAILURES: list[str] = []
CHECKS = 0


def check(condition: bool, label: str) -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILURES.append(label)


# A counted assertion in either language. The Python suites call check()/eq(),
# the panel suites ok()/contains(); matched with the opening bracket so a word
# inside a string does not count.
COUNTING = re.compile(r"(?<![A-Za-z_])(check|eq|ok|contains)\(")
PY_SUMMARY = re.compile(r"Prüfungen,")
JS_SUMMARY = re.compile(r"(?<![A-Za-z_])report\(")


def lines_of(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def positions(lines: list[str], pattern: re.Pattern) -> list[int]:
    """Line numbers (1-based) whose CODE matches - comments do not count."""
    out = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*"):
            continue
        if pattern.search(line):
            out.append(i)
    return out


py_files = sorted(TESTS.glob("test_*.py"))
js_files = sorted(TESTS.glob("test_*.js"))
check(len(py_files) >= 11, f"Prüfstand: nur {len(py_files)} Python-Dateien gefunden")
check(len(js_files) == 3, f"Prüfstand: {len(js_files)} Panel-Dateien statt 3")

for path in py_files:
    if path.name == Path(__file__).name:
        continue
    lines = lines_of(path)
    summaries = positions(lines, PY_SUMMARY)
    counted = positions(lines, COUNTING)
    name = path.name

    # 1 - exactly one summary, and no counted check behind it.
    #     "<= 1" used to be the rule, which let a file with NO summary through:
    #     its checks ran, printed PASS and carried the exit code, but never
    #     appeared in the suite's count - five files sat that way until 0.36.0.
    #     With "== 1" the ordering rule below can no longer be skipped either.
    check(len(summaries) == 1, f"{name}: {len(summaries)} Summary-Zeilen statt genau einer")
    check(len(counted) > 0, f"{name}: Summary ohne eine einzige gezählte Prüfung")
    if summaries and counted:
        last_check, summary = max(counted), summaries[-1]
        check(
            last_check < summary,
            f"{name}: Prüfung in Zeile {last_check} steht HINTER der Summary "
            f"(Zeile {summary}) - sie wird weder gezählt noch gemeldet",
        )

    # 2 - failures are printed, not only counted
    text = "\n".join(lines)
    prints_failures = (
        "for failure in FAILURES" in text
        or re.search(r'print\("FEHLER:", *failures', text) is not None
    )
    check(prints_failures, f"{name}: druckt die Fehlerliste nicht, nur den Zähler")

    # 3 - the exit code carries the verdict
    check(
        "sys.exit(" in text and ("FAILURES" in text or "failures" in text),
        f"{name}: Fehler erreichen den Exit-Code nicht",
    )

for path in js_files:
    lines = lines_of(path)
    summaries = positions(lines, JS_SUMMARY)
    counted = positions(lines, COUNTING)
    name = path.name
    check(len(summaries) == 1, f"{name}: {len(summaries)} report()-Aufrufe statt genau einem")
    check(len(counted) > 0, f"{name}: report() ohne eine einzige gezählte Prüfung")
    if summaries and counted:
        # report() itself matches COUNTING via none of its names, so the last
        # counted line must sit above it.
        last_check, summary = max(counted), summaries[-1]
        check(
            last_check < summary,
            f"{name}: Prüfung in Zeile {last_check} steht HINTER report() "
            f"(Zeile {summary}) - sie wird nicht gemeldet",
        )

print(f"test_suite_hygiene: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
sys.exit(1 if FAILURES else 0)
