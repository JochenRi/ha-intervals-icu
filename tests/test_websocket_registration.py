"""The websocket registration, checked without starting Home Assistant.

0.9.4 shipped a handler inserted between another handler's decorators and its
`def`. The decorators then applied to the new function and the old one went
out bare, Home Assistant refused to register it, and the whole integration
failed to set up - no entities, no panel, nothing. A single misplaced block.

This reads the module as a syntax tree, so it needs neither HA nor a running
event loop, and it fails on exactly that class of mistake.
"""

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
        found = re.search(r"['\"]intervals_icu/([a-z_]+)['\"]", text)
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

print(f"test_websocket_registration: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
print("registriert: " + ", ".join(sorted(seen)))
sys.exit(1 if FAILURES else 0)
