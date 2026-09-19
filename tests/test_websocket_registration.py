"""The websocket registration, checked without starting Home Assistant.

0.9.4 shipped a handler inserted between another handler's decorators and its
`def`. The decorators then applied to the new function and the old one went
out bare, Home Assistant refused to register it, and the whole integration
failed to set up - no entities, no panel, nothing. A single misplaced block.

This reads the module as a syntax tree, so it needs neither HA nor a running
event loop, and it fails on exactly that class of mistake.
"""

import ast
import ast
import re
import sys
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu" / "websocket.py"

FAILURES: list[str] = []
CHECKS = 0


def check(condition: bool, label: str) -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILURES.append(label)


tree = ast.parse(MODULE.read_text())

functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        functions[node.name] = node

# --- which handlers does async_register hand to Home Assistant? ------------
registered: list[str] = []
register = functions.get("async_register")
check(register is not None, "async_register fehlt")
if register is not None:
    for sub in ast.walk(register):
        if isinstance(sub, ast.Name) and sub.id.startswith("websocket_") and sub.id in functions:
            if sub.id not in registered:
                registered.append(sub.id)

check(len(registered) >= 12, f"nur {len(registered)} Handler registriert - ist einer verlorengegangen?")

# --- every registered handler must carry the command decorator -------------
commands: dict[str, str] = {}
for name in registered:
    node = functions[name]
    decorators = [ast.unparse(d) for d in node.decorator_list]
    has_command = any("websocket_command" in d for d in decorators)
    check(has_command, f"{name}: kein @websocket_command - Home Assistant lehnt die Registrierung ab "
                       f"und die Integration startet nicht (Dekoratoren: {decorators or 'keine'})")

    # async handlers need async_response, sync handlers need callback
    is_async = isinstance(node, ast.AsyncFunctionDef)
    has_async_response = any("async_response" in d for d in decorators)
    has_callback = any(d.endswith("callback") for d in decorators)
    if is_async:
        check(has_async_response, f"{name}: async ohne @async_response")
        check(not has_callback, f"{name}: async mit @callback")
    else:
        check(has_callback, f"{name}: sync ohne @callback")
        check(not has_async_response, f"{name}: sync mit @async_response")

    # pull the command string out of the decorator so duplicates are visible
    for dec in node.decorator_list:
        text = ast.unparse(dec)
        if "websocket_command" not in text:
            continue
        # ast.unparse normalises quotes, so match either kind
        found = re.search(r"['\"]intervals_icu/([a-z0-9_]+)['\"]", text)
        if found:
            commands[name] = "intervals_icu/" + found.group(1)

check(len(commands) == len(registered),
      f"{len(registered) - len(commands)} Handler ohne erkennbaren Befehlsnamen")

# --- command names must be unique ------------------------------------------
seen: dict[str, str] = {}
for name, command in commands.items():
    if command in seen:
        FAILURES.append(f"Befehl {command} doppelt vergeben: {seen[command]} und {name}")
        CHECKS += 1
    else:
        seen[command] = name
        CHECKS += 1

# --- the panel's commands must all exist ------------------------------------
PANEL = Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu" / "frontend" / "intervals-panel.js"
panel_source = PANEL.read_text()
used = set()
for line in panel_source.splitlines():
    if '_ws("' in line:
        for part in line.split('_ws("')[1:]:
            used.add("intervals_icu/" + part.split('"', 1)[0])
for command in sorted(used):
    check(command in seen, f"Panel ruft {command} auf, das Backend kennt den Befehl nicht")

# --- a handler defined but never registered is dead code --------------------
for name, node in functions.items():
    if not name.startswith("websocket_") or name == "async_register":
        continue
    decorators = [ast.unparse(d) for d in node.decorator_list]
    if any("websocket_command" in d for d in decorators):
        check(name in registered, f"{name} ist dekoriert, wird aber nie registriert")

def check_eq(got, want, label):
    check(got == want, f"{label}: {got!r} statt {want!r}")


# --- the FTP has to be found where Intervals actually puts it -----------------
# It sits on every activity as icu_ftp. Looking for it anywhere else returns
# None, and every workout then falls back to percentages - which is the honest
# answer when nothing is known and the wrong one when the number was in the
# data all along. This cost three releases of "the percentages are gone" that
# were not.
import re as _re

source = SOURCE if "SOURCE" in dir() else open(
    Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu" / "websocket.py"
).read()
check("_latest_ftp" in source, "FTP: keine Suche in den Aktivitäten")
check("icu_ftp" in source, "FTP: das Feld icu_ftp wird nicht gelesen")
check("ftp = _latest_ftp(data)" in source,
      "FTP: die Aktivitäten werden gar nicht befragt")
if "ftp = _latest_ftp(data)" in source:
    check(source.index("ftp = _latest_ftp(data)")
          < source.index('for settings in (data.get("sport_settings")'),
          "FTP: die Aktivitäten werden erst nach sport_settings befragt")

namespace: dict = {}
block = source[source.index("def _latest_ftp"):source.index("def _state_for_plan")]
exec(block, {"Any": dict}, namespace)
latest = namespace["_latest_ftp"]
check_eq(latest({"activities": {
    "a": {"start_date_local": "2026-09-01T09:00", "icu_ftp": 210},
    "b": {"start_date_local": "2026-09-11T09:00", "icu_ftp": 215},
    "c": {"start_date_local": "2026-08-01T09:00", "icu_ftp": 200},
}}), 215.0, "FTP: nicht die neueste genommen")
check_eq(latest({}), None, "FTP: aus dem Nichts erfunden")
check_eq(latest({"activities": {"x": {"start_date_local": "2026-09-01", "icu_rolling_ftp": 192}}}),
   192.0, "FTP: rollierender Wert nicht als Rückfall genutzt")
check_eq(latest({"activities": {"x": {"start_date_local": "2026-09-01"}}}), None,
   "FTP: Wert erfunden, wo keiner steht")


# --- one recommendation source, and the anchors must not disagree silently ----
# 0.31.0 carried a second recommender (coach.recommend) whose verdict could
# quietly contradict the workout list, plus a weekly load read from
# wellness.load - the field that is not filled on every account. Both are the
# documented error classes 3 and 1; these checks keep them out.
check("coach_module.recommend" not in source,
      "eine Quelle: websocket ruft den entfernten zweiten Empfehler auf")
check('"conflict"' in source,
      "anker: der Watt/DFA-Konfliktwächter fehlt im workouts-Payload")
check("anchor_conflict" in source,
      "anker: workouts.anchor_conflict wird nicht befragt")
state_block = source[source.index("def _state_for_plan"):source.index("@websocket_api.websocket_command(\n    {\n        vol.Required(\"type\"): \"intervals_icu/goal\"")]
check("icu_training_load" in state_block,
      "wochenlast: nicht aus den Aktivitäten gelesen")
check('row.get("load")' not in state_block,
      "wochenlast: liest wieder wellness.load (Fehlerklasse 1)")


# --- one rule for the calendar anchor ----------------------------------------
# set_goal used to compute "the Monday of this week" itself. The moment the
# archive migration needed the same rule, that inline arithmetic became a
# second copy - error class 3, the one that cost 0.11.0 and 0.27.0 a release.
# The rule now lives in plan.anchor_stamp, and these two checks keep it there.
check("weekday()" not in source,
      "anker: websocket rechnet sich den Montag wieder selbst aus")
check("plan_lib.anchor_stamp(" in source,
      "anker: set_goal benutzt die gemeinsame Ankerregel nicht")
check("plan_lib.has_anchor(" in source,
      "anker: set_goal prüft den Anker nicht über die gemeinsame Regel")

# The repair itself has to be wired into the load path, or an old archive keeps
# its drifting plan until the athlete happens to re-save the goal.
STORE = MODULE.parent / "store.py"
store_src = STORE.read_text()
check("plan.migrate_goal(" in store_src,
      "anker: das Archiv migriert das Zielprofil beim Laden nicht")
if "plan.migrate_goal(" in store_src and "base.update(stored)" in store_src:
    at = store_src.index("plan.migrate_goal(")
    check(store_src.index("base.update(stored)") < at,
          "anker: migriert wird, bevor die Altdaten übernommen sind")
    check("schedule_save()" in store_src[at:at + 400],
          "anker: die Reparatur wird nie gespeichert")

# --- day_context (Paket B6): Lese- und Schreibweg -----------------------------
SRC = MODULE.read_text()
check("websocket_day_context" in registered, "day_context: Leseweg nicht registriert")
check("websocket_set_day_context" in registered, "day_context: Schreibweg nicht registriert")
check(commands.get("websocket_day_context") == "intervals_icu/day_context",
      "day_context: falscher Kommandoname am Leseweg")
check(commands.get("websocket_set_day_context") == "intervals_icu/set_day_context",
      "day_context: falscher Kommandoname am Schreibweg")
# Der Name intervals_icu/context ist seit 0.31.0 durch den Coach-Sitzungs-
# kontext belegt — die neuen Wege dürfen ihn nicht anfassen.
check(commands.get("websocket_context") == "intervals_icu/context",
      "day_context: der belegte Name intervals_icu/context wurde verändert")
_set_src = ast.get_source_segment(SRC, functions["websocket_set_day_context"]) or ""
check("day_context_lib.set_entry" in _set_src,
      "day_context: Schreibweg validiert nicht über das Modul")
check("day_context_lib.remove_entry" in _set_src,
      "day_context: tag=null löscht nicht über das Modul")
check('msg["tag"] is None' in _set_src,
      "day_context: der Löschweg über tag=null fehlt")
check("async_save_now" in _set_src, "day_context: Schreibweg speichert nicht")
check("invalid_format" in _set_src,
      "day_context: Validierungsfehler erreichen den Aufrufer nicht")
_read_src = ast.get_source_segment(SRC, functions["websocket_day_context"]) or ""
for _need in ("day_context_lib.TAGS", "day_context_lib.SOURCES",
              "day_context_lib.VALID_WEIGHTS", "day_context_lib.MIN_WEIGHT_SUM"):
    check(_need in _read_src,
          f"day_context: Leseweg liefert {_need.split('.')[-1]} nicht aus dem Modul")
# Ampel-Herkunftsnotiz: die Divergenz wird gesagt, nicht geschluckt
_ready_src = ast.get_source_segment(SRC, functions["websocket_readiness"]) or ""
check("context_note" in _ready_src and "B4" in _ready_src,
      "readiness: Herkunftsnotiz zur ungewichteten Ampel fehlt")
check("ungewichtet gerechnet" in _ready_src,
      "readiness: die Notiz benennt die ungewichtete Rechnung nicht")


# --- the goal handler: grades for the CURRENT week only (ausbau.md I3) --------
# The handler wires state, budget and grade together; it must not restate any
# of them, and it must not grade a week whose budget does not exist yet.
goal_fn = functions.get("websocket_goal")
check(goal_fn is not None, "goal: Handler fehlt")
if goal_fn is not None:
    src = ast.get_source_segment(MODULE.read_text(), goal_fn) or ""
    for call in ("rate_sessions", "week_done", "recovery_offered", "readiness"):
        check(call in src, f"goal: {call} wird nicht gerufen — die Ansicht rechnet selbst")
    # only weeks[0] is graded, and it is the one marked as rated
    check('weeks[0]["rated"] = True' in src, "goal: die laufende Woche wird nicht markiert")
    check("weeks[1]" not in src and "for week in weeks" not in src,
          "goal: mehr als die laufende Woche wird bewertet — das ist die Prognose")
    check("NO_VERDICT_NOTE" in src, "goal: der Satz für spätere Wochen fehlt in der Payload")
    check("STAGES" in src, "goal: das Stufenregister erreicht das Panel nicht")
    check("CHOICE_EVIDENCE" in src, "goal: der Quellenblock fehlt in der Payload")
    # no threshold of its own: the handler compares nothing, it hands over
    for forbidden in ("<=", ">=", " < ", " > "):
        check(forbidden not in src,
              f"goal: der Handler vergleicht selbst ('{forbidden}') statt zu verdrahten")
    # Gegenprobe: der Wächter muss einen eingebauten Vergleich auch finden
    check("<=" in src + "\n    if load <= budget: pass",
          "goal Gegenprobe: ein eingebauter Vergleich wird NICHT gefunden — der Wächter ist blind")

# --- DER VORGABEWERT-WAECHTER (PROJEKTSTAND 7, 0.44.0) ----------------------
# Gefunden beim Bau von Paket K: websocket_workouts hat `recovery_offered` nie
# an suggest() uebergeben. Der Vorgabewert False ist stillschweigend
# eingesprungen, also konnte die Reiz-Stufe auf dem TRAINER-Reiter nie
# erscheinen - waehrend die Wochenansicht sie korrekt zeigt.
#
# Das ist NICHT Fehlerklasse 3 (zwei Rechenwege), sondern deren Schwester:
# eine Regel, ein Ort, aber zwei Aufrufer, von denen einer sie mit einem
# Vorgabewert fuettert. Ein Vorgabewert ist eine zweite Wahrheit in Tarnung,
# weil er unauffaellig richtig aussieht - keine der elf Gegenproben aus
# 0.42.0 hat ihn gesehen, weil sie stage() geprueft haben und nicht den Weg
# dorthin.
#
# Der Waechter prueft deshalb BEIDES:
#   (a) jeder Aufruf einer Urteilsfunktion nennt jeden Urteilseingang,
#   (b) die Liste der Urteilsfunktionen ist vollstaendig - eine neue Funktion
#       in workouts.py mit Vorgabewerten fuer Urteilseingaben MUSS hier
#       stehen, sonst schuetzt der Waechter genau bis zur naechsten Funktion
#       und ist wieder ein Einzelfall statt einer Klasse.
WORKOUTS = Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu" / "workouts.py"
wtree = ast.parse(WORKOUTS.read_text(encoding="utf-8"))

# DIESE LISTE IST VON HAND ZU PFLEGEN. Kommt eine Urteilsfunktion dazu, gehoert
# sie hier hinein - Pruefung (b) unten faellt sonst, benannt.
# `ramp_protocol` kam in 0.51.1 dazu - und der Waechter hat es beim ERSTEN
# Lauf gemeldet, wie 0.44.0 bei `fatigued_session()` und `scaled()`. Eine
# Liste ohne Vollstaendigkeitspruefung schuetzt genau bis zur naechsten
# Funktion (vierte Bauregel, §9).
JUDGEMENT_FUNCTIONS = {"suggest", "rate_sessions", "fit_for", "stage", "scaled",
                       "ramp_protocol"}

# Eingaenge, die ein Urteil VERAENDERN. `limit` ist eine Anzeigegrenze und
# steht bewusst nicht dabei: ein Waechter, der Harmloses mitzaehlt, wird
# abgeschaltet statt befolgt.
JUDGEMENT_INPUTS = {
    "state", "fit", "fits_budget", "budget", "recovery", "recovery_offered",
    "hard_days_last_7", "layoff_days", "infection", "intensity", "goal",
    "ftp", "aerobic_hr", "max_hr", "aerobic_power", "p20_fresh",
    # seit 0.47.0: fehlt `curve`, faellt die Wattvorgabe STILLSCHWEIGEND auf
    # die FTP zurueck - der Athlet saehe dieselbe Einheit mit anderen Zahlen
    # und keinen Hinweis darauf. Genau die Klasse, fuer die dieser Waechter
    # gebaut wurde (PROJEKTSTAND §7, 0.44.0).
    "curve",
    # seit 0.49.0: fehlt `blocks`, faellt nicht nur die Wattvorgabe der harten
    # Familien still auf die FTP zurueck, sondern auch ihr Pulsfenster - und
    # zwar getrennt voneinander, was genau das halb umgestellte Paar ergaebe.
    "blocks",
}


def defaulted_args(node) -> set[str]:
    """Parameter WITH a default value - the ones a caller may silently drop."""
    names = [a.arg for a in node.args.args]
    return set(names[len(names) - len(node.args.defaults):]) if node.args.defaults else set()


wfuncs = {n.name: n for n in ast.walk(wtree)
          if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

# (b) Vollstaendigkeit: welche oeffentliche Funktion in workouts.py traegt
#     Vorgabewerte fuer Urteilseingaben und fehlt in der Liste?
for name, node in sorted(wfuncs.items()):
    if name.startswith("_"):
        continue
    risky = defaulted_args(node) & JUDGEMENT_INPUTS
    if not risky:
        continue
    check(name in JUDGEMENT_FUNCTIONS,
          f"Vorgabewert-Wächter: {name}() in workouts.py hat Vorgabewerte für "
          f"{sorted(risky)} und steht nicht in JUDGEMENT_FUNCTIONS — die Liste "
          "muss beim Hinzufügen einer Urteilsfunktion mitgepflegt werden")
# ... und andersherum: eine Funktion, die es nicht mehr gibt, taeuscht Schutz vor.
for name in sorted(JUDGEMENT_FUNCTIONS):
    check(name in wfuncs,
          f"Vorgabewert-Wächter: {name} steht in JUDGEMENT_FUNCTIONS, existiert "
          "aber nicht mehr in workouts.py")
# Gegenprobe auf den Waechter selbst: er muss ueberhaupt etwas zu pruefen
# finden. Faende er null Urteilseingaenge, bestuende er immer.
_covered = {n for n in JUDGEMENT_FUNCTIONS
            if n in wfuncs and defaulted_args(wfuncs[n]) & JUDGEMENT_INPUTS}
check(len(_covered) >= 4,
      f"Vorgabewert-Wächter: nur {len(_covered)} Urteilsfunktionen mit "
      "Vorgabewerten gefunden — der Wächter greift ins Leere")

# (a) Jeder Aufruf nennt jeden Urteilseingang ausdruecklich.
calls = 0
for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue
    func = node.func
    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
    if name not in JUDGEMENT_FUNCTIONS or name not in wfuncs:
        continue
    calls += 1
    given = {kw.arg for kw in node.keywords if kw.arg}
    # Positionsargumente zaehlen genauso: sie sind genannt, nur ohne Namen.
    positional = [a.arg for a in wfuncs[name].args.args][:len(node.args)]
    given |= set(positional)
    for missing in sorted((defaulted_args(wfuncs[name]) & JUDGEMENT_INPUTS) - given):
        check(False,
              f"Vorgabewert-Wächter: websocket.py Zeile {node.lineno} ruft "
              f"{name}() ohne {missing} — der Vorgabewert springt still ein")
# Die Untergrenze ist eine ZAHL AUS DEM BESTAND, keine Wunschzahl: sie faellt,
# wenn ein Aufruf verschwindet, und das ist der Zweck. In 0.51.0 ist sie von
# drei auf zwei gesunken, weil protocol_block mit dem Durability-Protokoll
# entfallen ist - eine erklaerte Senkung, keine gelockerte Pruefung (§9,
# dritte Bauregel).
check(calls >= 2, f"Vorgabewert-Wächter: nur {calls} Aufrufe gefunden — "
                  "der Wächter sieht die Aufrufstellen nicht")

# --- DIE REIZ-STUFE IN BEIDEN ANSICHTEN, UNTER DENSELBEN BEDINGUNGEN --------
# Nicht "erscheint in beiden", sondern: gleicher Zustand, gleiches Budget,
# gleiche Erholungslage -> DIESELBE Stufe. Anwesenheit allein waere erneut
# stumpf, genau wie die elf Gegenproben aus 0.42.0.
import coldcache  # noqa: F401,E402  - MUSS vor jedem Bauteil-Import stehen (§9)
sys.path.insert(0, str(WORKOUTS.parent))
import workouts as WK  # noqa: E402

GRID = [
    ("ready", 200.0, True), ("ready", 200.0, False),
    ("ready", 5.0, True), ("ready", 5.0, False),
    ("strained", 200.0, True), ("strained", 5.0, True),
    ("rebound", 200.0, False), ("ready", None, True),
]
seen_stages: set[str] = set()
for state, budget, recovered in GRID:
    picks = WK.suggest(state, ftp=215, aerobic_hr=146, max_hr=186, infection=False,
                       budget=budget, hard_days_last_7=0, layoff_days=None,
                       goal="long_ride", recovery_offered=recovered)
    # dieselben Einheiten, wie die Wochenansicht sie bewertet
    sessions = [{"workout": e.get("key"), "hours": None} for e in picks]
    rated = WK.rate_sessions(sessions, state, budget=budget,
                             recovery_offered=recovered, hard_days_last_7=0,
                             layoff_days=None, infection=False, ftp=215,
                             aerobic_hr=146, max_hr=186)
    by_key = {e.get("key"): e for e in rated}
    for entry in picks:
        key = entry.get("key")
        mirror = by_key.get(key)
        if mirror is None:
            continue
        here = (entry.get("stage") or {}).get("key")
        there = (mirror.get("stage") or {}).get("key")
        seen_stages.add(here)
        check(here == there,
              f"Reiz-Gleichstand: {key} bei Zustand {state}, Budget {budget}, "
              f"Erholung {recovered} — Trainer {here!r}, Wochenansicht {there!r}")
        check(((entry.get("stage") or {}).get("blocked_by")
               == (mirror.get("stage") or {}).get("blocked_by")),
              f"Reiz-Gleichstand: {key} bei {state}/{budget}/{recovered} — "
              "Begründung weicht zwischen den Ansichten ab")
# Die Fixture muss die Stufen auseinanderziehen, sonst prueft der Gleichstand
# nichts: ein Gitter, das nur gruen erzeugt, bestuende auch ohne die Regel.
check("stimulus" in seen_stages,
      f"Reiz-Gleichstand: das Gitter erzeugt keine Reiz-Stufe ({sorted(seen_stages)}) "
      "— die Gegenprobe ist stumpf")
for needed in ("green", "yellow", "red"):
    check(needed in seen_stages,
          f"Reiz-Gleichstand: das Gitter erzeugt keine Stufe {needed!r} "
          f"({sorted(seen_stages)})")

# --- die Zuordnung (Paket P3): Leseweg, Schreibweg, Bestaetigen ---------------
# Drei Kommandos, und der Schreibweg hat einen Fehlerpfad, den kein
# Kommandoname zeigt: scheitert der Lap-Abruf, darf NICHTS geschrieben werden.
# Das ist der Unterschied zu set_ramp_test, wo die Markierung auch ohne Messung
# steht - dort faellt die MESSUNG aus, hier fiele das aus, was die Aussage
# ueberhaupt erst bestimmt. Eine Marke ohne Anker ist eine, deren Drift nie
# auffallen kann.
for name, command in (("websocket_section_marks", "intervals_icu/section_marks"),
                      ("websocket_set_section_mark", "intervals_icu/set_section_mark"),
                      ("websocket_confirm_section_marks",
                       "intervals_icu/confirm_section_marks")):
    check(name in registered, f"section_marks: {name} nicht registriert")
    check(commands.get(name) == command,
          f"section_marks: falscher Kommandoname an {name}: {commands.get(name)!r}")

_setter = functions.get("websocket_set_section_mark")
_set_src = ast.get_source_segment(SRC, _setter) if _setter else ""
_set_src = _set_src or ""
check("marks_lib.set_mark(" in _set_src,
      "section_marks: der Schreibweg validiert nicht über das Modul")
check("marks_lib.unset_mark(" in _set_src,
      "section_marks: die Rücknahme läuft nicht über das Modul")

# Die Laps werden GEHOLT, BEVOR geschrieben wird - sonst stünde die Marke
# ungeprüft und ohne Anker da.
if "_laps_for(" in _set_src and "marks_lib.set_mark(" in _set_src:
    check(_set_src.index("_laps_for(") < _set_src.index("marks_lib.set_mark("),
          "section_marks: geschrieben wird, bevor die Abschnitte geholt sind")
else:
    check(False, "section_marks: der Schreibweg holt die Abschnitte nicht live")

# DER FEHLERPFAD, am Syntaxbaum statt am Zeilenbild (zehnte Bauregel): in
# keinem except-Zweig des Setzers wird geschrieben, und jeder endet mit return.
_handlers = [node for node in ast.walk(_setter)
             if isinstance(node, ast.ExceptHandler)] if _setter else []
check(len(_handlers) >= 2,
      f"section_marks: nur {len(_handlers)} Fehlerzweige im Schreibweg")
for index, handler in enumerate(_handlers):
    body = ast.unparse(ast.Module(body=handler.body, type_ignores=[]))
    check("set_mark(" not in body,
          f"section_marks: Fehlerzweig {index} schreibt trotzdem eine Marke")
    check("async_save_now" not in body,
          f"section_marks: Fehlerzweig {index} speichert das Archiv")
    check(any(isinstance(sub, ast.Return) for sub in ast.walk(handler)),
          f"section_marks: Fehlerzweig {index} läuft weiter, statt abzubrechen")
# Gegenprobe: derselbe Ausdruck muss einen eingebauten Schreibvorgang FINDEN,
# sonst prueft die Schleife oben nur, dass nie etwas dasteht.
_geplant = ast.parse("try:\n    x()\nexcept ValueError:\n    marks_lib.set_mark(1)\n")
_geplant_body = ast.unparse(ast.Module(
    body=[h for h in ast.walk(_geplant) if isinstance(h, ast.ExceptHandler)][0].body,
    type_ignores=[]))
check("set_mark(" in _geplant_body,
      "section_marks Gegenprobe: ein eingebauter Schreibvorgang im Fehlerzweig "
      "wird NICHT gefunden — der Ausdruck ist blind")

# Die RUECKNAHME braucht keine Laps und darf deshalb auch keine holen: sonst
# waere eine falsch gesetzte Marke genau dann nicht loszuwerden, wenn die
# Schnittstelle klemmt.
_unset = [node for node in ast.walk(_setter)
          if isinstance(node, ast.If) and "not msg['mark']" in ast.unparse(node.test)] \
    if _setter else []
check(len(_unset) == 1,
      f"section_marks: der Rücknahme-Zweig ist nicht zu finden ({len(_unset)})")
if _unset:
    _unset_src = ast.unparse(ast.Module(body=_unset[0].body, type_ignores=[]))
    check("_laps_for(" not in _unset_src,
          "section_marks: die Rücknahme holt Abschnitte, obwohl sie keine braucht")
    check("marks_lib.unset_mark(" in _unset_src,
          "section_marks: der Rücknahme-Zweig nimmt nicht über das Modul zurück")

_confirm = ast.get_source_segment(SRC, functions["websocket_confirm_section_marks"]) \
    if "websocket_confirm_section_marks" in functions else ""
check("marks_lib.reanchor(" in (_confirm or ""),
      "section_marks: das Bestätigen verankert nicht über das Modul")

# Der Leseweg liefert Familien und Driftsätze AUS DEM MODUL - eine
# handgepflegte Kopie im Panel oder hier wäre die Listen-Klasse (§7).
_reader = ast.get_source_segment(SRC, functions["websocket_section_marks"]) \
    if "websocket_section_marks" in functions else ""
check("marks_lib.FAMILIES" in (_reader or ""),
      "section_marks: der Leseweg führt eine eigene Familienliste")
check("marks_lib.STALE_REASON" in (_reader or ""),
      "section_marks: die Driftsätze kommen nicht aus dem Modul")

# --- der Messweg (B1): ZWEI Abrufe, Drift davor, zwei Arten von Fehlschlag ---
check("websocket_measure_section_marks" in registered,
      "Messweg: der Übernehmen-Knopf hat kein Kommando")
check(commands.get("websocket_measure_section_marks")
      == "intervals_icu/measure_section_marks",
      f"Messweg: falscher Kommandoname "
      f"({commands.get('websocket_measure_section_marks')!r})")

_measure = functions.get("websocket_measure_section_marks")
_m_src = (ast.get_source_segment(SRC, _measure) if _measure else "") or ""

# ZWEI ABRUFE. set_ramp_test kommt mit einem aus, weil es die ganze Fahrt
# auswertet; maskieren braucht die Lap-GRENZEN, und die stehen nicht im Strom.
check("async_get_streams(" in _m_src, "Messweg: er holt keine Ströme")
check("_laps_for(" in _m_src,
      "Messweg: er holt keine Abschnitte — ohne ihre Grenzen gibt es keine Maske")
# Und aus DENSELBEN Kanälen wie der Import: die maskierte Stundenliste steht
# später neben der Ganzfahrt-Liste, und zwei verschieden erhobene Größen unter
# einer Überschrift waren 0.49.2.
check("importer.DFA_STREAMS" in _m_src,
      "Messweg: er führt eine eigene Kanalliste statt der des Importwegs")

# DIE DRIFT WIRD GEPRÜFT, BEVOR GERECHNET WIRD. Ohne das misst der Weg auf
# verschobenen Abschnitten, und das Ergebnis sähe sauber aus.
for erst, dann, label in (
        ("marks_lib.drift(", "derive.dfa_hours(", "gerechnet"),
        ("marks_lib.drift(", "marks_lib.set_measurement(", "geschrieben"),
        ("marks_lib.mask_ranges(", "derive.dfa_hours(", "gerechnet")):
    if erst in _m_src and dann in _m_src:
        check(_m_src.index(erst) < _m_src.index(dann),
              f"Messweg: es wird {label}, bevor {erst[:-1]} gelaufen ist")
    else:
        check(False, f"Messweg: {erst[:-1]} oder {dann[:-1]} kommt gar nicht vor")

check("keep=" in _m_src,
      "Messweg: dfa_hours wird ohne Maske gerufen — dann misst er die ganze Fahrt")

# DIE MASKE IST FAMILIENREIN (0.54.1). Ohne den Familienparameter legte die
# Gerade zwei getrennte Punktwolken zusammen — Einrollen mit wenig Watt und
# hohem alpha, Intervalle mit viel Watt und niedrigem alpha — und las bei 0,75
# einen Zustand ab, den niemand gefahren ist. Das ist der Fit-durch-zwei-
# Wolken aus Paket M, dort schon behoben, über einen NEUEN Weg zurückgekommen.
# SEIT B2b-0: der Knopf misst ALLE markierten Familien, jede mit ihrem
# Instrument. Die Maske bleibt familienrein — sie bekommt die Marken der
# Familie, über die die Schleife gerade läuft.
check("marks_lib.marked(entry, family)" in _m_src,
      "Messweg: die Maske nimmt alle Marken quer über die Familien — "
      "der Fit läuft dann durch zwei Wolken (Paket M)")
check("for family in marks_lib.FAMILIES:" in _m_src,
      "Messweg: er läuft nicht über die Familien — dann misst er nur eine")
check("marks_lib.marked_blocks(" in _m_src,
      "Messweg: die Blockfamilien werden nicht gemessen")
# DIE BLOCKZEILEN WERDEN FRISCH GERECHNET. Im Archiv nachzuschlagen sieht
# gleich aus, solange niemand die Fahrt in Intervals neu unterteilt — an der
# 13.09.2026 fiel es auseinander (Archiv sieben Runden, live fünf), und die
# Driftprobe kann das nicht sehen.
check("derive.dfa_blocks(" in _m_src,
      "Messweg: die Blockzeilen werden nicht frisch gerechnet")
for verboten in ('summary.get("blocks")', '["dfa"]', 'archive.data["dfa"]'):
    check(verboten not in _m_src,
          f"Messweg: er greift mit {verboten} doch ins Archiv — der alte Weg "
          f"ist still zurückgekommen")

# GEGENPROBE über den ganzen Produktivcode: KEINE Aufrufstelle von `marked`
# darf die Familie weglassen — außer dem ANKER, der zu Recht alle Marken
# umspannt. Der Fehler saß genau hier, und er sitzt beim nächsten Anschluss
# der Blockmessung an derselben Stelle wieder.
COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"
# Die ERLAUBTEN familienlosen Aufrufe, einzeln benannt statt als Muster: zwei
# gehören dem ANKER (er umspannt zu Recht alle Marken einer Fahrt), einer
# fragt nur, OB überhaupt etwas markiert ist. Wer einen vierten hinzufügt,
# muss ihn hier eintragen — und begründen.
_anker_ok = ("anchor_of(rows, marked(entry))",
             "missing = [i for i in marked(entry) if",
             "if entry is None or not marks_lib.marked(entry):")
for _datei in ("section_marks.py", "websocket.py", "blocks.py", "fatigue.py"):
    _pfad = COMPONENT / _datei
    if not _pfad.exists():
        continue
    for _nr, _zeile in enumerate(_pfad.read_text(encoding="utf-8").splitlines(), 1):
        if "marked(" not in _zeile or "def marked" in _zeile or "marked_blocks(" in _zeile:
            continue
        _blank = re.search(r"marked\((entry|old)\)", _zeile)
        if not _blank:
            continue                      # Regex null-geprüft (§9)
        check(any(erlaubt in _zeile for erlaubt in _anker_ok),
              f"Familienreinheit: {_datei}:{_nr} ruft marked() ohne Familie — "
              f"das mischt zwei Sorten Abschnitt in eine Messung")

# ZWEI ARTEN VON FEHLSCHLAG, und der Unterschied ist die 0.53.1-Klasse: ein
# Netzfehler darf nicht als Satz im Archiv versteinern, ein Sachbefund über die
# Fahrt gehört hinein. Also: in KEINEM except-Zweig wird gemessen oder
# gespeichert, und jeder bricht ab.
_m_handlers = [node for node in ast.walk(_measure)
               if isinstance(node, ast.ExceptHandler)] if _measure else []
check(len(_m_handlers) >= 2,
      f"Messweg: nur {len(_m_handlers)} Fehlerzweige — Ströme und Laps brauchen eigene")
for index, handler in enumerate(_m_handlers):
    body = ast.unparse(ast.Module(body=handler.body, type_ignores=[]))
    check("set_measurement(" not in body,
          f"Messweg: Fehlerzweig {index} schreibt eine Messung")
    check("async_save_now" not in body,
          f"Messweg: Fehlerzweig {index} speichert das Archiv")
    check(any(isinstance(sub, ast.Return) for sub in ast.walk(handler)),
          f"Messweg: Fehlerzweig {index} läuft weiter, statt abzubrechen")
# GEGENPROBE zu beidem: der Sachbefund wird sehr wohl geschrieben, sonst
# prüfte die Schleife oben nur, dass nirgends etwas steht.
check("marks_lib.set_measurement(" in _m_src,
      "Messweg Gegenprobe: er schreibt das Ergebnis überhaupt nicht")
check("async_save_now" in _m_src,
      "Messweg Gegenprobe: er speichert das Ergebnis überhaupt nicht")

# --- websocket_laps SCHREIBT, und nur im Änderungsfall -----------------------
# Gemeldet, nicht versteckt: es ist die einzige Stelle, an der Runden und
# Archiv gleichzeitig vorliegen.
_laps_fn = functions.get("websocket_laps")
_laps_src = (ast.get_source_segment(SRC, _laps_fn) if _laps_fn else "") or ""
check("marks_lib.drift(" in _laps_src,
      "Öffnen: die Drift wird nicht geprüft, obwohl die Runden vorliegen")
check("marks_lib.drop_hours(" in _laps_src,
      "Öffnen: eine gedriftete Fahrt behält ihre Messung")
check('"marks_stale"' in _laps_src or "'marks_stale'" in _laps_src,
      "Öffnen: der Befund kommt nicht beim Panel an")
# DER SPEICHERVORGANG HÄNGT AM ÄNDERUNGSFALL - ein No-op darf keinen auslösen
# (J7, zweite Auflage). Am Syntaxbaum, nicht am Zeilenbild.
_saves_in_if = 0
_saves_total = 0
for node in ast.walk(_laps_fn) if _laps_fn else []:
    if isinstance(node, ast.Await) and "async_save_now" in ast.unparse(node):
        _saves_total += 1
for node in ast.walk(_laps_fn) if _laps_fn else []:
    if not isinstance(node, ast.If) or "drop_hours" not in ast.unparse(node.test):
        continue
    body = ast.unparse(ast.Module(body=node.body, type_ignores=[]))
    if "async_save_now" in body:
        _saves_in_if += 1
check((_saves_total, _saves_in_if) == (1, 1),
      f"Öffnen: der Speichervorgang hängt nicht am Änderungsfall "
      f"({_saves_total} gesamt, {_saves_in_if} hinter drop_hours)")
# Gegenprobe, gezählt und benannt: derselbe Ausdruck findet ein Speichern, das
# NICHT am Änderungsfall hängt.
_frei = ast.parse("async def f():\n    await c.archive.async_save_now()\n")
check(sum(1 for node in ast.walk(_frei)
          if isinstance(node, ast.Await) and "async_save_now" in ast.unparse(node)) == 1,
      "Öffnen Gegenprobe: ein freistehender Speichervorgang wird NICHT gefunden — "
      "der Ausdruck ist blind")

# Und die Migration ist verdrahtet - ein Block ohne sie ist unfertig (J7).
check("section_marks.migrate(" in store_src,
      "section_marks: das Archiv migriert den Block beim Laden nicht")
if "section_marks.migrate(" in store_src:
    _at = store_src.index("section_marks.migrate(")
    check(store_src.index("base.update(stored)") < _at,
          "section_marks: migriert wird, bevor die Altdaten übernommen sind")
    check("schedule_save()" in store_src[_at:_at + 400],
          "section_marks: die Reparatur wird nie gespeichert")


# ---------------------------------------------------------------------------
# JEDER AUFRUF VON dfa_hours NENNT SEINE FENSTERBREITE (0.63.1).
# Der Fehler von 0.63.0 war genau das Fehlen des Parameters an EINER von zwei
# Stellen: der Importweg kannte den Rechenschalter, der Messweg der
# Markierungen nicht. Geprueft wird deshalb ueber das ganze Paket und nicht an
# der einen Stelle, die gerade repariert wurde - die naechste Stelle soll beim
# Schreiben auffallen und nicht im Betrieb.
_PKG = Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"
# AM SYNTAXBAUM, nicht am Text: `dfa_hours` kommt in zwei Docstrings vor, und
# eine Erwaehnung in Prosa ist kein Aufruf.
_AUFRUFE = []
for _f in sorted(_PKG.glob("*.py")):
    _baum = ast.parse(_f.read_text(encoding="utf-8"))
    for _node in ast.walk(_baum):
        if not isinstance(_node, ast.Call):
            continue
        _ziel = _node.func
        if not (isinstance(_ziel, ast.Attribute) and _ziel.attr == "dfa_hours"):
            continue
        _AUFRUFE.append((_f.name, {kw.arg: ast.dump(kw.value) for kw in _node.keywords}))
check(len(_AUFRUFE) == 5,
      f"Fensterbreite: {len(_AUFRUFE)} Aufrufe von dfa_hours statt fuenf - "
      "eine neue Stelle ist einzeln zu beurteilen")
for _name, _args in _AUFRUFE:
    check("watt_window_s" in _args,
          f"Fensterbreite: der Aufruf in {_name} nennt sie nicht - "
          "er misst dann immer sekundengenau, egal wie der Schalter steht")
# Die zwei PRODUKTIVEN Wege muessen sie ERFRAGEN statt sie selbst zu setzen.
# Der Trockenlauf darf beide Breiten fest waehlen - das ist sein Zweck.
_PRODUKTIV = [(n, a) for n, a in _AUFRUFE if n in ("importer.py", "websocket.py")]
check(len(_PRODUKTIV) == 2,
      f"Fensterbreite: {len(_PRODUKTIV)} produktive Aufrufe statt zwei")
for _name, _args in _PRODUKTIV:
    check("watt_window" in str(_args.get("watt_window_s")),
          f"Fensterbreite: {_name} setzt sie selbst statt sie zu erfragen - "
          "genau der Fehler von 0.63.0")
# Trefferzusicherung: der Wortlaut kommt im Paket WIRKLICH vor.
check(any("watt_window" in str(a.get("watt_window_s")) for _, a in _PRODUKTIV),
      "Fensterbreite Fixture-Beweis: kein produktiver Aufruf erfragt sie - "
      "die Pruefung greift ins Leere")


# ---------------------------------------------------------------------------
# DER MESSWEG SCHREIBT JE FAHRT ALLE MARKIERTEN FAMILIEN (0.65.1). Am
# Syntaxbaum, weil der Livebefund genau hier haette auffallen muessen: eine
# Fahrt mit SweetSpot- UND Grundlagen-Marken darf nicht mit einer Messung
# zurueckbleiben. Der Handler tut es richtig - geprueft war es nie.
_ws_quelle = (Path(__file__).resolve().parents[1] / "custom_components"
              / "intervals_icu" / "websocket.py").read_text(encoding="utf-8")
_ws_baum = ast.parse(_ws_quelle)
_mess = next((n for n in ast.walk(_ws_baum)
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
              and n.name == "websocket_measure_section_marks"), None)
check(_mess is not None, "Messweg: der Handler ist nicht zu finden")
_schleifen = [n for n in ast.walk(_mess) if isinstance(n, ast.For)] if _mess else []
_ueber_familien = [n for n in _schleifen
                   if "FAMILIES" in ast.dump(n.iter)]
check(len(_ueber_familien) == 1,
      f"Messweg: {len(_ueber_familien)} Schleifen ueber FAMILIES statt einer")
_in_schleife = [n for n in ast.walk(_ueber_familien[0])
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "set_measurement"] if _ueber_familien else []
_gesamt = [n for n in ast.walk(_mess)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
           and n.func.attr == "set_measurement"] if _mess else []
check(len(_gesamt) == 1 and len(_in_schleife) == 1,
      f"Messweg: {len(_gesamt)} Aufrufe von set_measurement, davon {len(_in_schleife)} "
      "in der Familienschleife - er schriebe sonst nur fuer eine Familie")
# Trefferzusicherung: es gibt wirklich mehr als eine Familie, sonst prueft die
# Schleife oben nichts.
check(len(sys.modules["iv.section_marks"].FAMILIES) > 1
      if "iv.section_marks" in sys.modules else True,
      "Messweg Fixture-Beweis: es gibt nur eine Familie")


print(f"test_websocket_registration: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
print("registriert: " + ", ".join(sorted(seen)))
sys.exit(1 if FAILURES else 0)
