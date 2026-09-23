"""DER ZWEITE ATHLET - eine eigene Gattung im Pruefstand (0.66.3, Bauregel 10).

Warum eine eigene Datei: jede andere Fixture im Pruefstand traegt die Zahlen des
ersten Athleten - 190/250 W, den 17.09.2026, seine Marken. Ein Waechter, der
mit diesen Zahlen prueft, kann nicht sehen, dass sie im CODE stehen statt im
Archiv (Michael-Befund, 23.09.2026: ein zweiter Athlet sah im Kachelkopf eine
fremde Vorgabe). Hier laeuft ein ERFUNDENER zweiter Athlet - andere Wattlage,
anderer Kalender, Einheiten vor und nach dem 17.09.2026 - durch dieselben
Handler und Rechenwege wie der erste. Die Zusicherung ist immer dieselbe: keine
Zahl und kein Datum des ersten Athleten kommt in seinen Payloads vor, und was
er sieht, kommt aus seinem Archiv.

Wer eine Konstante mit Bestandszahlen anlegt, faellt hier - das ist der Zweck.
Home Assistant, voluptuous und aiohttp sind gestubbt wie in test_handlers.
"""
import coldcache  # noqa: F401,E402  - MUSS vor jedem Bauteil-Import stehen (§9)
import asyncio
import copy
import importlib.util
import json
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
# Das ECHTE blocks.series, bevor einzelne Abschnitte es stubben - der
# Michael-Befund unten braucht es zurueck (ein Stub kennt keine Marken).
_REAL_SERIES = ws.blocks_lib.series


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

sm = ws.marks_lib
blocks = ws.blocks_lib
steering = ws.steering_lib


class SaveArchive(FakeArchive):
    def __init__(self, data):
        super().__init__(data)
        self.saves = 0

    async def async_save_now(self):
        self.saves += 1


# --- DER ERSTE ATHLET, als Verbotsliste -------------------------------------
# Was in KEINEM Payload des zweiten Athleten stehen darf: die Startwerte und der
# Stichtag, die bis 0.66.2 im Code standen. Bewusst als Literale, nicht aus
# const gelesen: verschwindet die Uebernahme-Konstante eines Tages, prueft diese
# Datei trotzdem weiter gegen die Zahlen, die einmal im Code standen.
FIRST_ATHLETE = {"sweetspot_w": 190, "vo2max_w": 250, "date": "2026-09-17"}

# --- DER ZWEITE ATHLET: anderes Niveau, anderer Kalender --------------------
LAPS = [{"n": i + 1, "label": l, "start_index": s, "end_index": e, "moving_time": e - s}
        for i, (l, s, e) in enumerate([("WARMUP", 0, 600), ("WORK", 600, 1200), ("RECOVERY", 1200, 1290),
                                       ("WORK", 1290, 1890), ("COOLDOWN", 1890, 2400)])]
# SweetSpot um 150 W, VO2max um 210 W - je zwei Einheiten VOR und eine NACH dem 17.09.2026.
UNITS = [
    ("s1", "2026-08-20", "sweetspot", 148, 0.66), ("s2", "2026-08-30", "sweetspot", 150, 0.62),
    ("s3", "2026-09-20", "sweetspot", 152, 0.90),
    ("v1", "2026-08-25", "vo2max", 208, 0.42), ("v2", "2026-09-06", "vo2max", 212, 0.40),
    ("v3", "2026-09-21", "vo2max", 210, 0.30),
]


def second_athlete(steering_on=False):
    d = importer.empty_data("i2")
    d["settings"] = {blocks.BLOCK_SWITCH: True, steering.STEERING_SWITCH: bool(steering_on)}
    for aid, day, fam, w, a in UNITS:
        d["activities"][aid] = {"start_date_local": day + "T07:00:00", "name": fam, "type": "Ride",
                                "icu_ftp": 220, "icu_training_load": 60}
        sm.set_mark(d, aid, day, fam, 600, LAPS, set_at=day)
        sm.set_mark(d, aid, day, fam, 1290, LAPS, set_at=day)
        sm.set_measurement(d, aid, family=fam, measured_at=day, window_s=0,
                           blocks=[{"start_index": 600, "alpha": a + 0.05, "watts": w + 3, "hr": 150, "minutes": 10},
                                   {"start_index": 1290, "alpha": a, "watts": w, "hr": 152, "minutes": 10}])
    return d


def leaks(payload) -> list[str]:
    """Welche Zahlen des ersten Athleten in einer Payload stehen - als Zahlenwert, nicht als Ziffernfolge."""
    found = []
    def walk(x, path):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, f"{path}.{k}")
        elif isinstance(x, (list, tuple)):
            for i, v in enumerate(x):
                walk(v, f"{path}[{i}]")
        elif isinstance(x, bool):
            return
        elif isinstance(x, (int, float)):
            if x in (FIRST_ATHLETE["sweetspot_w"], FIRST_ATHLETE["vo2max_w"]) and any(
                    key in path for key in ("watts", "anchor", "target", "new_", "old_", "median", "first_", "suggested")):
                found.append(f"{path}={x}")
        elif isinstance(x, str) and FIRST_ATHLETE["date"] in x:
            found.append(f"{path}={x!r}")
    walk(payload, "")
    return found


def run(coro):
    return asyncio.run(coro)


print("\n=== Z1. Steuerung AUS: die Kachel zeigt SEINE Zahlen, nicht die des ersten ===")
_c = FakeCoordinator(second_athlete(steering_on=False))
_c.archive = SaveArchive(_c.archive.data)
ws._pick = lambda hass, athlete_id: _c
_b = FakeConn()
ws.websocket_blocks(None, _b, {"id": 1})
_p = (_b.results or [{}])[0]
eq("Z1: der Befehl laeuft ohne Fehler", _b.errors, [])
# Median ueber BEIDE Bloecke seiner letzten Einheit (155/152 -> 153,5 -> 154): die alte
# Rechnung zaehlt Block 1 mit, der Startwert unten nicht (unit_rows ab Block 2).
eq("Z1: SweetSpot-Median ist seiner", ((_p.get("families") or {}).get("sweetspot") or {}).get("latest", {}).get("median_watts"), 154)
eq("Z1: keine Zahl des ersten Athleten in der Payload", leaks(_p), [])
_st = _p.get("steering") or {}
check("Z1: ohne Startwert keine Vorgabe (SweetSpot)", (_st.get("sweetspot") or {}).get("watts") is None)
check("Z1: ... und die Kachel sagt, dass der Startwert noch entsteht",
      (_st.get("sweetspot") or {}).get("anchor_pending") is True)
eq("Z1: compare stuerzt nicht (F2.1) und traegt kein Delta ohne Vorgabe",
   ((_p.get("compare") or {}).get("sweetspot") or {}).get("delta"), None)

print("\n=== Z2. EINSCHALTEN: der Startwert entsteht aus seinen Einheiten, am Einschalttag ===")
_dt_saved = ws.dt_util
ws.dt_util = types.SimpleNamespace(now=lambda: __import__("datetime").datetime(2026, 9, 24))
_s = FakeConn()
run(ws.websocket_set_steering_source(None, _s, {"id": 2, "on": True}))
_anc = ((_s.results or [{}])[0]).get("anchors") or {}
eq("Z2: SweetSpot-Startwert = Median seiner Einheiten", (_anc.get("sweetspot") or {}).get("w"), 150)
eq("Z2: VO2max-Startwert = Median seiner Einheiten", (_anc.get("vo2max") or {}).get("w"), 210)
eq("Z2: der Stichtag ist SEIN Einschalttag", {a.get("date") for a in _anc.values()}, {"2026-09-24"})
eq("Z2: der Startwert steht im ARCHIV, nicht im Code",
   (_c.archive.data["settings"].get(steering.ANCHOR_KEY) or {}).get("sweetspot", {}).get("w"), 150)
eq("Z2: einmal gespeichert", _c.archive.saves, 1)

print("\n=== Z3. Steuerung AN: Kachel, Einheit und Stufentest-Protokoll auf SEINEN Zahlen ===")
_b2 = FakeConn()
ws.websocket_blocks(None, _b2, {"id": 3})
_p2 = (_b2.results or [{}])[0]
_st2 = _p2.get("steering") or {}
eq("Z3: Kachelkopf SweetSpot = sein Startwert", (_st2.get("sweetspot") or {}).get("watts"), 150)
eq("Z3: Kachelkopf VO2max = sein Startwert", (_st2.get("vo2max") or {}).get("watts"), 210)
eq("Z3: keine Einheit nach SEINEM Stichtag (alle liegen davor)", (_st2.get("sweetspot") or {}).get("n_since"), 0)
eq("Z3: keine Zahl des ersten Athleten in der Blockpayload", leaks(_p2), [])
_inputs = ws._session_inputs(_c.archive.data)
eq("Z3: die Einheit liest seinen Startwert", ((_inputs.get("steering") or {}).get("sweetspot") or {}).get("watts"), 150)
_w = FakeConn()
ws.websocket_workouts(None, _w, {"id": 4})
_wp = (_w.results or [{}])[0]
eq("Z3: workouts laeuft ohne Fehler", _w.errors, [])
_ss_cards = [s for s in (_wp.get("picks") or _wp.get("sessions") or _wp.get("workouts") or []) if s.get("family") == "sweetspot"]
check("Z3: es gibt eine SweetSpot-Karte", bool(_ss_cards))
eq("Z3: die Karte traegt die Steuerung", _ss_cards[0].get("watt_source") if _ss_cards else None, "steering")
_work = [b for b in ((_ss_cards[0].get("blocks_w") or []) if _ss_cards else []) if str(b[2]).startswith("Block")]
check("Z3: ihre Arbeitsbloecke stehen auf 150 W", bool(_work) and all(b[1] == 150 for b in _work))
eq("Z3: keine Zahl des ersten Athleten in der Trainer-Payload", leaks(_wp), [])
ws.dt_util = _dt_saved

print("\n=== Z4. EINSCHALTEN am ersten Tag ohne genug Einheiten: die Kachel sagt, was fehlt ===")
_d4 = importer.empty_data("i3")
_d4["settings"] = {blocks.BLOCK_SWITCH: True}
for aid, day, fam, w, a in UNITS[:2]:
    _d4["activities"][aid] = {"start_date_local": day + "T07:00:00", "name": fam, "type": "Ride"}
    sm.set_mark(_d4, aid, day, fam, 600, LAPS, set_at=day)
    sm.set_mark(_d4, aid, day, fam, 1290, LAPS, set_at=day)
    sm.set_measurement(_d4, aid, family=fam, measured_at=day, window_s=0,
                       blocks=[{"start_index": 600, "alpha": a, "watts": w, "hr": 150, "minutes": 10},
                               {"start_index": 1290, "alpha": a, "watts": w, "hr": 152, "minutes": 10}])
_c4 = FakeCoordinator(_d4); _c4.archive = SaveArchive(_c4.archive.data)
ws._pick = lambda hass, athlete_id: _c4
ws.dt_util = types.SimpleNamespace(now=lambda: __import__("datetime").datetime(2026, 9, 24))
_s4 = FakeConn()
run(ws.websocket_set_steering_source(None, _s4, {"id": 5, "on": True}))
eq("Z4: mit zwei Einheiten entsteht kein Startwert", ((_s4.results or [{}])[0]).get("anchors"), {})
_b4 = FakeConn()
ws.websocket_blocks(None, _b4, {"id": 6})
_st4 = ((_b4.results or [{}])[0]).get("steering") or {}
check("Z4: die Kachel nennt 2 von 3", "2 von 3" in str((_st4.get("sweetspot") or {}).get("note")))
eq("Z4: keine Zahl des ersten Athleten", leaks((_b4.results or [{}])[0]), [])
ws.dt_util = _dt_saved

print("\n=== Z5. DIE UEBERNAHME trifft nur, wer die Vorgabe schon hatte - und zu wem sie passt ===")
_aus = second_athlete(steering_on=False)
check("Z5: Schalter aus -> keine Uebernahme des Code-Startwerts",
      steering.migrate_legacy_anchor(_aus) is False and steering.anchors(_aus) == {})
# Der Fall, der ohne die Bestandsprobe Michael getroffen haette: Schalter beim
# Update AN, Bestand bei 150/210 - der Code-Startwert 190/250 passt nicht.
_an = second_athlete(steering_on=True)
check("Z5: Schalter an, fremder Bestand -> keine Uebernahme (echtes Archiv, echtes blocks.series)",
      steering.migrate_legacy_anchor(_an) is False and steering.anchors(_an) == {})
_b5 = FakeConn()
_c5 = FakeCoordinator(_an); ws._pick = lambda hass, athlete_id: _c5
ws.websocket_blocks(None, _b5, {"id": 7})
eq("Z5: ... und seine Kachel traegt danach keine Zahl des ersten Athleten", leaks((_b5.results or [{}])[0]), [])

print(f"\ntest_zweiter_athlet: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
sys.exit(1 if FAILURES else 0)
