"""Reconciliation against Intervals: the three locks, and the handler around them.

Two levels are checked here, because the failure modes live on both:

* ``reconcile.plan()/apply()`` - what may be removed at all,
* ``websocket_reconcile`` - the state of the system around it (import in
  flight, history never walked, a second answer between dialog and click).

The handler is exercised for real, not grepped: Home Assistant, voluptuous and
aiohttp are stubbed to the few names the module touches, so the test still
needs neither a running instance nor a browser (PROJEKTSTAND §9).
"""

import asyncio
import importlib.util
import json
import sys
import types
from datetime import date, timedelta
from pathlib import Path

COMP = Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"

FAILURES: list[str] = []
CHECKS = 0


def check(label, condition):
    global CHECKS
    CHECKS += 1
    print(f"{'PASS' if condition else 'FAIL'}  {label}")
    if not condition:
        FAILURES.append(label)


def eq(label, got, expected):
    global CHECKS
    CHECKS += 1
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {got!r}" + ("" if ok else f"  (erwartet {expected!r})"))
    if not ok:
        FAILURES.append(label)


# --- stubs: only the names the modules actually import ------------------------
def _stub(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _identity(obj):
    return obj


def _decorator(*args, **kwargs):
    return _identity


class _Any:
    def __init__(self, *args, **kwargs):
        pass


_stub("voluptuous", Required=_identity, Optional=_identity, Any=_Any, Schema=_identity,
      Coerce=_identity, In=_identity, All=_Any, Range=_Any, Clamp=_Any, Length=_Any,
      Lower=_identity, Maybe=_identity)
_stub("aiohttp", BasicAuth=object, ClientError=Exception, ClientResponse=object,
      ClientSession=object)

ha = _stub("homeassistant")
_stub("homeassistant.core", HomeAssistant=object, callback=_identity)
_stub("homeassistant.components")
_stub(
    "homeassistant.components.websocket_api",
    websocket_command=_decorator,
    async_response=_identity,
    async_register_command=lambda hass, handler: None,
)
_dt = _stub("homeassistant.util.dt", now=lambda: date.today())
_stub("homeassistant.util", dt=_dt)
_stub("homeassistant.helpers")
_stub("homeassistant.helpers.storage", Store=object)

_pkg = types.ModuleType("iv")
_pkg.__path__ = [str(COMP)]
_pkg.__package__ = "iv"
sys.modules["iv"] = _pkg


def _load(name):
    spec = importlib.util.spec_from_file_location(f"iv.{name}", COMP / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"iv.{name}"] = module
    spec.loader.exec_module(module)
    return module


reconcile = _load("reconcile")
importer = _load("importer")
ws = _load("websocket")


# --- fixture: a small replay of the live archive ------------------------------
# 40 activities across 2025-06-01 .. 2026-09-10, every third with a DFA
# summary, two Strava placeholders in `unavailable`, and one DFA orphan whose
# activity is already gone.
OLDEST = date(2025, 6, 1)
ORPHAN = "i-orphan"
UNAVAILABLE = ["i-strava-1", "i-strava-2"]


def build_archive():
    data = importer.empty_data("i1")
    data["full_import_done"] = True
    day = OLDEST
    for index in range(40):
        key = f"i{1000 + index}"
        data["activities"][key] = {
            "id": key,
            "start_date_local": f"{day.isoformat()}T17:32:00",
            "type": "Ride" if index % 2 else "Run",
            "name": f"Einheit {index}",
            "icu_training_load": 50 + index,
        }
        if index % 3 == 0:
            data["dfa"][key] = {"threshold": 140 + index}
        day += timedelta(days=12)
    data["unavailable"] = list(UNAVAILABLE)
    data["dfa"][ORPHAN] = {"threshold": 133}
    return data


def remote_rows(data, drop=(), extra_ids=()):
    """The answer Intervals would give for the whole history."""
    rows = [
        {"id": key, "start_date_local": activity["start_date_local"]}
        for key, activity in data["activities"].items()
        if key not in drop
    ]
    rows += [{"id": key, "start_date_local": "2025-07-01T08:00:00"}
             for key in list(data["unavailable"]) + [ORPHAN] if key not in drop]
    rows += [{"id": key, "start_date_local": "2026-01-01T08:00:00"} for key in extra_ids]
    return rows


NEWEST = date(2026, 9, 13)
BASE = build_archive()
ALL_KEYS = sorted(BASE["activities"])
LAST_DAY = date.fromisoformat(BASE["activities"][ALL_KEYS[-1]]["start_date_local"][:10])
eq("Fixture: Aktivitäten", len(BASE["activities"]), 40)
eq("Fixture: DFA-Zusammenfassungen inkl. Waise", len(BASE["dfa"]), 15)
eq("Fixture: unavailable", len(BASE["unavailable"]), 2)
check("Fixture: die Waise hängt an keiner Aktivität", ORPHAN not in BASE["activities"])


def fingerprint(data):
    return json.dumps(data, sort_keys=True, default=str)


# --- the fixture must be able to tell two cases apart -------------------------
# Paket A, Muster 2: a prescribed check is only a check once the fixture makes
# the two outcomes distinguishable.
gone = ALL_KEYS[7]
report_clean = reconcile.plan(build_archive(), remote_rows(BASE), OLDEST, NEWEST)
report_gap = reconcile.plan(build_archive(), remote_rows(BASE, drop={gone}), OLDEST, NEWEST)
eq("Fixture-Beweis: Bestand ohne Abweichung meldet nichts", len(report_clean["missing"]), 0)
eq("Fixture-Beweis: Bestand mit Abweichung meldet genau eine", len(report_gap["missing"]), 1)
check("Fixture-Beweis: die beiden Befunde unterscheiden sich",
      report_clean["missing"] != report_gap["missing"])
check("Fixture-Beweis: beide Läufe sahen dieselbe Menge an Kandidaten",
      report_clean["checked"] == report_gap["checked"] and report_clean["checked"] > 0)


# --- one missing id disappears from all three sites, and nothing else ---------
data = build_archive()
before = fingerprint(data)
target = ALL_KEYS[0]  # index 0 -> has a DFA summary
check("Aufräumstellen: die Ziel-Einheit hat eine DFA-Zusammenfassung", target in data["dfa"])
report = reconcile.plan(data, remote_rows(data, drop={target}), OLDEST, NEWEST)
eq("Abgleich: genau eine Einheit fehlt drüben", [item["id"] for item in report["missing"]], [target])
eq("Abgleich: sie ist freigegeben", report["removable"], [target])
eq("Abgleich: der Befund trägt das Datum aus dem Archiv", report["missing"][0]["date"], OLDEST.isoformat())
eq("Abgleich: der Befund trägt den Namen aus dem Archiv", report["missing"][0]["name"], "Einheit 0")
check("Abgleich: der Befund meldet die DFA-Zusammenfassung mit", report["missing"][0]["dfa"] is True)
eq("Abgleich: plan() allein verändert nichts", fingerprint(data), before)

removed = reconcile.apply(data, report["removable"])
eq("Aufräumstellen: aus activities entfernt", removed["activities"], 1)
eq("Aufräumstellen: aus dfa entfernt", removed["dfa"], 1)
eq("Aufräumstellen: unavailable unberührt", removed["unavailable"], 0)
check("Aufräumstellen: die ID ist aus activities weg", target not in data["activities"])
check("Aufräumstellen: die ID ist aus dfa weg", target not in data["dfa"])
eq("Aufräumstellen: keine andere Einheit angefasst", len(data["activities"]), 39)
eq("Aufräumstellen: keine andere DFA-Zusammenfassung angefasst", len(data["dfa"]), 14)
eq("Aufräumstellen: unavailable steht unverändert", data["unavailable"], UNAVAILABLE)
stats = importer.archive_stats(data)
eq("Aufräumstellen: der Kopfzähler folgt", stats["activities"], 39)


# --- lock 1: an answer that cannot be vouched for aborts ----------------------
for label, rows in (
    ("kein Datensatz", {"activities": []}),
    ("Zeile ist kein Datensatz", [{"id": "i1"}, "kaputt"]),
    ("Zeile ohne id", [{"id": "i1"}, {"start_date_local": "2026-01-01T00:00:00"}]),
    ("Zeile mit leerer id", [{"id": ""}]),
):
    data = build_archive()
    before = fingerprint(data)
    raised = False
    try:
        reconcile.plan(data, rows, OLDEST, NEWEST)
    except ValueError:
        raised = True
    check(f"Sperre 1: {label} bricht ab", raised)
    eq(f"Sperre 1: {label} lässt den Bestand bit-identisch", fingerprint(data), before)

# The importer may skip a malformed row - the reconciliation may not. Same
# input, two deliberately different verdicts.
skipped = importer.merge_activities(build_archive(), [{"start_date_local": "x"}])
eq("Sperre 1: der Importer überspringt dieselbe Zeile weiterhin still", skipped, 0)


# --- lock 2: only inside the fetched window -----------------------------------
data = build_archive()
inside, outside = ALL_KEYS[5], ALL_KEYS[0]
narrow_oldest = date.fromisoformat(data["activities"][ALL_KEYS[3]]["start_date_local"][:10])
report = reconcile.plan(
    data, remote_rows(data, drop={inside, outside}), narrow_oldest, NEWEST)
ids = [item["id"] for item in report["missing"]]
check("Sperre 2: die Einheit im Fenster wird gemeldet", inside in ids)
check("Sperre 2: die Einheit vor dem Fenster wird nicht gemeldet", outside not in ids)
check("Sperre 2: ein Teilfenster gilt nicht als volle Historie", report["full_history"] is False)
reconcile.apply(data, report["removable"])
check("Sperre 2: die Einheit vor dem Fenster steht noch im Archiv", outside in data["activities"])

# Sharpened after a counter-check that did NOT bite: above, the placeholders
# and the orphan are still present on the Intervals side, so leaving them
# alone proves nothing about the window rule. They have to be missing over
# there for the difference to show - the fixture must tell the two cases
# apart (Paket A, Muster 2).
dateless = set(UNAVAILABLE) | {ORPHAN}
narrow = build_archive()
report = reconcile.plan(
    narrow, remote_rows(narrow, drop={inside} | dateless), narrow_oldest, NEWEST)
eq("Sperre 2: im Teilfenster wird keine datumslose Leiche gemeldet",
   [item["id"] for item in report["missing"]], [inside])
reconcile.apply(narrow, report["removable"])
eq("Sperre 2: unavailable bleibt im Teilfenster unangetastet", narrow["unavailable"], UNAVAILABLE)
check("Sperre 2: die DFA-Waise bleibt im Teilfenster stehen", ORPHAN in narrow["dfa"])

# ...and the same archive with the same gaps over the FULL window does clear
# them - two runs, two outcomes, so the rule is what makes the difference.
wide = build_archive()
wide_report = reconcile.plan(wide, remote_rows(wide, drop={inside} | dateless), OLDEST, NEWEST)
eq("Sperre 2: dieselben Lücken im Vollfenster werden gemeldet", len(wide_report["missing"]), 4)
check("Sperre 2: Teilfenster und Vollfenster kommen zu verschiedenen Ergebnissen",
      len(wide_report["missing"]) != len(report["missing"]))

# The bounds themselves belong to the window - an activity recorded at 17:32
# on the last day must not fall out because its timestamp carries a time.
edge = reconcile.plan(build_archive(), remote_rows(BASE, drop={ALL_KEYS[-1]}), OLDEST, LAST_DAY)
eq("Sperre 2: der Randtag zählt zum Fenster", [i["id"] for i in edge["missing"]], [ALL_KEYS[-1]])
check("Sperre 2: Zeitstempel mit Uhrzeit werden auf den Tag gekürzt",
      reconcile.in_window(reconcile._day("2026-09-13T23:50:00"), OLDEST, date(2026, 9, 13)))
check("Sperre 2: eine Einheit ohne lesbares Datum liegt nie im Fenster",
      reconcile.in_window(reconcile._day(None), OLDEST, NEWEST) is False)

# ...and an unreadable date anywhere means the window is not provably complete.
broken = build_archive()
broken["activities"][ALL_KEYS[2]]["start_date_local"] = None
check("Sperre 2: ein unlesbares Datum im Archiv verhindert den Vollabgleich",
      reconcile.covers_history(broken, OLDEST, NEWEST) is False)
check("Sperre 2: der vollständige Bestand gilt als volle Historie",
      reconcile.covers_history(build_archive(), OLDEST, NEWEST) is True)


# --- the two dateless sites, only on a full sweep ------------------------------
data = build_archive()
report = reconcile.plan(data, remote_rows(data, drop=set(UNAVAILABLE) | {ORPHAN}), OLDEST, NEWEST)
kinds = {item["id"]: item["kind"] for item in report["missing"]}
eq("Vollabgleich: alle drei datumslosen Leichen werden gemeldet", len(kinds), 3)
eq("Vollabgleich: der Platzhalter wird als solcher benannt", kinds[UNAVAILABLE[0]], "unavailable")
eq("Vollabgleich: die DFA-Waise wird als solche benannt", kinds[ORPHAN], "dfa")
removed = reconcile.apply(data, report["removable"])
eq("Vollabgleich: aus unavailable entfernt", removed["unavailable"], 2)
eq("Vollabgleich: die Waise ist aus dfa weg", ORPHAN in data["dfa"], False)
eq("Vollabgleich: unavailable ist leer", data["unavailable"], [])
eq("Vollabgleich: keine Aktivität dabei verloren", len(data["activities"]), 40)


# --- lock 3: the cap ----------------------------------------------------------
half = set(ALL_KEYS[:20])
data = build_archive()
before = fingerprint(data)
report = reconcile.plan(data, remote_rows(data, drop=half), OLDEST, NEWEST)
check("Sperre 3: die Hälfte fehlt, die Deckelung greift", report["capped"] is True)
eq("Sperre 3: nichts ist freigegeben", report["removable"], [])
eq("Sperre 3: gemeldet wird trotzdem alles", len(report["missing"]), 20)
check("Sperre 3: der Anteil wird beziffert", report["share"] > 0.20)
eq("Sperre 3: apply() ohne Freigabe verändert nichts", fingerprint(data), before)

# The cap counts the placeholders too - otherwise a fetch that silently drops
# every Strava stub could take the whole `unavailable` list with it.
eq("Sperre 3: unavailable zählt in den Nenner", report["checked"], 43)

# Just under the line the sweep still runs: the cap is a cap, not a freeze.
few = set(ALL_KEYS[:8])  # 8 of 43 = 18.6 %
data = build_archive()
report = reconcile.plan(data, remote_rows(data, drop=few), OLDEST, NEWEST)
check("Sperre 3: knapp unter der Grenze wird abgeglichen", report["capped"] is False)
eq("Sperre 3: knapp unter der Grenze sind alle freigegeben", len(report["removable"]), 8)

# An empty window has nothing to be a share of - and nothing to lose either.
empty = importer.empty_data("i1")
empty["full_import_done"] = True
report = reconcile.plan(empty, [], OLDEST, NEWEST)
eq("Sperre 3: leeres Fenster teilt nicht durch null", report["share"], 0.0)
eq("Sperre 3: leeres Fenster meldet nichts", report["missing"], [])


# --- the no-op case -----------------------------------------------------------
data = build_archive()
before = fingerprint(data)
report = reconcile.plan(data, remote_rows(data), OLDEST, NEWEST)
eq("No-op: kein Befund", report["missing"], [])
eq("No-op: nichts freigegeben", report["removable"], [])
removed = reconcile.apply(data, report["removable"])
eq("No-op: apply() meldet keine Entfernung", removed, {"activities": 0, "dfa": 0, "unavailable": 0})
check("No-op: changed() ist falsch", reconcile.changed(removed) is False)
eq("No-op: der Bestand ist bit-identisch", fingerprint(data), before)

# Unknown ids are not an instruction to delete something else.
data = build_archive()
before = fingerprint(data)
removed = reconcile.apply(data, ["gibt-es-nicht"])
check("apply(): unbekannte IDs verändern nichts", reconcile.changed(removed) is False)
eq("apply(): der Bestand bleibt bit-identisch", fingerprint(data), before)

# Extra activities on the Intervals side are not our business - the direction
# is one-way, and nothing here is ever sent over.
data = build_archive()
report = reconcile.plan(data, remote_rows(data, extra_ids=["i-neu-1", "i-neu-2"]), OLDEST, NEWEST)
eq("Einbahnstraße: fremde Einheiten erzeugen keinen Befund", report["missing"], [])
eq("Einbahnstraße: sie werden nur gezählt", report["remote"], 45)


# --- the handler around the locks ---------------------------------------------
class FakeConn:
    def __init__(self):
        self.results = []
        self.errors = []

    def send_result(self, mid, payload):
        self.results.append(payload)

    def send_error(self, mid, code, message):
        self.errors.append((code, message))


class FakeArchive:
    def __init__(self, data):
        self.data = data
        self.saves = 0

    async def async_save_now(self):
        self.saves += 1


class FakeClient:
    def __init__(self, rows):
        self._rows = rows
        self.calls = []

    async def async_get_activities(self, oldest, newest, fields=None):
        self.calls.append((oldest, newest, fields))
        if isinstance(self._rows, Exception):
            raise self._rows
        return self._rows


class FakeCoordinator:
    def __init__(self, data, rows, import_running=False):
        self.archive = FakeArchive(data)
        self.client = FakeClient(rows)
        self.import_running = import_running
        self.listeners = 0

    def history_start(self):
        return OLDEST

    def async_update_listeners(self):
        self.listeners += 1


def run(coordinator, msg=None):
    conn = FakeConn()
    ws._pick = lambda hass, athlete_id: coordinator
    asyncio.run(ws.websocket_reconcile(None, conn, dict({"id": 1}, **(msg or {}))))
    return conn


eq("Handler: der Abruf nimmt die schlanke Feldliste",
   reconcile.RECONCILE_FIELDS, ("id", "start_date_local"))

# preview: reports, changes nothing, saves nothing
data = build_archive()
before = fingerprint(data)
coordinator = FakeCoordinator(data, remote_rows(data, drop={ALL_KEYS[1]}))
conn = run(coordinator)
eq("Handler: die Vorschau antwortet ohne Fehler", conn.errors, [])
eq("Handler: die Vorschau meldet den Befund", [i["id"] for i in conn.results[0]["missing"]], [ALL_KEYS[1]])
check("Handler: die Vorschau ist als solche gekennzeichnet", conn.results[0]["applied"] is False)
eq("Handler: die Vorschau verändert den Bestand nicht", fingerprint(data), before)
eq("Handler: die Vorschau speichert nicht", coordinator.archive.saves, 0)
eq("Handler: der Abruf fragt das volle Fenster ab", coordinator.client.calls[0][0], OLDEST)
eq("Handler: der Abruf trimmt serverseitig", coordinator.client.calls[0][2], reconcile.RECONCILE_FIELDS)

# execution on confirmation
data = build_archive()
coordinator = FakeCoordinator(data, remote_rows(data, drop={ALL_KEYS[1]}))
conn = run(coordinator, {"confirm": [ALL_KEYS[1]]})
eq("Handler: der Vollzug antwortet ohne Fehler", conn.errors, [])
check("Handler: der Vollzug ist als solcher gekennzeichnet", conn.results[0]["applied"] is True)
eq("Handler: der Vollzug entfernt genau eine Einheit", conn.results[0]["removed"]["activities"], 1)
check("Handler: die Einheit ist aus dem Archiv weg", ALL_KEYS[1] not in data["activities"])
eq("Handler: der Vollzug speichert genau einmal", coordinator.archive.saves, 1)
eq("Handler: der Vollzug meldet die neuen Kopfzahlen", conn.results[0]["stats"]["activities"], 39)
eq("Handler: die Anzeige wird aufgefrischt", coordinator.listeners, 1)

# lock 1 at handler level: the fetch throws
data = build_archive()
before = fingerprint(data)
coordinator = FakeCoordinator(data, TimeoutError("Zeitüberschreitung"))
conn = run(coordinator, {"confirm": [ALL_KEYS[1]]})
eq("Sperre 1 (Handler): der Fehler wird gemeldet", [code for code, _ in conn.errors], ["fetch_failed"])
eq("Sperre 1 (Handler): es wird nichts beantwortet, was nach Vollzug aussieht", conn.results, [])
eq("Sperre 1 (Handler): der Bestand ist bit-identisch", fingerprint(data), before)
eq("Sperre 1 (Handler): es wurde nicht gespeichert", coordinator.archive.saves, 0)

# lock 1 at handler level: the answer is malformed
data = build_archive()
before = fingerprint(data)
coordinator = FakeCoordinator(data, [{"id": "i1000"}, {"start_date_local": "2026-01-01"}])
conn = run(coordinator, {"confirm": [ALL_KEYS[1]]})
eq("Sperre 1 (Handler): die kaputte Antwort wird benannt", [code for code, _ in conn.errors], ["bad_response"])
eq("Sperre 1 (Handler): kaputte Antwort lässt den Bestand bit-identisch", fingerprint(data), before)

# lock 3 at handler level
data = build_archive()
before = fingerprint(data)
coordinator = FakeCoordinator(data, remote_rows(data, drop=half))
conn = run(coordinator, {"confirm": sorted(half)})
check("Sperre 3 (Handler): der Vollzug wird verweigert", conn.results[0]["applied"] is False)
check("Sperre 3 (Handler): die Deckelung wird gemeldet", conn.results[0]["capped"] is True)
eq("Sperre 3 (Handler): der Bestand ist bit-identisch", fingerprint(data), before)
eq("Sperre 3 (Handler): es wurde nicht gespeichert", coordinator.archive.saves, 0)

# a second answer between dialog and click
data = build_archive()
coordinator = FakeCoordinator(data, remote_rows(data, drop={ALL_KEYS[2]}))
conn = run(coordinator, {"confirm": [ALL_KEYS[2], ALL_KEYS[3]]})
check("Zwischenstand: abweichende Bestätigung vollzieht nichts", conn.results[0]["applied"] is False)
check("Zwischenstand: die Abweichung wird benannt", conn.results[0]["stale"] is True)
check("Zwischenstand: die bestätigte Einheit steht noch da", ALL_KEYS[2] in data["activities"])
eq("Zwischenstand: es wurde nicht gespeichert", coordinator.archive.saves, 0)

# no-op through the handler: nothing removed, nothing saved
data = build_archive()
coordinator = FakeCoordinator(data, remote_rows(data))
conn = run(coordinator, {"confirm": []})
check("No-op (Handler): der Lauf gilt als vollzogen", conn.results[0]["applied"] is True)
eq("No-op (Handler): nichts entfernt", conn.results[0]["removed"],
   {"activities": 0, "dfa": 0, "unavailable": 0})
eq("No-op (Handler): kein Speichervorgang", coordinator.archive.saves, 0)
eq("No-op (Handler): keine Auffrischung", coordinator.listeners, 0)

# an import in flight
data = build_archive()
coordinator = FakeCoordinator(data, remote_rows(data, drop={ALL_KEYS[1]}), import_running=True)
conn = run(coordinator, {"confirm": [ALL_KEYS[1]]})
eq("Laufender Import: der Abgleich wird verweigert", [code for code, _ in conn.errors], ["busy"])
eq("Laufender Import: es wurde gar nicht erst abgerufen", coordinator.client.calls, [])

# history never walked
data = build_archive()
data["full_import_done"] = False
coordinator = FakeCoordinator(data, remote_rows(data, drop={ALL_KEYS[1]}))
conn = run(coordinator, {"confirm": [ALL_KEYS[1]]})
eq("Ohne Vollimport: der Abgleich wird verweigert", [code for code, _ in conn.errors], ["not_ready"])
eq("Ohne Vollimport: es wurde gar nicht erst abgerufen", coordinator.client.calls, [])


# --- the border: no delete operation anywhere ---------------------------------
ws_source = (COMP / "websocket.py").read_text(encoding="utf-8")
panel_source = (COMP / "frontend" / "intervals-panel.js").read_text(encoding="utf-8")
reconcile_source = (COMP / "reconcile.py").read_text(encoding="utf-8")
commands = {line.split('"')[3] for line in ws_source.splitlines() if 'vol.Required("type")' in line}
check("Grenze: es gibt keinen Befehl zum Löschen einer Aktivität",
      not any("delete" in name or "remove_activity" in name for name in commands))
check("Grenze: der Abgleich ist registriert", "intervals_icu/reconcile" in commands)
check("Grenze: das Panel kennt keinen Löschbefehl",
      '_ws("delete' not in panel_source and "activity_delete" not in panel_source)
check("Grenze: der Abgleich schickt nichts nach Intervals",
      "async_create_event" not in reconcile_source and "method=" not in reconcile_source)
check("Grenze: apply() ist nur über plan() erreichbar",
      ws_source.index("reconcile_lib.plan(") < ws_source.index("reconcile_lib.apply("))

print(f"test_reconcile: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
sys.exit(1 if FAILURES else 0)
