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
        # wie der echte Koordinator: die letzte Abfrage (0.73.0: der Heute-Handler
        # liest daraus die Kalender-Events fuer die Familie einer Fahrt)
        self.data = {"events": []}

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
# 0.68.0, erweitert (Auftrag 25.09.): Zahlen, die nur aus dem Archiv des ersten
# Athleten stammen koennen - seine Umrechnung (90,6 W/alpha aus dem Stufentest,
# 101,2 die alte Mitte mit Leiter), sein Anker (160,8 W) und sein Ziel-alpha
# (1,3, eine Option, keine Vorgabe). Keine davon darf als Zahlenwert in einer
# Payload des zweiten Athleten stehen - an keinem Pfad.
FIRST_ATHLETE_VALUES = (90.6, 101.2, 160.8, 1.3)

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
            if any(abs(float(x) - v) < 1e-9 for v in FIRST_ATHLETE_VALUES):
                found.append(f"{path}={x}")
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

print("\n=== Z3b. DER WOCHENPLAN liest dieselben Eingaenge wie die Trainer-Karte (F3.2) ===")
# Bis 0.67.1 baute websocket_goal seine Eingaenge von Hand - OHNE steering. Bei
# Steuerung an trug die Trainer-Karte den Startwert (150), die Wocheneinheit
# derselben Familie den Median der letzten Einheit (154). Rot an 0.67.1.
ws.dt_util = types.SimpleNamespace(now=lambda: __import__("datetime").datetime(2026, 9, 24))
_c.archive.data["goal"] = {"goal": "long_ride", "days_per_week": 4, "plan_start": "2026-09-21", "target_date": "2026-11-15", "target_hours": 5}
_g = FakeConn()
ws.websocket_goal(None, _g, {"id": 8})
_gp = (_g.results or [{}])[0]
eq("Z3b: goal laeuft ohne Fehler", _g.errors, [])
_w1 = (((_gp.get("plan") or {}).get("weeks") or [{}])[0].get("sessions") or [])
_ss_week = [x for x in _w1 if x.get("family") == "sweetspot"]
check("Z3b Fixture: Woche 1 hat eine SweetSpot-Einheit", bool(_ss_week))
eq("Z3b Treffer: die Wocheneinheit traegt die Steuerung wie die Trainer-Karte",
   _ss_week[0].get("watt_source") if _ss_week else None, "steering")
_work_w = [b for b in ((_ss_week[0].get("blocks_w") or []) if _ss_week else []) if str(b[2]).startswith("Block")]
check("Z3b Treffer: ihre Arbeitsbloecke stehen auf seinem Startwert (150), nicht auf dem Median",
      bool(_work_w) and all(b[1] == 150 for b in _work_w))
eq("Z3b: keine Zahl des ersten Athleten im Wochenplan", leaks(_gp), [])
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

print("\n=== Z6. EINE LASTGRENZE (S5): Trainer-Karten und Heute-Reiter nennen dieselbe Obergrenze ===")
# Entscheidung 24.09.: die Grenze MIT Zustandsdeckel (min(Budget, Deckel)) gilt
# fuer beide Leser. Bis 0.67.2 lasen die Karten das Budget allein; an einem
# beanspruchten Tag stand eine Karte "passt ins Budget" neben "Obergrenze 75".
# Hier: der Zustand wird auf `strained` gestellt (Deckel 75), das Budget liegt
# darueber. Rot an 0.67.2.
_a6 = second_athlete(steering_on=False)
import datetime as _dt6
for _i in range(40):
    _d = (_dt6.date(2026, 9, 24) - _dt6.timedelta(days=39 - _i)).isoformat()
    _a6["wellness"][_d] = {"hrv": 55.0, "restingHR": 52, "ctlLoad": 40.0 if _i < 34 else 10.0,
                           "ctl": 40.0, "atl": 40.0, "sleepSecs": 25200}
# 0.73.1 umgestellt: das Budget kommt nicht mehr aus einer gestellten readiness(),
# sondern aus B's eigener Reihe mit der Farbe des Zustands (strained -> amber, x1,0).
# Leichte letzte sechs Tage (10) halten es ueber dem Deckel 75 - der Fall bleibt derselbe.
_c6 = FakeCoordinator(_a6); _c6.archive = SaveArchive(_c6.archive.data)
ws._pick = lambda hass, athlete_id: _c6
_state_saved = ws.coach_module.state
ws.coach_module.state = lambda data, **kw: {"state": "strained", "label": "beansprucht", "detail": "", "since": None,
    "week_z": -0.6, "recent_hrv_z": -0.6, "recent_rhr_z": 0.2, "infection_suspected": False, "warnings": [], "explained": [], "context": {}, "baseline_note": ""}
_ready_saved = ws.analytics.readiness
# die zweite Ampel darf die Grenze nicht mehr bewegen: rot gestellt, Grenze bleibt 75
ws.analytics.readiness = lambda data, today=None: {"overall": "red", "components": [], "note": ""}
_t6 = FakeConn(); ws.websocket_today(None, _t6, {"id": 9})
_heute = (_t6.results or [{}])[0]
# 0.73.0 (Regel 10): die Familie kommt aus B's EIGENEN Marken; ohne eigene Events
# gibt es keinen Plan-Weg, und was nicht markiert ist, bleibt ohne Zuordnung.
_w73 = _heute.get("week") or {}
_s73 = _w73.get("sessions") or []
check("Z6 0.73.0: der Heute-Kopf traegt B's Woche aus B's Marken, ohne Plan-Weg",
      any(x.get("source") == "marks" for x in _s73)
      and all(x.get("source") in ("marks", "rest", "sport", None) for x in _s73)
      and all((x.get("group") is None) == (x.get("source") in ("rest", None)) for x in _s73))
_w6 = FakeConn(); ws.websocket_workouts(None, _w6, {"id": 10})
_wp6 = (_w6.results or [{}])[0]
eq("Z6 Fixture: der Heute-Reiter deckelt das Budget mit dem Zustand", _heute.get("ceiling"), 75)
eq("Z6 Treffer: die Trainer-Karten lesen dieselbe Obergrenze", _wp6.get("budget"), 75)
_karten = _wp6.get("workouts") or []
check("Z6 Treffer: eine Karte ueber 75 Last passt nicht mehr",
      all((k.get("fits_budget") is False) for k in _karten if (k.get("load") or 0) > 75) and any((k.get("load") or 0) > 75 for k in _karten))
check("Z6 Gegenprobe: eine Karte unter 75 passt weiter",
      all((k.get("fits_budget") is True) for k in _karten if (k.get("load") or 0) <= 75) and any((k.get("load") or 0) <= 75 for k in _karten))
eq("Z6: der Verbrauch reist in den Heute-Reiter", _heute.get("budget_used"), 0.0)
ws.coach_module.state = _state_saved; ws.analytics.readiness = _ready_saved

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

print("\n=== Z7. DIE GRUNDLAGE (0.68.0): ohne Stufentest, ohne HRV, ohne Ziel - benannt, nicht ersetzt ===")
# Athlet B unterscheidet sich in ALLEM: kein Stufentest, keine DFA-Daten, keine
# Tagesetiketten, keine Markierungen, kein Ziel-alpha (kein config_entry, also
# keine Option). Pflicht: kein Absturz, keine Zahl des ersten Athleten, jede
# fehlende Eingabe BENANNT statt still ersetzt.
_d7 = importer.empty_data("i4")
_d7["settings"] = {}
_d7["activities"]["r1"] = {"start_date_local": "2026-09-22T07:00:00", "name": "Ride", "type": "Ride",
                           "icu_ftp": 180, "icu_training_load": 40, "moving_time": 3600}
_c7 = FakeCoordinator(_d7); ws._pick = lambda hass, athlete_id: _c7
ws.dt_util = types.SimpleNamespace(now=lambda: __import__("datetime").datetime(2026, 9, 25))
_w7 = FakeConn()
ws.websocket_workouts(None, _w7, {"id": 9})
_wp7 = (_w7.results or [{}])[0]
eq("Z7: workouts laeuft ohne Fehler", _w7.errors, [])
_ga7 = [s for s in (_wp7.get("picks") or _wp7.get("sessions") or _wp7.get("workouts") or []) if s.get("family") in ("endurance", "long")]
check("Z7 Fixture: es gibt eine Grundlagen-Karte", bool(_ga7))
eq("Z7: ohne Stufentest -> Watt aus der FTP, beschriftet", _ga7[0].get("watt_source") if _ga7 else None, "ftp")
check("Z7: die fehlende Eingabe ist BENANNT (kein Stufentest), nicht still ersetzt",
      bool(_ga7) and "Stufentest" in str(_ga7[0].get("ga_missing") or ""))
_main7 = [b for b in ((_ga7[0].get("blocks_w") or []) if _ga7 else []) if str(b[2]).startswith("gleich")]
check("Z7: der Hauptteil traegt seine FTP-Prozent (180 W), kein Ziel des ersten Athleten",
      bool(_main7) and all(0 < b[1] <= 180 for b in _main7))
eq("Z7: keine Zahl des ersten Athleten in der Trainer-Payload (auch nicht 90,6 · 101,2 · 160,8 · 1,3)", leaks(_wp7), [])
_in7 = ws._session_inputs(_d7, None)
eq("Z7: ohne Option kein Ziel-alpha - keine 1,3 aus dem Code", (_in7.get("ga") or {}).get("target_alpha"), None)
check("Z7: die Umkehrung nennt, was fehlt", "Stufentest" in str((_in7.get("ga") or {}).get("missing") or ""))

print("\n=== Z7b. ATHLET B MIT EIGENEM STUFENTEST, OHNE ZIEL: nur die Grenze, aus SEINER Steigung ===")
# Sein Stufentest: HRVT1 140 W bei alpha 0,75, personalisiert 120 W bei 1,00 ->
# 80 W je alpha (nicht 90,6). Vier Grundlagenfahrten mit Stunde 1: 105 W bei
# alpha 1,15 -> Grenze 105 + 0,15 x 80 = 117 W. Kein Ziel-alpha -> kein Ziel.
_d7b = importer.empty_data("i5")
_d7b["settings"] = {}
rt = ws.ramp_lib if hasattr(ws, "ramp_lib") else _load("ramp_tests")
_d7b["activities"]["rt"] = {"start_date_local": "2026-08-01T07:00:00", "name": "Stufentest", "type": "Ride", "moving_time": 1500}
rt.set_entry(_d7b, "rt", "2026-08-01", result={"hrvt1": {"watts": 140, "alpha": 0.75, "hr": 140},
                                              "hrvt1_pers": {"watts": 120, "alpha": 1.0, "hr": 130}}, set_at="2026-08-01")
for i, day in enumerate(("2026-08-10", "2026-08-17", "2026-08-24", "2026-09-07")):
    aid = f"g{i}"
    _d7b["activities"][aid] = {"start_date_local": day + "T07:00:00", "name": "GA", "type": "Ride",
                               "icu_ftp": 180, "icu_training_load": 50, "moving_time": 5400,
                               "icu_zone_times": [3000, 2400, 0, 0, 0], "icu_weighted_avg_watts": 106, "icu_average_watts": 104}
    _d7b["dfa"][aid] = {"hours": [{"hour": 1, "load_alpha": 1.15, "load_n": 300, "load_w": 105}]}
_in7b = ws._session_inputs(_d7b, None)
_g7b = _in7b.get("ga") or {}
eq("Z7b: seine Steigung, nicht die des ersten", _g7b.get("mid"), 80.0)
eq("Z7b: Stunde 1 traegt seine Grenze 117 W und kein Ziel",
   [(h.get("hours"), h.get("limit_w"), h.get("target_w")) for h in (_g7b.get("hours") or [])], [(1, 117.0, None)])
_c7b = FakeCoordinator(_d7b); ws._pick = lambda hass, athlete_id: _c7b
_w7b = FakeConn()
ws.websocket_workouts(None, _w7b, {"id": 10})
_wp7b = (_w7b.results or [{}])[0]
eq("Z7b: workouts laeuft ohne Fehler", _w7b.errors, [])
_ga7b = [s for s in (_wp7b.get("picks") or _wp7b.get("sessions") or _wp7b.get("workouts") or []) if s.get("family") in ("endurance", "long")]
eq("Z7b: die Grundlage liest die Umkehrung", _ga7b[0].get("watt_source") if _ga7b else None, "ga")
_gb = ((_ga7b[0].get("ga_blocks") or [{}])[0]) if _ga7b else {}
eq("Z7b: nur die Grenze (117), kein Ziel, kein Ziel-alpha", (_gb.get("limit"), _gb.get("target"), _gb.get("target_alpha")), (117, None, None))
check("Z7b: der Hauptteil traegt die Grenze",
      bool(_ga7b) and all(b[1] == 117 for b in _ga7b[0]["blocks_w"] if str(b[2]).startswith("gleich")))
eq("Z7b: keine Zahl des ersten Athleten (auch nicht 90,6 · 1,3)", leaks(_wp7b), [])
ws.dt_util = _dt_saved

print("\n=== Z8. L1 (0.69.0): ATHLET B OHNE HRV - die Last entscheidet, und die Karte sagt es ===")
# 30 Tage Bestand mit Last, aber ohne eine einzige HRV-Zeile: kein Zustand
# ("unknown"). Dann darf die Last sperren - aber nur BESCHRIFTET, und keine
# Karte darf so aussehen, als haette der Zustand entschieden.
_d8 = importer.empty_data("i6")
_d8["settings"] = {}
import datetime as _dt
for i in range(35):
    day = (_dt.date(2026, 9, 25) - _dt.timedelta(days=35 - i)).isoformat()
    _d8["wellness"][day] = {"sleepSecs": 25000}
    # die letzten sechs Tage schwer (120), damit die Obergrenze unter die Karten faellt
    _d8["activities"][f"a{i}"] = {"start_date_local": day + "T07:00:00", "name": "Ride", "type": "Ride",
                                  "icu_ftp": 180, "icu_training_load": 120 if i >= 29 else 60, "moving_time": 3600}
_c8 = FakeCoordinator(_d8); ws._pick = lambda hass, athlete_id: _c8
ws.dt_util = types.SimpleNamespace(now=lambda: _dt.datetime(2026, 9, 25))
_w8 = FakeConn()
ws.websocket_workouts(None, _w8, {"id": 11})
_wp8 = (_w8.results or [{}])[0]
eq("Z8: workouts laeuft ohne Fehler", _w8.errors, [])
_cards8 = _wp8.get("picks") or _wp8.get("sessions") or _wp8.get("workouts") or []
check("Z8 Fixture: es gibt Karten und eine Obergrenze", bool(_cards8) and _wp8.get("budget") is not None)
_over8 = [c for c in _cards8 if c.get("fits_budget") is False and c.get("fit") != "no"]
check("Z8 Fixture: mindestens eine Karte liegt ueber der Obergrenze", bool(_over8))
check("Z8: ohne Zustand sperrt die Last - rot am Budget",
      _over8 and all(c["stage"]["key"] == "red" and c["stage"]["blocked_by"] == "budget" for c in _over8))
check("Z8: ... und die Karte sagt, dass kein Zustand da ist",
      _over8 and all("Zustand" in c["stage"]["detail"] and "Last" in c["stage"]["detail"] for c in _over8))
check("Z8: jede Karte ueber der Grenze traegt das Gelaender mit Last und Obergrenze",
      _over8 and all((c.get("guard") or {}).get("over") and (c.get("guard") or {}).get("ceiling") == _wp8.get("budget") for c in _over8))
eq("Z8: keine Zahl des ersten Athleten", leaks(_wp8), [])
# S1: ohne HRV keine HRV-Komponente, keine Vorbemerkung, kein Absturz - und
# die Ampel sagt nicht "gewichtet", wo nichts zu gewichten ist.
_r8 = FakeConn(); ws.websocket_readiness(None, _r8, {"id": 12})
_rp8 = (_r8.results or [{}])[0]
eq("Z8 S1: readiness laeuft ohne Fehler", _r8.errors, [])
check("Z8 S1: ohne HRV steht die HRV-Komponente auf unbekannt, keine Vorbemerkung",
      {c.get("id"): c.get("state") for c in (_rp8.get("components") or [])}.get("hrv") == "unknown"
      and _rp8.get("context_note") is None)
# L2: die Nacht-Bewertung ohne HRV - "keine Bewertung", benannt, kein Absturz
_n8 = FakeConn(); ws.websocket_night(None, _n8, {"id": 13, "activity_id": "a34"})
_np8 = (_n8.results or [{}])[0]
eq("Z8 L2: night laeuft ohne Fehler", _n8.errors, [])
check("Z8 L2: ohne HRV keine Bewertung, aber benannt",
      not _np8.get("available") or ((_np8.get("verdict") or {}).get("key") == "unbekannt" and "HRV" in str((_np8.get("verdict") or {}).get("label"))))
# Johannes' Fall zum Vergleich, am selben Rechenweg: MIT Zustand "ready" sperrt
# die Last nicht mehr - die Stufe bleibt gruen, das Gelaender kommt dazu.
_st8 = W.stage("ok", False, False)
eq("Z8 Gegenprobe: mit Zustand bleibt die Art (gruen + Gelaender)", (_st8["key"], _st8["blocked_by"], _st8["over_ceiling"]), ("green", None, True))
ws.dt_util = _dt_saved


print("\n=== Z9. 0.74.0 Belastungs-Reiter: seine Wochen, sein Verlauf, keine Zahl des ersten ===")
import datetime as _dtz  # noqa: E402
_dz = second_athlete()
for _i in range(45):
    _day = (_dtz.date(2026, 8, 15) - _dtz.timedelta(days=44 - _i)).isoformat()  # fern vom Stichtag des ersten
    _dz["wellness"][_day] = {"ctlLoad": [0.0, 60.0, 0.0, 45.0, 0.0, 80.0, 25.0][_i % 7], "hrv": 70, "restingHR": 48}
_cz = FakeCoordinator(_dz); _cz.data = {"events": []}
ws._pick = lambda hass, athlete_id: _cz
_lz = FakeConn()
ws.websocket_load(None, _lz, {"id": 9})
_pz = (_lz.results or [{}])[0]
eq("Z9: der Befehl laeuft ohne Fehler", _lz.errors, [])
eq("Z9: ohne Events nichts geplant", _pz.get("planned"), {})
check("Z9: Verlauf und Wochen stehen da", len(_pz.get("window_history") or []) == 45 and len(_pz.get("weeks_by_group") or []) == 12)
eq("Z9: keine Zahl des ersten Athleten in den neuen Teilen",
   leaks({k: _pz.get(k) for k in ("weeks_by_group", "window_history", "window_projection", "headline", "planned")}), [])


print("\n=== Z10. 0.74.4 Die Nacht in Klartext: seine Wortstufen aus seiner Basislinie ===")
# Eigene Lage: HRV um 70 ms, Ruhepuls um 47 bpm, eigener Kalender weit vor dem Stichtag des ersten.
# Nach der Einheit: HRV 60 (unter), Ruhepuls 52 (ueber) - die Worte muessen aus SEINER Basislinie kommen.
_dn = importer.empty_data("i2")
_start10 = _dtz.date(2026, 6, 1)
for _i in range(70):
    _day10 = (_start10 + _dtz.timedelta(days=_i)).isoformat()
    _dn["wellness"][_day10] = {"hrv": 70 + (_i % 5) - 2, "restingHR": 47 + (_i % 3) - 1, "sleepSecs": 27000 + (_i % 4) * 600}
_act10 = (_start10 + _dtz.timedelta(days=68)).isoformat()
_night10 = (_start10 + _dtz.timedelta(days=69)).isoformat()
_dn["activities"]["z10"] = {"start_date_local": _act10 + "T18:00:00", "type": "Ride", "name": "Abendrunde",
                            "icu_training_load": 95, "icu_intensity": 85, "moving_time": 5400}
_dn["wellness"][_night10].update({"hrv": 60, "restingHR": 52})
ws._pick = lambda hass, athlete_id: FakeCoordinator(_dn)
_n10 = FakeConn(); ws.websocket_night(None, _n10, {"id": 21, "activity_id": "z10"})
_p10 = (_n10.results or [{}])[0]
eq("Z10: der Befehl laeuft ohne Fehler", _n10.errors, [])
_h10 = (_p10.get("night") or {}).get("hrv") or {}
_r10 = (_p10.get("night") or {}).get("rhr") or {}
check("Z10: seine Basislinie ist seine (HRV um 70, Ruhepuls um 47)",
      68 <= (_h10.get("baseline") or 0) <= 72 and 46 <= (_r10.get("baseline") or 0) <= 48)
check("Z10: HRV 60 gegen seine ~70 steht als 'unter deinem Normalwert'", "unter deinem Normalwert" in str((_h10.get("word") or {}).get("text")))
check("Z10: Ruhepuls 52 gegen seine ~47 steht als 'über deinem Normalwert' (z ungünstig, Wort aus dem Rohwert)",
      (_r10.get("z") or 0) < 0 and "über deinem Normalwert" in str((_r10.get("word") or {}).get("text")))
check("Z10: die Karte traegt dasselbe Wort wie die Werte-Zeile (und es gibt eins)",
      _h10.get("word") is not None and (_p10.get("verdict") or {}).get("z_hrv_word") == _h10.get("word"))
check("Z10: das Karten-Label nennt seine Vergleichsbasis",
      str((_p10.get("verdict") or {}).get("label")).startswith("Verglichen mit deinen normalen Nächten: "))
eq("Z10: ohne zweite Nacht 'Zweite Nacht: kommt morgen'", (_p10.get("verdict") or {}).get("note"), "Zweite Nacht: kommt morgen")
eq("Z10: keine Zahl des ersten Athleten in der Nacht", leaks(_p10), [])

print(f"\ntest_zweiter_athlet: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
sys.exit(1 if FAILURES else 0)
