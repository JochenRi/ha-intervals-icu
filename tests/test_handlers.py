"""Handler am echten Aufruf: der Schreibweg nach Intervals und die Saetze nach Schalterstellung.

Warum eine eigene Datei: die Befunde aus 0.56.0 sassen nicht in einer Rechnung,
sondern im HANDLER um sie herum - und ein Syntaxbaum-Waechter sieht nicht, was
ein Handler zur Laufzeit an welches Bauteil weiterreicht.

* A4 - `plan_workout` nahm den ROHEN Katalogeintrag. `to_event` fiel auf dessen
  FTP-Prozent zurueck: die Karte zeigte 250 W, im Kalender landeten 106-110 %
  einer FTP von 200. Der Kommentar ueber `to_event` verlangte das Gegenteil.
* A1 - `section_marks` sagte bedingungslos, die Kurve lese die Marken nicht,
  auch bei umgelegtem Kurvenschalter.
* A2 - die Kurve vergab den Grund `not_measured`, fuer den das Panel kein Wort
  kannte.

Home Assistant, voluptuous und aiohttp sind auf die wenigen Namen gestubbt, die
das Modul anfasst (dieselbe Bauart wie test_reconcile, PROJEKTSTAND §9).
"""

import coldcache  # noqa: F401,E402  - MUSS vor jedem Bauteil-Import stehen (§9)
import asyncio
import importlib.util
import sys
import types
from datetime import date
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


def _stub(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _identity(value=None, *args, **kwargs):
    return value


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
_stub("homeassistant")
_stub("homeassistant.core", HomeAssistant=object, callback=_identity)
_stub("homeassistant.components")
_stub("homeassistant.components.websocket_api", websocket_command=_decorator,
      async_response=_identity, async_register_command=lambda hass, handler: None)
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


importer = _load("importer")
W = _load("workouts")
ws = _load("websocket")


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


class FakeClient:
    def __init__(self):
        self.events = []

    async def async_create_event(self, payload):
        self.events.append(payload)
        return {"id": 4711}


class FakeCoordinator:
    def __init__(self, data):
        self.archive = FakeArchive(data)
        self.client = FakeClient()


# --- DIE EINGAENGE, fest gesetzt ---------------------------------------------
# Gesetzt wird an den BAUTEILEN, die `_session_inputs` befragt - nicht an
# `_session_inputs` selbst. Sonst pruefte der Test eine Attrappe des Weges, um
# den es geht.
CURVE = {"measured": [{"hour": 1, "t": 0.5, "watts": 152.5, "n": 26},
                      {"hour": 2, "t": 1.5, "watts": 142.2, "n": 23}],
         "literature": [{"hour": 1, "t": 0.5, "watts": 152.5},
                        {"hour": 2, "t": 1.5, "watts": 149.1}],
         "solid_until_hour": 2, "thin_until_hour": 2}
BLOCKS = {"families": {"vo2max": {
    "source_ok": True, "sessions": 6, "from": "2026-07-23", "to": "2026-09-08",
    "hr_window": {"low": 176, "high": 185, "n": 6},
    "latest": {"date": "2026-09-08", "median_watts": 252, "median_alpha": 0.41,
               "n_blocks": 4}}}}


def set_inputs(ftp, curve, blocks, anchors=None):
    ws._latest_ftp = lambda data: ftp
    ws._max_hr = lambda data: 190.0
    ws.coach_module.anchors = lambda data: dict(anchors or {"aerobic_hr": 146})
    ws.fatigue.curve = lambda data, **kw: curve
    ws.blocks_lib.series = lambda data: blocks
    ws.ramp_lib.latest = lambda data: None


def plan(key, data=None):
    coordinator = FakeCoordinator(data if data is not None else importer.empty_data("i1"))
    conn = FakeConn()
    ws._pick = lambda hass, athlete_id: coordinator
    asyncio.run(ws.websocket_plan_workout(
        None, conn, {"id": 1, "workout": key, "date": "2026-09-18"}))
    return coordinator, conn


# --- A4 · FIXTURE-BEWEIS: die Vorlage traegt Prozent, die Messung andere Watt --
# Ohne beides unterschiede der Test den rohen Eintrag nicht vom gerechneten.
check("A4 Fixture: die rohe VO2max-Vorlage traegt Prozent",
      "%" in W.BY_KEY["vo2_4x4"]["text"])
check("A4 Fixture: die Blockmessung liegt nicht zufaellig auf der FTP-Rechnung",
      252 not in {round(200 * p / 100) for p in (106, 108, 110)})

# --- A4 · der Schreibweg schreibt die gemessenen Watt -----------------------
set_inputs(200.0, CURVE, BLOCKS)
coord, conn = plan("vo2_4x4")
eq("A4: VO2max wird geschrieben", len(coord.client.events), 1)
desc = (coord.client.events[0] if coord.client.events else {}).get("description", "")
check(f"A4: VO2max ohne Prozent im Kalender: {desc!r}", "%" not in desc)
check("A4: VO2max traegt die gemessenen 252 W", "252w" in desc)
check("A4: VO2max traegt NICHT die FTP-Rechnung (212-220 W)",
      not any(f"{w}w" in desc for w in (212, 216, 220)))
eq("A4: kein Fehler gemeldet", conn.errors, [])

coord, conn = plan("z2_60")
desc = (coord.client.events[0] if coord.client.events else {}).get("description", "")
check(f"A4: Grundlage ohne Prozent im Kalender: {desc!r}", "%" not in desc)
check("A4: Grundlage traegt 0,90 der gemessenen Kurve (137 W)",
      f"{round(152.5 * W.CURVE_TARGET_SHARE)}w" in desc)

# JEDE Einheit des Katalogs, nicht nur die zwei oben: der Waechter gilt fuer
# den Weg, nicht fuer die Beispiele. Und die Faelle muessen die gemessenen
# Wege auch wirklich betreten (Trefferzusicherung).
quellen = set()
for key in sorted(W.BY_KEY):
    coord, conn = plan(key)
    events = coord.client.events
    check(f"A4 Katalog: {key} wurde geschrieben ({conn.errors})", len(events) == 1)
    text = (events[0] if events else {}).get("description", "")
    check(f"A4 Katalog: {key} traegt Prozent im Kalender", "%" not in text)
    quellen.add(W.scaled(W.BY_KEY[key], 200.0, 146, max_hr=190.0, curve=CURVE,
                         blocks=BLOCKS, ramp=None).get("watt_source"))
check(f"A4 Fixture-Beweis: Katalog laeuft ueber Bloecke, Kurve und FTP ({sorted(map(str, quellen))})",
      {"blocks", "curve", "ftp"} <= quellen)

# --- A4 · ohne Wattzahlen wird NICHT geschrieben -----------------------------
# Keine FTP, keine Messung: dann gibt es nur Prozent. Die gehen nicht still
# nach Intervals, der Handler bricht mit Grund ab.
set_inputs(None, None, None, anchors={})
coord, conn = plan("vo2_4x4")
eq("A4 ohne Watt: nichts geschrieben", len(coord.client.events), 0)
eq("A4 ohne Watt: Grund benannt", [code for code, _ in conn.errors], ["no_watts"])
eq("A4 ohne Watt: kein Erfolg gemeldet", conn.results, [])

# --- A1 · der Kurvensatz haengt an der Schalterstellung ----------------------
def marks_payload(from_marks):
    data = importer.empty_data("i1")
    data["settings"] = {ws.fatigue.CURVE_SWITCH: from_marks}
    coordinator = FakeCoordinator(data)
    conn = FakeConn()
    ws._pick = lambda hass, athlete_id: coordinator
    ws.websocket_section_marks(None, conn, {"id": 1})
    return (conn.results[0] if conn.results else {}).get("not_active") or {}


aus, an = marks_payload(False), marks_payload(True)
check("A1 Fixture-Beweis: beide Stellungen liefern Verschiedenes", aus != an)
check("A1: Schalter aus - der Kurvensatz steht da", bool(aus.get("curve")))
check("A1: Schalter an - der Kurvensatz ist fort", "curve" not in an)
_sm_payload = FakeConn()
ws._pick = lambda hass, athlete_id: FakeCoordinator(importer.empty_data("i1"))
ws.websocket_section_marks(None, _sm_payload, {"id": 1})
_lost = ((_sm_payload.results or [{}])[0]).get("lost_text") or {}
eq("lost: die Payload traegt je Verwerfungsgrund einen Satz",
      sorted(_lost), sorted(["changed", "moved", "version", "unknown"]))
eq("lost: die Saetze kommen aus dem Modul",
      _lost, dict(sys.modules["iv.section_marks"].LOST_TEXT))
check("A1: der Blocksatz steht in beiden Stellungen",
      bool(aus.get("blocks")) and bool(an.get("blocks")))

# --- A2 · jeder Grund der markierten Auswahl hat ein Wort -------------------
fat = _load("fatigue")
data = importer.empty_data("i1")
data["settings"] = {fat.CURVE_SWITCH: True}
data["activities"]["i9"] = {"id": "i9", "start_date_local": "2026-06-04T09:00:00",
                            "name": "Volumen", "moving_time": 5400}
data["section_marks"] = {"i9": {"date": "2026-06-04", "marks": {"endurance": [0]},
                                "anchor": {"laps": 1, "sections": [{"i": 0, "s": 5400}]},
                                "measure": {}, "reason": "", "measured_at": "2026-09-15",
                                "set_at": "2026-09-15", "v": 3}}
gruende = fat._marked_rides(data).get("dropped") or {}
check("A2 Fixture-Beweis: die markierte Fahrt ohne Messung erzeugt einen Grund", bool(gruende))
worte = fat.DROPPED_WORDS
for grund in sorted(gruende):
    check(f"A2: der Grund {grund} hat ein Wort", grund in worte)
    paar = worte.get(grund) or ("", "")
    check(f"A2: das Wort zu {grund} ist nicht der Rohschluessel", grund not in " ".join(paar))
for wort in ("zu locker", "Fehler", "Mangel", "leider", "nicht ausreich"):
    check(f"A2: kein gesperrtes Wort ({wort})",
          all(wort not in " ".join(p) for p in worte.values()))
fat_src = (COMP / "fatigue.py").read_text(encoding="utf-8")
check("A2: die Kurven-Payload traegt die Woerter", '"dropped_words":' in fat_src)

# --- B2b-2 · der Blockschalter: speichert nur im Aenderungsfall -------------
class SaveArchive(FakeArchive):
    def __init__(self, data):
        super().__init__(data)
        self.saves = 0

    async def async_save_now(self):
        self.saves += 1


_bs = FakeCoordinator(importer.empty_data("i1"))
_bs.archive = SaveArchive(_bs.archive.data)
ws._pick = lambda hass, athlete_id: _bs
for _want, _saves in ((True, 1), (True, 1), (False, 2)):
    _c = FakeConn()
    asyncio.run(ws.websocket_set_block_source(None, _c, {"id": 1, "from_marks": _want}))
    eq(f"B2b-2: umgelegt auf {_want} meldet die Stellung",
       ((_c.results or [{}])[0]).get("from_marks"), _want)
    eq(f"B2b-2: nach {_want} {_saves} Speichervorgang/-vorgaenge (nur im Aenderungsfall)",
       _bs.archive.saves, _saves)
check("B2b-2: der Schalter steht im Archiv, nicht in den Integrationsoptionen",
      "blocks_from_marks" in (_bs.archive.data.get("settings") or {}))

# WELCHE Familien ihre Watt aus den Bloecken beziehen - aus der Quellenkette.
_bl = FakeConn()
ws.blocks_lib.series = lambda data: {"families": {}}
ws._pick = lambda hass, athlete_id: FakeCoordinator(importer.empty_data("i1"))
ws.websocket_blocks(None, _bl, {"id": 1})
eq("B2b-2: feeds_watts kommt aus SOURCE_CHAIN",
   ((_bl.results or [{}])[0]).get("feeds_watts"),
   sorted(f for f, c in W.SOURCE_CHAIN.items() if "blocks" in c))
check("B2b-2: Tempo speist seine Watt nicht aus Bloecken",
      "tempo" not in (((_bl.results or [{}])[0]).get("feeds_watts") or ["tempo"]))

print(f"test_handlers: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
sys.exit(1 if FAILURES else 0)
