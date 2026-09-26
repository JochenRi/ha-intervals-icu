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
# Das ECHTE blocks.series, bevor einzelne Abschnitte es stubben - der
# Michael-Befund unten braucht es zurueck (ein Stub kennt keine Marken).
_REAL_SERIES = ws.blocks_lib.series
_REAL_LATEST_FTP = ws._latest_ftp


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
         "solid_until_hour": 2, "thin_until_hour": 2,
         # 0.67.4 (S3): die Kette der Kachel, aus der die Einheit liest
         "plan": [{"hours": 1, "watts": 152.5}, {"hours": 2, "watts": 142.2}]}
# 0.68.0: die Grundlage liest Ziel und Grenze der Umkehrung - hier als Fixture,
# das Ziel bei 137 W (die alte 0,90-Zahl), damit die Kalenderprobe unten bleibt.
GA = {"mid": 90.6, "limit_alpha": 1.0, "target_alpha": 1.3, "missing": None,
      "hours": [{"hours": 1, "n": 11, "load_w": 150.0, "alpha": 1.16, "limit_w": 164.5, "target_w": 137.0}]}
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
    ws.fatigue_v2.ga_targets = lambda data, today=None, limit_alpha=1.0, target_alpha=None: GA
    ws.blocks_lib.series = lambda data, **kw: blocks
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
check("A4: Grundlage traegt das Ziel der Umkehrung (137 W)", "137w" in desc)

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
                         blocks=BLOCKS, ramp=None, ga=GA).get("watt_source"))
check(f"A4 Fixture-Beweis: Katalog laeuft ueber Bloecke, Umkehrung und FTP ({sorted(map(str, quellen))})",
      {"blocks", "ga", "ftp"} <= quellen)

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
# Gegen das REGISTER, nicht gegen eine Liste im Test: ein neuer Grund (seit
# 0.63.1 "window") muss in der Payload ankommen, ohne dass jemand hier
# nachzieht - sonst zeigt die Karte den Rohschluessel (§7, 0.56.0).
eq("lost: die Payload traegt je Verwerfungsgrund einen Satz",
      sorted(_lost), sorted(sys.modules["iv.section_marks"].LOST_TEXT))
eq("lost: das Umlegen der Rechnung hat seinen eigenen Satz",
      bool(_lost.get(sys.modules["iv.section_marks"].LOST_WINDOW)), True)
eq("lost: die Saetze kommen aus dem Modul",
      _lost, dict(sys.modules["iv.section_marks"].LOST_TEXT))
check("A1: der Blocksatz steht in beiden Stellungen des KURVENschalters",
      bool(aus.get("blocks")) and bool(an.get("blocks")))


# --- F1.14 · der Blocksatz haengt am BLOCKschalter, nicht an der Steuerung ----
# "an deinen Marken vorbei" ist eine Aussage darueber, ob die Blockreihe die
# Marken liest - das entscheidet `blocks_from_marks` (blocks.series). Bis
# 0.66.2 hing der Satz an `steering_v2`: bei Blockschalter an und Steuerung
# aus stand er neben einer Reihe, die laengst auf den Marken rechnete; bei
# Blockschalter aus und Steuerung an fehlte er, obwohl die Marken nichts
# taten. Rote Pruefung: die zwei Kreuzstellungen fallen.
def blocks_sentence(blocks_from_marks, steering_on):
    data = importer.empty_data("i1")
    data["settings"] = {ws.blocks_lib.BLOCK_SWITCH: blocks_from_marks,
                        ws.steering_lib.STEERING_SWITCH: steering_on}
    coordinator = FakeCoordinator(data)
    conn = FakeConn()
    ws._pick = lambda hass, athlete_id: coordinator
    ws.websocket_section_marks(None, conn, {"id": 1})
    return "blocks" in ((conn.results[0] if conn.results else {}).get("not_active") or {})


check("F1.14: Blockschalter aus, Steuerung aus - der Satz steht", blocks_sentence(False, False))
check("F1.14: Blockschalter aus, Steuerung AN - der Satz steht trotzdem (Marken tun nichts)",
      blocks_sentence(False, True))
check("F1.14: Blockschalter an, Steuerung aus - der Satz ist fort (die Reihe liest die Marken)",
      not blocks_sentence(True, False))
check("F1.14: Blockschalter an, Steuerung an - der Satz ist fort", not blocks_sentence(True, True))

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
ws.blocks_lib.series = lambda data, **kw: {"families": {}}
ws._pick = lambda hass, athlete_id: FakeCoordinator(importer.empty_data("i1"))
ws.websocket_blocks(None, _bl, {"id": 1})
eq("B2b-2: feeds_watts kommt aus SOURCE_CHAIN",
   ((_bl.results or [{}])[0]).get("feeds_watts"),
   sorted(f for f, c in W.SOURCE_CHAIN.items() if "blocks" in c))
check("B2b-2: Tempo speist seine Watt nicht aus Bloecken",
      "tempo" not in (((_bl.results or [{}])[0]).get("feeds_watts") or ["tempo"]))

# --- Stufentest-Markierung: der Grund kommt aus ramp.measure (Rechenweg e1) --
# Vorher schrieb der Handler bei JEDEM leeren Ergebnis denselben Sammelsatz
# "kein auswertbarer Abfall" - bei einer Fahrt ohne Einrollen ist das falsch.
# Geprueft am echten Aufruf: echter Strom -> Zahlen; derselbe Strom ohne
# Einrollen -> der Protokollgrund im Archiv.
import json as _json  # noqa: E402
from datetime import datetime as _datetime  # noqa: E402

_REAL = _json.loads((Path(__file__).resolve().parent / "data" / "ramp_i187258578.json")
                    .read_text(encoding="utf-8"))


class StreamClient(FakeClient):
    def __init__(self, dfa, watts, hr):
        super().__init__()
        self.streams = [{"type": "dfa_a1", "data": dfa}, {"type": "watts", "data": watts},
                        {"type": "heartrate", "data": hr}]

    async def async_get_streams(self, activity_id, types_):
        return self.streams


def _mark(dfa, watts, hr):
    data = importer.empty_data("i1")
    data.setdefault("activities", {})["i187258578"] = {"start_date_local": "2026-09-16T17:00:00"}
    coord = FakeCoordinator(data)
    coord.archive = SaveArchive(data)
    coord.client = StreamClient(dfa, watts, hr)
    ws._pick = lambda hass, athlete_id: coord
    conn = FakeConn()
    asyncio.run(ws.websocket_set_ramp_test(None, conn, {"id": 1, "activity_id": "i187258578",
                                                         "mark": True}))
    return ((conn.results or [{}])[0]).get("entry") or {}, conn


_dt_saved = ws.dt_util
ws.dt_util = types.SimpleNamespace(now=lambda: _datetime(2026, 9, 16, 21, 0))
_ok_entry, _ok_conn = _mark(_REAL["alpha1"], _REAL["watts"], _REAL["heartrate"])
eq("Stufentest-Handler: echter Strom ohne Fehlermeldung", _ok_conn.errors, [])
eq("Stufentest-Handler: echter Strom traegt HRVT2 1861 s",
   ((_ok_entry.get("result") or {}).get("hrvt2") or {}).get("seconds"), 1861)
eq("Stufentest-Handler: echter Strom schreibt einen Grund", _ok_entry.get("reason"), "")
check("Stufentest-Handler: das Widerspruchsfeld kommt nicht im Archiv an",
      "contradiction" in (_ok_entry.get("result") or {}))
# Derselbe Strom OHNE Einrollen: die ersten 15 Minuten abgeschnitten.
_cut = 900
_no_warm = (_REAL["alpha1"][_cut:], _REAL["watts"][_cut:], _REAL["heartrate"][_cut:])
_expect = ws.ramp.measure(*_no_warm)
check("Stufentest-Handler Trefferzusicherung: der geschnittene Strom verletzt das Protokoll "
      "am Einrollen", _expect.get("code") == ws.ramp.WARMUP_NOT_FLAT)
_bad_entry, _ = _mark(*_no_warm)
eq("Stufentest-Handler: ohne Einrollen trotzdem Zahlen", _bad_entry.get("result"), None)
eq("Stufentest-Handler: der Grund ist nicht der Satz aus ramp.measure",
   _bad_entry.get("reason"), (_expect.get("reason") or "")[:256])
check("Stufentest-Handler: der alte Sammelsatz steht im Archiv",
      "auswertbarer Abfall" not in (_bad_entry.get("reason") or ""))
ws.dt_util = _dt_saved


# --- F1.11 · der Leseweg `laps` loescht nur bei FESTGESTELLTER Drift ----------
# Karte 1 F1.11, Pruefbericht 20.09. (bestaetigt), Entscheidung R1 Haltung (i):
# "keine Runden" ist kein Drift, sondern "konnte nicht pruefen". Die Messung
# bleibt stehen, der Befund reist mit, der Grund `moved` wird nur nach einer
# festgestellten Verschiebung gesetzt. Rote Pruefung zuerst (Regel 6 / Auflage):
# an 0.66.0 faellt Treffer 1, die Gegenproben A-C sind an 0.66.0 gruen.
import copy as _copy
sm = ws.marks_lib
_LAPS_RAW = [("WARMUP", 0, 600), ("WORK", 600, 1200), ("RECOVERY", 1200, 1290),
             ("WORK", 1290, 1890), ("COOLDOWN", 1890, 2400)]
_LAPS = [{"n": i + 1, "label": l, "start_index": s, "end_index": e, "moving_time": e - s}
         for i, (l, s, e) in enumerate(_LAPS_RAW)]


def _lap_payload(laps):
    return {"id": "f1", "icu_intervals": [
        {"label": l["label"], "start_index": l["start_index"],
         "end_index": l["end_index"], "moving_time": l["moving_time"]} for l in laps]}


def _marked_archive():
    data = importer.empty_data("i1")
    sm.set_mark(data, "f1", "2026-09-12", "tempo", 600, _LAPS, set_at="2026-09-12")
    sm.set_mark(data, "f1", "2026-09-12", "endurance", 1290, _LAPS, set_at="2026-09-12")
    sm.set_measurement(data, "f1", family="tempo",
                       blocks=[{"start_index": 600, "alpha": 0.9, "watts": 180}],
                       measured_at="2026-09-15", window_s=0)
    sm.set_measurement(data, "f1", family="endurance",
                       hours=[{"hour": 1, "p075": 201.0, "hr075": 140}],
                       measured_at="2026-09-15", window_s=0)
    return data


class _LapClient(FakeClient):
    def __init__(self, payload):
        super().__init__()
        self._payload = payload

    async def async_get_intervals(self, activity_id):
        return self._payload


def _open(payload):
    coord = FakeCoordinator(_marked_archive())
    coord.archive = SaveArchive(coord.archive.data)
    coord.client = _LapClient(payload)
    before = _copy.deepcopy(sm.entry_for(coord.archive.data, "f1"))
    ws._pick = lambda hass, athlete_id: coord
    conn = FakeConn()
    asyncio.run(ws.websocket_laps(None, conn, {"id": 1, "activity_id": "f1"}))
    return coord, before, (conn.results or [{}])[0]


# Fixture-Beweis: die Messung TRAEGT, und die Runden passen zum Anker.
_c0, _b0, _r0 = _open(_lap_payload(_LAPS))
check("F1.11 Fixture: beide Familien tragen Zahlen",
      bool(((_b0.get("measure") or {}).get("tempo") or {}).get("blocks"))
      and bool(((_b0.get("measure") or {}).get("endurance") or {}).get("hours")))
eq("F1.11 Fixture: passende Runden sind kein Drift", _r0.get("marks_stale"), None)

# 1 · TREFFER: keine Runden -> Messung unveraendert, nichts gespeichert, Befund gemeldet.
_c1, _b1, _r1 = _open({"id": "f1", "icu_intervals": []})
_e1 = sm.entry_for(_c1.archive.data, "f1")
eq("F1.11 Treffer: der Befund reist mit", _r1.get("marks_stale"), "laps_missing")
eq("F1.11 Treffer: die Messung steht noch (bitgleich)", _e1.get("measure"), _b1.get("measure"))
eq("F1.11 Treffer: kein Speichervorgang", _c1.archive.saves, 0)
check("F1.11 Treffer: `lost` ist nicht `moved` - nichts wurde festgestellt",
      _e1.get("lost") != sm.LOST_MOVED)
eq("F1.11 Treffer: die Stundenliste ist die von vorher (festgehaltener Sollwert)",
   (_e1.get("measure") or {}).get("endurance", {}).get("hours"),
   [{"hour": 1, "p075": 201.0, "hr075": 140}])

# 2 · GEGENPROBE A: andere Rundenzahl -> Messung faellt MIT Grund, ein Speichervorgang.
_c2, _b2, _r2 = _open(_lap_payload(_LAPS[:-1]))
_e2 = sm.entry_for(_c2.archive.data, "f1")
eq("F1.11 Gegenprobe A: Grund lap_count", _r2.get("marks_stale"), "lap_count")
eq("F1.11 Gegenprobe A: die Messung faellt", _e2.get("measure"), {})
eq("F1.11 Gegenprobe A: lost = moved", _e2.get("lost"), sm.LOST_MOVED)
eq("F1.11 Gegenprobe A: ein Speichervorgang", _c2.archive.saves, 1)

# 3 · GEGENPROBE B: ein markierter Abschnitt hat eine andere Dauer.
_moved = _copy.deepcopy(_LAPS)
_moved[1]["moving_time"] = 555
_c3, _b3, _r3 = _open(_lap_payload(_moved))
_e3 = sm.entry_for(_c3.archive.data, "f1")
eq("F1.11 Gegenprobe B: Grund section_moved", _r3.get("marks_stale"), "section_moved")
eq("F1.11 Gegenprobe B: die Messung faellt", _e3.get("measure"), {})
eq("F1.11 Gegenprobe B: ein Speichervorgang", _c3.archive.saves, 1)

# 4 · GEGENPROBE C: passende Runden -> nichts faellt, nichts gespeichert.
eq("F1.11 Gegenprobe C: die Messung bleibt",
   sm.entry_for(_c0.archive.data, "f1").get("measure"), _b0.get("measure"))
eq("F1.11 Gegenprobe C: kein Speichervorgang", _c0.archive.saves, 0)

# 5 · EIGENSCHAFT: behalten heisst nicht benutzen - ohne Runden keine brauchbaren Stunden.
eq("F1.11 Eigenschaft: usable_hours ohne Runden ist None",
   sm.usable_hours(_e1, []), None)
# 6 · DER SATZ AN DER EINHEIT sagt, dass die Messung steht und nicht verwendet wird.
check("F1.11 Satz: laps_missing sagt, dass die Messung stehen bleibt",
      "bleibt stehen" in sm.STALE_REASON["laps_missing"]
      and "nicht verwendet" in sm.STALE_REASON["laps_missing"])
check("F1.11 Grundmenge: laps_missing ist keine festgestellte Drift",
      "laps_missing" not in sm.DRIFT_FOUND and sm.DRIFT_FOUND == {"lap_count", "section_moved"})


# --- F1.8b · der Handler speichert nicht, wenn sich nichts geaendert hat ------
_c8 = FakeCoordinator(_marked_archive())
_c8.archive = SaveArchive(_c8.archive.data)
_c8.client = _LapClient(_lap_payload(_LAPS))
_c8.archive.data["activities"]["f1"] = {"start_date_local": "2026-09-12T08:00:00"}
ws._pick = lambda hass, athlete_id: _c8
_dt_saved8 = ws.dt_util
ws.dt_util = types.SimpleNamespace(now=lambda: __import__("datetime").datetime(2026, 9, 20))
_before8 = _copy.deepcopy(sm.entry_for(_c8.archive.data, "f1"))
for _i in range(2):
    _cn = FakeConn()
    asyncio.run(ws.websocket_set_section_mark(None, _cn, {
        "id": 1, "activity_id": "f1", "family": "tempo", "start_index": 600, "mark": True}))
    check(f"F1.8b Handler: Durchlauf {_i + 1} ohne Fehler", not _cn.errors)
eq("F1.8b Handler: dieselbe Marke zweimal - kein Speichervorgang", _c8.archive.saves, 0)
eq("F1.8b Handler: der Eintrag ist bitgleich", sm.entry_for(_c8.archive.data, "f1"), _before8)
ws.dt_util = _dt_saved8


# --- Michael-Befund (0.66.3) · der Startwert entsteht beim Einschalten ---------
# Ein ZWEITER, erfundener Athlet: drei gemessene SweetSpot-Einheiten bei
# ~150 W, Blockschalter auf Marken, Steuerung aus. Beim Einschalten entsteht
# sein Startwert aus SEINEN Einheiten und wird gespeichert; 190 W kommt nirgends
# vor. Rot vor dem Bau (der Handler kannte keine Anker).
def _michael_archive():
    d = importer.empty_data("i2")
    d["settings"] = {ws.blocks_lib.BLOCK_SWITCH: True, ws.steering_lib.STEERING_SWITCH: False}
    for i, (day, w) in enumerate((("2026-08-20", 148), ("2026-08-28", 150), ("2026-09-05", 152))):
        aid = f"m{i}"
        d["activities"][aid] = {"start_date_local": day + "T08:00:00", "name": "SweetSpot", "type": "Ride"}
        sm.set_mark(d, aid, day, "sweetspot", 600, _LAPS, set_at=day)
        sm.set_mark(d, aid, day, "sweetspot", 1290, _LAPS, set_at=day)
        sm.set_measurement(d, aid, family="sweetspot", measured_at=day, window_s=0,
                           blocks=[{"start_index": 600, "alpha": 0.72, "watts": w + 2, "hr": 150, "minutes": 10},
                                   {"start_index": 1290, "alpha": 0.68, "watts": w, "hr": 152, "minutes": 10}])
    return d


# Der globale Stub von oben (`series = lambda data: {}`) wird hier durch das
# ECHTE Modul ersetzt - der Startwert muss aus echten Marken entstehen.
ws.blocks_lib.series = _REAL_SERIES
_cm = FakeCoordinator(_michael_archive())
_cm.archive = SaveArchive(_cm.archive.data)
ws._pick = lambda hass, athlete_id: _cm
_dtm = ws.dt_util
ws.dt_util = types.SimpleNamespace(now=lambda: __import__("datetime").datetime(2026, 9, 23))
_cn = FakeConn()
asyncio.run(ws.websocket_set_steering_source(None, _cn, {"id": 1, "on": True}))
_ancm = (_cn.results or [{}])[0].get("anchors") or {}
check("Michael: der Handler meldet den entstandenen Startwert", "sweetspot" in _ancm)
eq("Michael: der Startwert ist SEIN Median (nicht 190)", (_ancm.get("sweetspot") or {}).get("w"), 150)
eq("Michael: der Stichtag ist der Einschalttag", (_ancm.get("sweetspot") or {}).get("date"), "2026-09-23")
eq("Michael: einmal gespeichert (Schalter + Anker)", _cm.archive.saves, 1)
check("Michael: VO2max ohne Einheiten hat keinen Startwert", "vo2max" not in _ancm)
# Die Blockkachel danach: Vorgabe 150, und 190 kommt in der Payload nicht vor.
_cb = FakeConn()
ws.websocket_blocks(None, _cb, {"id": 2})
_stm = ((_cb.results or [{}])[0]).get("steering") or {}
eq("Michael: die Kachel zeigt seinen Startwert", (_stm.get("sweetspot") or {}).get("watts"), 150)
check("Michael: 190 und 250 stehen nirgends in der Steuerungs-Payload",
      "190" not in str(_stm) and "250" not in str(_stm))
ok_json = str(((_cb.results or [{}])[0]).get("compare") or {})
check("Michael: auch nicht in der Vorschau", "190" not in ok_json and "250" not in ok_json)
# Ausschalten loescht den Startwert nicht.
asyncio.run(ws.websocket_set_steering_source(None, FakeConn(), {"id": 3, "on": False}))
eq("Michael: Ausschalten laesst den Startwert stehen",
   ws.steering_lib.anchors(_cm.archive.data).get("sweetspot", {}).get("w"), 150)
ws.dt_util = _dtm


# --- F3.11 · _latest_ftp: zwei Aktivitaeten am selben Tag ------------------------
# Karte 3 F3.11: verglichen wurde nur der TAG (`day < best_day`); bei gleichem Tag
# gewann die Archivreihenfolge. Zwei Aktivitaeten eines Tages mit verschiedener
# FTP (Rad/Lauf, oder eine geaenderte Einstellung dazwischen): die spaetere
# gilt. Rot an 0.67.1: die Reihenfolge im dict entscheidet, hier absichtlich
# gegen die Zeit sortiert.
_real_latest = _REAL_LATEST_FTP if "_REAL_LATEST_FTP" in globals() else None
_d11 = {"activities": {
    "b": {"start_date_local": "2026-09-20T18:00:00", "icu_ftp": 210},
    "a": {"start_date_local": "2026-09-20T07:00:00", "icu_ftp": 200},
    "c": {"start_date_local": "2026-09-19T09:00:00", "icu_ftp": 195}}}
_d11b = {"activities": {
    "a": {"start_date_local": "2026-09-20T07:00:00", "icu_ftp": 200},
    "b": {"start_date_local": "2026-09-20T18:00:00", "icu_ftp": 210}}}
eq("F3.11 Treffer: die spaetere Aktivitaet des Tages gilt (Archivreihenfolge b,a)", _real_latest(_d11), 210.0)
eq("F3.11 Treffer: ... unabhaengig von der Archivreihenfolge (a,b)", _real_latest(_d11b), 210.0)
eq("F3.11 Gegenprobe: ein juengerer Tag gewinnt weiter", _real_latest({"activities": {
    "x": {"start_date_local": "2026-09-21T06:00:00", "icu_ftp": 205}, **_d11["activities"]}}), 205.0)
eq("F3.11 Gegenprobe: ohne FTP-Feld faellt die Aktivitaet durch", _real_latest({"activities": {
    "x": {"start_date_local": "2026-09-21T06:00:00"}, **_d11["activities"]}}), 210.0)
eq("F3.11 Randfall: leeres Archiv", _real_latest({}), None)

# --- 0.73.4 · E4 §3.3 und §4: die Rueckmeldung des Schreibwegs ------------------
# Die Antwort von intervals.icu wird hier gestellt: mit der Kennung zurueck,
# ohne, mit anderem Wert, kein dict. Der Handler darf in keinem Fall abstuerzen,
# und "bestaetigt" nur bei Gleichheit.
class _EchoClient:
    def __init__(self, answer):
        self.answer, self.events = answer, []

    async def async_create_event(self, payload):
        self.events.append(payload)
        return self.answer(payload) if callable(self.answer) else self.answer


def _plan_e4(answer, key="vo2_4x4", day="2026-09-27"):
    coordinator = FakeCoordinator(importer.empty_data("i1"))
    coordinator.client = _EchoClient(answer)
    conn = FakeConn()
    ws._pick = lambda hass, athlete_id: coordinator
    asyncio.run(ws.websocket_plan_workout(None, conn, {"id": 1, "workout": key, "date": day}))
    return coordinator, conn


set_inputs(200.0, CURVE, BLOCKS)
_SOLL4 = "ha-intervals-icu:vo2_4x4:2026-09-27"
_c4, _k4 = _plan_e4(lambda p: {"id": 77, **p})
eq("0.73.4 §3.3: genau ein Event geschrieben", len(_c4.client.events), 1)
eq("0.73.4 §3.1: der Schreibweg sendet die Kennung", (_c4.client.events or [{}])[0].get("external_id"), _SOLL4)
_r4 = (_k4.results or [{}])[0]
eq("0.73.4 §3.3: kein Fehler", _k4.errors, [])
eq("0.73.4 §3.3: die Antwort nennt die gesendete Kennung", _r4.get("external_id"), _SOLL4)
eq("0.73.4 §3.3: Echo gleich -> bestaetigt", _r4.get("external_id_confirmed"), True)
eq("0.73.4 §3.3: der Rest der Antwort bleibt (ok/name/date/id)",
   {k: _r4.get(k) for k in ("ok", "name", "date", "id")},
   {"ok": True, "name": W.BY_KEY["vo2_4x4"]["title"], "date": "2026-09-27", "id": 77})
for _lab, _ans in (("Antwort ohne external_id", {"id": 4711}),
                   ("Antwort mit anderem Wert", {"id": 4711, "external_id": "ha-intervals-icu:vo2_4x4:2026-09-28"}),
                   ("Antwort kein dict (Liste)", [{"external_id": _SOLL4}]),
                   ("Antwort kein dict (Text)", "ok"),
                   ("Antwort None", None)):
    _c, _k = _plan_e4(_ans)
    eq(f"0.73.4 §4 {_lab}: kein Absturz, kein Fehler", _k.errors, [])
    _rr = (_k.results or [{}])[0]
    eq(f"0.73.4 §4 {_lab}: nicht bestaetigt", _rr.get("external_id_confirmed"), False)
    eq(f"0.73.4 §4 {_lab}: die gesendete Kennung steht trotzdem da", _rr.get("external_id"), _SOLL4)
    eq(f"0.73.4 §4 {_lab}: genau ein Schreibversuch, keine Wiederholung", len(_c.client.events), 1)
# Fehlerweg bleibt: eine Ausnahme wird gemeldet, nicht wiederholt
_cb = FakeCoordinator(importer.empty_data("i1"))
_calls = []
async def _boom_counted(payload):
    _calls.append(payload)
    raise RuntimeError("422 Unprocessable")
_cb.client.async_create_event = _boom_counted
_kb = FakeConn()
ws._pick = lambda hass, athlete_id: _cb
asyncio.run(ws.websocket_plan_workout(None, _kb, {"id": 1, "workout": "vo2_4x4", "date": "2026-09-27"}))
eq("0.73.4 §2 Rueckfall: 4xx geht als write_failed an das Panel", [c for c, _ in _kb.errors], ["write_failed"])
eq("0.73.4 §2 Rueckfall: genau ein Versuch", len(_calls), 1)

print(f"test_handlers: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
sys.exit(1 if FAILURES else 0)
