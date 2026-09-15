"""Die Zuordnung Abschnitt -> Familie: Schluessel, Anker, Drift, Ruecknahme.

Lauf: python3 tests/test_section_marks.py

WAS HIER BEWIESEN WERDEN MUSS, und warum die Fixture so aussieht wie sie
aussieht: der naheliegende Fehler ist, die LAUFENDE NUMMER aus der Panel-
Rundenliste als Schluessel abzulegen. Er faellt bei einer Fahrt ohne Pausen
NICHT auf - beide Listen sind dort deckungsgleich. Deshalb traegt die Fixture
eine Fahrt, bei der ein Lap durch dfa_blocks faellt, und die beiden Bloecke,
die dabei verwechselt werden, sind an ihren Zahlen unterscheidbar (Lehre 2 aus
Paket A: eine Fixture, die zwei Faelle nicht trennt, besteht jede Pruefung und
beweist nichts).
"""

import coldcache  # noqa: F401,E402  - MUSS vor jedem Bauteil-Import stehen (§9)
import copy  # noqa: E402
import importlib.util  # noqa: E402
import sys  # noqa: E402
import types  # noqa: E402
from pathlib import Path  # noqa: E402

# Die Bauteile als winziges Paket laden, damit ihre relativen Importe tragen,
# ohne Home Assistant in den Lauf zu ziehen - derselbe Weg wie in test_import.
COMP = Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"
_pkg = types.ModuleType("iv")
_pkg.__path__ = [str(COMP)]
sys.modules["iv"] = _pkg


def _load(name):
    spec = importlib.util.spec_from_file_location(f"iv.{name}", COMP / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"iv.{name}"] = module
    spec.loader.exec_module(module)
    return module


const = _load("const")
derive = _load("derive")
importer = _load("importer")
sm = _load("section_marks")
BLOCK_MIN_SECONDS = const.BLOCK_MIN_SECONDS
BLOCK_WARMUP_DISCARD_S = const.BLOCK_WARMUP_DISCARD_S

FAILURES = []
CHECKS = 0


def check(label, got, expected):
    global CHECKS
    CHECKS += 1
    ok_ = got == expected
    print(f"{'PASS' if ok_ else 'FAIL'}  {label}: {got!r}"
          + ("" if ok_ else f"  (erwartet {expected!r})"))
    if not ok_:
        FAILURES.append(label)


def ok(label, condition):
    check(label, bool(condition), True)


def raises(label, fn, needle=""):
    """Ein strenger Schreibweg wirft MIT GRUND - beides wird geprueft."""
    global CHECKS
    CHECKS += 1
    try:
        fn()
    except ValueError as err:
        if needle and needle not in str(err):
            print(f"FAIL  {label}: Grund nennt {needle!r} nicht: {err}")
            FAILURES.append(label)
            return
        print(f"PASS  {label}: {str(err)[:70]}")
        return
    print(f"FAIL  {label}: kein ValueError")
    FAILURES.append(label)


# --- Die Fixture -------------------------------------------------------------
# Fuenf Abschnitte, EINER faellt durch dfa_blocks (90 s < BLOCK_MIN_SECONDS).
# Damit laufen laufende Nummer und Blockposition auseinander, und zwar genau um
# eins ab Abschnitt 4.
LAPS = [
    {"n": 1, "label": "WARMUP",   "start_index": 0,    "end_index": 600,  "moving_time": 600},
    {"n": 2, "label": "WORK",     "start_index": 600,  "end_index": 1200, "moving_time": 600},
    {"n": 3, "label": "RECOVERY", "start_index": 1200, "end_index": 1290, "moving_time": 90},
    {"n": 4, "label": "WORK",     "start_index": 1290, "end_index": 1890, "moving_time": 600},
    {"n": 5, "label": "COOLDOWN", "start_index": 1890, "end_index": 2400, "moving_time": 510},
]

# Je Abschnitt ein eigenes Niveau, damit die Bloecke an ihren Zahlen
# auseinanderzuhalten sind.
LEVELS = [(0, 600, 0.95, 120), (600, 1200, 0.55, 250), (1200, 1290, 0.90, 95),
          (1290, 1890, 0.58, 232), (1890, 2400, 0.99, 105)]


def streams():
    dfa, watts, hr = [], [], []
    for start, stop, alpha, power in LEVELS:
        for i in range(start, stop):
            # leichte Welle, damit der Median nicht auf einem einzigen Wert sitzt
            dfa.append(round(alpha + (i % 10) / 1000, 4))
            watts.append(power + (i % 6))
            hr.append(140 + (i % 4))
    return dfa, watts, hr


DFA, WATTS, HR = streams()
BLOCKS = derive.dfa_blocks(DFA, WATTS, HR, LAPS)

print("=== die Fixture trennt ueberhaupt zwei Faelle ===")
check("Fixture: ein Lap faellt durch dfa_blocks", len(BLOCKS), len(LAPS) - 1)
check("Fixture: der gefallene ist der kurze",
      [b.get("start_index") for b in BLOCKS], [0, 600, 1290, 1890])
ok("Fixture: er faellt wegen der Dauer", LAPS[2].get("moving_time") < BLOCK_MIN_SECONDS)
ok("Fixture: die verwechselbaren Bloecke sind unterscheidbar",
   BLOCKS[2].get("watts") != BLOCKS[3].get("watts")
   and BLOCKS[2].get("alpha") != BLOCKS[3].get("alpha"))
ok("Fixture: nach dem Verwerfen bleibt genug uebrig",
   all(b.get("points", 0) > 0 for b in BLOCKS)
   and LAPS[1].get("moving_time") > BLOCK_WARMUP_DISCARD_S)


# --- 1 · start_index gegen laufende Nummer ------------------------------------
print("\n=== 1 · der Schluessel ist start_index, NIEMALS die laufende Nummer ===")

data = {"section_marks": {}}
sm.set_mark(data, "a1", "2026-09-10", "sweetspot",
            LAPS[3].get("start_index"), LAPS, set_at="2026-09-10")
entry = sm.entry_for(data, "a1")

richtig = sm.marked_blocks(entry, BLOCKS, "sweetspot")
check("Schluessel: ueber start_index wird genau ein Block getroffen", len(richtig), 1)
check("Schluessel: und es ist der markierte Abschnitt",
      richtig[0].get("start_index"), LAPS[3].get("start_index"))
check("Schluessel: mit seiner eigenen Leistung",
      richtig[0].get("watts"), BLOCKS[3 - 1].get("watts"))

# DIE GEGENPROBE, gezaehlt und benannt: derselbe Haken, abgelegt als LAUFENDE
# NUMMER - so, wie es die Panel-Rundenliste nahelegt. Vorher die Zusicherung,
# dass die Ersetzung ueberhaupt etwas veraendert (achte Bauregel): die beiden
# Zuordnungen muessen auf VERSCHIEDENE Bloecke zeigen, sonst prueft der
# Vergleich unten nichts.
naiv = {"marks": {"sweetspot": [LAPS[3].get("n")]}}
ueber_n = [b for i, b in enumerate(BLOCKS, start=1)
           if i == LAPS[3].get("n")]
ok("Gegenprobe: die naive Zuordnung trifft ueberhaupt einen Block", len(ueber_n) == 1)
ok("Gegenprobe: und NICHT denselben",
   ueber_n and ueber_n[0].get("start_index") != richtig[0].get("start_index"))
check("Gegenprobe: sie trifft den Ausrollblock statt des Arbeitsblocks",
      ueber_n[0].get("start_index") if ueber_n else None, LAPS[4].get("start_index"))
check("Gegenprobe: und damit eine andere Leistung",
      ueber_n[0].get("watts") == richtig[0].get("watts") if ueber_n else None, False)
check("Gegenprobe: marked_blocks findet zur laufenden Nummer nichts",
      sm.marked_blocks(naiv, BLOCKS, "sweetspot"), [])

# Und der Schreibweg laesst sie gar nicht erst zu.
raises("Schreibweg: die laufende Nummer faellt mit Grund auf",
       lambda: sm.set_mark(data, "a2", "2026-09-10", "sweetspot",
                           LAPS[3].get("n"), LAPS),
       "laufende Nummer")
raises("Schreibweg: unbekannte Familie",
       lambda: sm.set_mark(data, "a2", "2026-09-10", "cyclocross", 600, LAPS),
       "Familie")
raises("Schreibweg: kein gueltiges Datum",
       lambda: sm.set_mark(data, "a2", "10.09.2026", "tempo", 600, LAPS),
       "Datum")
check("Schreibweg: nach drei Fehlschlaegen steht nichts im Archiv",
      sorted(data.get("section_marks", {})), ["a1"])


# --- 2 · die zwei J7-Auflagen, einzeln ----------------------------------------
print("\n=== 2 · Grundgeruest und Migration, jede fuer sich ===")

skeleton = importer.empty_data("42")
ok("J7 a: empty_data kennt den Block", sm.BLOCK in skeleton)
check("J7 a: und er ist leer, nicht None", skeleton.get(sm.BLOCK), {})

# Die Gegenprobe zur ersten Auflage: async_load fuellt NUR die oberste Ebene
# auf. Fehlt der Block im Grundgeruest, entsteht er auf einem Altbestand nie -
# genau die Luecke aus 0.35.0. Nachgestellt ohne Home Assistant.
altbestand = {"wellness": {}, "activities": {}, "dfa": {}}
mit_geruest = importer.empty_data("42")
mit_geruest.update(altbestand)
ok("J7 a Gegenprobe: MIT Eintrag bekommt der Altbestand den Block",
   sm.BLOCK in mit_geruest)
ohne_geruest = {k: v for k, v in importer.empty_data("42").items() if k != sm.BLOCK}
ok("J7 a Gegenprobe: die Mutation hat den Eintrag wirklich entfernt",
   sm.BLOCK not in ohne_geruest)
ohne_geruest.update(altbestand)
ok("J7 a Gegenprobe: OHNE Eintrag entsteht er nie", sm.BLOCK not in ohne_geruest)

# Zweite Auflage: die Migration. Ein No-op gibt None und loest keinen
# Speichervorgang aus - die eingefrorene Referenz.
sauber = copy.deepcopy(data.get(sm.BLOCK))
check("J7 b: ein sauberer Block ist ein No-op", sm.migrate(sauber), None)
check("J7 b: und er wurde dabei nicht angefasst", sauber, data.get(sm.BLOCK))

kaputt = {
    "x1": {"date": "2026-09-01", "marks": {"tempo": [600, "600", None], "unfug": [1]},
           "anchor": {"laps": 5, "sections": [{"i": 600, "s": 600}]},
           "hours": [{"hour": 1}], "reason": "", "set_at": "", "v": sm.MEASURE_VERSION},
    "x2": {"date": "kein Datum", "marks": {"tempo": [600]}},
    "x3": "gar kein Eintrag",
    "x4": {"date": "2026-09-02", "marks": {}},
}
mig = sm.migrate(kaputt)
ok("J7 b: ein kaputter Block wird normalisiert", isinstance(mig, dict))
check("J7 b: nur der brauchbare Eintrag bleibt", sorted(mig or {}), ["x1"])
check("J7 b: unbekannte Familien fallen",
      sorted((mig or {}).get("x1", {}).get("marks", {})), ["tempo"])
check("J7 b: Schluessel werden zu Zahlen und entdoppelt",
      (mig or {}).get("x1", {}).get("marks", {}).get("tempo"), [600])
check("J7 b: ein Rumpf ohne Familie ist kein Eintrag", "x4" in (mig or {}), False)


# --- 3 · die Messmarke --------------------------------------------------------
print("\n=== 3 · aeltere Messmarke: Zahlen weg, Zuordnung bleibt ===")

alt = {"a9": {"date": "2026-09-01", "marks": {"endurance": [0, 600]},
              "anchor": {"laps": 5, "sections": [{"i": 0, "s": 600}, {"i": 600, "s": 600}]},
              "hours": [{"hour": 1, "p075": 210}], "reason": "", "set_at": "",
              "v": sm.MEASURE_VERSION - 1}}
ok("Messmarke: die Fixture traegt ueberhaupt Zahlen",
   alt.get("a9", {}).get("hours"))
gealtert = sm.migrate(copy.deepcopy(alt)) or {}
check("Messmarke: die Stunden fallen", gealtert.get("a9", {}).get("hours"), None)
check("Messmarke: die Marken bleiben",
      gealtert.get("a9", {}).get("marks"), {"endurance": [0, 600]})
check("Messmarke: der Anker bleibt",
      gealtert.get("a9", {}).get("anchor", {}).get("sections"),
      [{"i": 0, "s": 600}, {"i": 600, "s": 600}])
ok("Messmarke: der Zustand ist SICHTBAR, nicht still",
   "neu zu messen" in gealtert.get("a9", {}).get("reason", ""))
check("Messmarke: und die Marke steht auf aktuell",
      gealtert.get("a9", {}).get("v"), sm.MEASURE_VERSION)
# Gegenprobe: mit AKTUELLER Marke bleiben die Zahlen stehen - sonst prueft der
# Block oben nur, dass migrate() Stunden immer wegwirft.
aktuell = copy.deepcopy(alt)
aktuell["a9"]["v"] = sm.MEASURE_VERSION
ok("Messmarke Gegenprobe: die Mutation hat die Marke wirklich gehoben",
   aktuell.get("a9", {}).get("v") != alt.get("a9", {}).get("v"))
behalten = sm.migrate(aktuell)
check("Messmarke Gegenprobe: bei aktueller Marke bleiben die Stunden",
      (behalten or aktuell).get("a9", {}).get("hours"), [{"hour": 1, "p075": 210}])


# Altbestaende: der frueher GESPEICHERTE Anzeigetext verwies auf einen Knopf,
# den es nicht gab. Er faellt beim Laden - und NUR er.
legacy = {"a7": {"date": "2026-09-01", "marks": {"tempo": [600]},
                 "anchor": {"laps": 3, "sections": [{"i": 600, "s": 600}]},
                 "hours": None, "v": sm.MEASURE_VERSION, "set_at": "",
                 "reason": "Markiert, noch nicht gemessen — die Messung läuft auf "
                           "„übernehmen und messen“."},
          "a8": {"date": "2026-09-01", "marks": {"tempo": [600]},
                 "anchor": {"laps": 3, "sections": [{"i": 600, "s": 600}]},
                 "hours": None, "v": sm.MEASURE_VERSION, "set_at": "",
                 "reason": "Die Abschnitte waren nicht abrufbar."}}
ok("Altbestand: die Fixture traegt den alten Satz wirklich",
   "übernehmen und messen" in legacy["a7"]["reason"])
gereinigt = sm.migrate(copy.deepcopy(legacy)) or {}
check("Altbestand: der veraltete Anzeigetext faellt",
      gereinigt.get("a7", {}).get("reason"), "")
check("Altbestand: die Marken bleiben dabei unberuehrt",
      gereinigt.get("a7", {}).get("marks"), {"tempo": [600]})
check("Altbestand: ein ECHTER Grund bleibt stehen",
      gereinigt.get("a8", {}).get("reason"), "Die Abschnitte waren nicht abrufbar.")

# --- 4 · die Ruecknahme sitzt auf der einzelnen Marke --------------------------
print("\n=== 4 · Ruecknahme: eine Marke, nicht 'letzter Zustand' ===")

vorher = {"section_marks": {}}
unberuehrt = copy.deepcopy(vorher)
sm.set_mark(vorher, "b1", "2026-09-11", "sweetspot", 600, LAPS, set_at="2026-09-11")
sm.set_mark(vorher, "b1", "2026-09-11", "tempo", 600, LAPS, set_at="2026-09-11")
check("Mehrfach: ein Abschnitt traegt zwei Familien",
      sm.families_at(sm.entry_for(vorher, "b1"), 600), ["sweetspot", "tempo"])
ok("Mehrfach: die Fixture hat wirklich zwei", len(sm.marked(sm.entry_for(vorher, "b1"))) == 1)

sm.unset_mark(vorher, "b1", "tempo", 600)
check("Ruecknahme: die eine Familie ist weg",
      sm.families_at(sm.entry_for(vorher, "b1"), 600), ["sweetspot"])
ok("Ruecknahme: der Eintrag steht noch", sm.entry_for(vorher, "b1") is not None)

sm.unset_mark(vorher, "b1", "sweetspot", 600)
check("Ruecknahme: mit der letzten Marke faellt der ganze Eintrag",
      sm.entry_for(vorher, "b1"), None)
check("Ruecknahme: kein Rumpf bleibt stehen - bit-identisch wie nie markiert",
      vorher, unberuehrt)

# Gegenprobe: die Ruecknahme trifft die GENANNTE Marke, nicht die zuletzt
# gesetzte. Zwei Familien an ZWEI Abschnitten, zurueckgenommen wird die erste.
zwei = {"section_marks": {}}
sm.set_mark(zwei, "b2", "2026-09-11", "sweetspot", 600, LAPS)
sm.set_mark(zwei, "b2", "2026-09-11", "tempo", 1290, LAPS)
sm.unset_mark(zwei, "b2", "sweetspot", 600)
check("Ruecknahme: die genannte Marke faellt, nicht die letzte",
      sm.entry_for(zwei, "b2").get("marks"), {"tempo": [1290]})
check("Ruecknahme: und der Anker fuehrt nur noch den uebrigen Abschnitt",
      [s.get("i") for s in sm.entry_for(zwei, "b2").get("anchor", {}).get("sections", [])],
      [1290])

# Die Ruecknahme braucht WEDER Laps NOCH Datum - sonst waere eine falsch
# gesetzte Marke genau dann nicht loszuwerden, wenn die Schnittstelle klemmt.
ohne = {"section_marks": {}}
sm.set_mark(ohne, "b3", "2026-09-11", "endurance", 0, LAPS, set_at="2026-09-11")
sm.set_mark(ohne, "b3", "2026-09-11", "endurance", 600, LAPS, set_at="2026-09-11")
anker_vorher = copy.deepcopy(sm.entry_for(ohne, "b3").get("anchor"))
check("Ruecknahme: sie laeuft ohne Laps",
      sm.unset_mark(ohne, "b3", "endurance", 0) is None, False)
check("Ruecknahme: das Datum bleibt das des Eintrags",
      sm.entry_for(ohne, "b3").get("date"), "2026-09-11")
check("Ruecknahme: der Anker des UEBRIGEN Abschnitts bleibt unveraendert",
      sm.entry_for(ohne, "b3").get("anchor", {}).get("sections"),
      [s_ for s_ in (anker_vorher or {}).get("sections", []) if s_.get("i") == 600])
check("Ruecknahme: und die Rundenzahl im Anker bleibt stehen",
      sm.entry_for(ohne, "b3").get("anchor", {}).get("laps"),
      (anker_vorher or {}).get("laps"))
check("Ruecknahme: eine Marke, die es nicht gibt, aendert nichts",
      sm.unset_mark(ohne, "b3", "tempo", 600).get("marks"), {"endurance": [600]})
check("Ruecknahme: auf einer nie markierten Fahrt ist sie None",
      sm.unset_mark({"section_marks": {}}, "nix", "tempo", 0), None)
raises("Ruecknahme: unbekannte Familie faellt auch hier auf",
       lambda: sm.unset_mark(ohne, "b3", "cyclocross", 600), "Familie")

check("Ruecknahme: die ganze Fahrt auf einmal", sm.remove_entry(zwei, "b2"), True)
check("Ruecknahme: ein zweites Mal ist kein Fehler", sm.remove_entry(zwei, "b2"), False)


# --- 5 · der Haken misst NICHT ------------------------------------------------
print("\n=== 5 · der Haken misst nicht - gemessen wird auf 'uebernehmen' ===")

def haken_misst_nicht(entry_):
    """DIE Zusicherung, einmal geschrieben und zweimal angewandt.

    Einmal am echten Code, einmal am eingebauten Messpfad - sonst prueft die
    Gegenprobe nur, dass eine Mutation etwas veraendert, und nicht, dass die
    Zusicherung sie FINDET.

    Der Zustand steht in `hours is None`, NICHT in einem Satz: seit 0.53.1
    wird kein Anzeigetext mehr in den Eintrag geschrieben (er veraltete mit
    dem naechsten Umbau und stand dann in Altbestaenden weiter).
    """
    return (entry_ or {}).get("hours") is None \
        and not (entry_ or {}).get("reason")


mess = {"section_marks": {}}
frisch = sm.set_mark(mess, "c1", "2026-09-12", "endurance", 0, LAPS, set_at="2026-09-12")
check("Haken: der Eintrag steht ohne Zahlen", frisch.get("hours"), None)
check("Haken: und OHNE gespeicherten Anzeigetext", frisch.get("reason"), "")
check("Haken: die Zusicherung haelt am echten Code", haken_misst_nicht(frisch), True)
# Der Satz reist im LESEWEG mit, statt im Eintrag zu stehen - eine Stelle,
# kein Altbestand, der migriert werden muss.
ok("Haken: der Satz nennt den Knopf nicht mehr, den es noch nicht gibt",
   "übernehmen und messen" not in sm.NOT_MEASURED)
ok("Haken: er sagt stattdessen, dass der Knopf noch kommt",
   "kommt mit der Messung" in sm.NOT_MEASURED)
check("Haken: usable_hours gibt nichts her", sm.usable_hours(frisch, LAPS), None)

gemessen = sm.set_measurement(mess, "c1", hours=[{"hour": 1, "p075": 208}], reason="")
check("Uebernehmen: erst jetzt stehen Zahlen da",
      gemessen.get("hours"), [{"hour": 1, "p075": 208}])
check("Uebernehmen: und sie sind benutzbar",
      sm.usable_hours(sm.entry_for(mess, "c1"), LAPS), [{"hour": 1, "p075": 208}])

# DIE GEGENPROBE zu 'der Haken misst nicht': ein impliziter Messpfad wird
# eingebaut - set_mark misst gleich mit - und muss auffallen. Zuerst die
# Zusicherung, dass die Ersetzung ueberhaupt gegriffen hat.
echt_set_mark = sm.set_mark


def _heimlich_messend(data_, aid, date, family, index, laps, set_at=""):
    entry_ = echt_set_mark(data_, aid, date, family, index, laps, set_at=set_at)
    if entry_ is not None:
        entry_["hours"] = [{"hour": 1, "p075": 999}]
        entry_["reason"] = ""
    return entry_


sm.set_mark = _heimlich_messend
mutiert = {"section_marks": {}}
schleich = sm.set_mark(mutiert, "c2", "2026-09-12", "endurance", 0, LAPS)
ok("Gegenprobe: der eingebaute Messpfad hat wirklich etwas veraendert",
   schleich.get("hours") is not None)
check("Gegenprobe: DIESELBE Zusicherung faellt daran - sie ist nicht blind",
      haken_misst_nicht(schleich), False)
sm.set_mark = echt_set_mark
zurueck = sm.set_mark({"section_marks": {}}, "c3", "2026-09-12", "endurance", 0, LAPS)
check("Gegenprobe: nach dem Zuruecknehmen haelt sie wieder",
      haken_misst_nicht(zurueck), True)


# --- 6 · die Drift MELDET, statt zu rechnen -----------------------------------
print("\n=== 6 · Drift: gemeldet, nicht stillschweigend weiterverrechnet ===")

eintrag = sm.entry_for(mess, "c1")
check("Drift: auf unveraenderter Fahrt ist nichts zu melden", sm.drift(eintrag, LAPS), None)

verschoben = copy.deepcopy(LAPS)
verschoben[0]["moving_time"] = 640
ok("Drift: die Mutation hat die Dauer wirklich veraendert",
   verschoben[0].get("moving_time") != LAPS[0].get("moving_time"))
check("Drift: ein verschobener Abschnitt wird benannt",
      sm.drift(eintrag, verschoben), "section_moved")
check("Drift: und die Fahrt zieht keinen Wert mehr",
      sm.usable_hours(eintrag, verschoben), None)

weniger = [lap for lap in LAPS if lap.get("n") != 5]
ok("Drift: die Mutation hat wirklich einen Lap entfernt", len(weniger) != len(LAPS))
check("Drift: eine andere Rundenzahl wird benannt", sm.drift(eintrag, weniger), "lap_count")
check("Drift: fehlende Runden sind ein eigener Grund, kein 'in Ordnung'",
      sm.drift(eintrag, []), "laps_missing")
ok("Drift: jeder Grund traegt einen Satz",
   all(g in sm.STALE_REASON for g in ("laps_missing", "lap_count", "section_moved")))

# Der Anker wird von einer WEITEREN Marke nicht stillschweigend aufgefrischt -
# sonst verschwaende ein spaeterer Haken die Drift.
sm.set_mark(mess, "c1", "2026-09-12", "endurance", 600, verschoben)
check("Anker: eine zweite Marke frischt den alten Abschnitt NICHT auf",
      sm.drift(sm.entry_for(mess, "c1"), verschoben), "section_moved")

# Bestaetigen ist ein Knopf, kein Automatismus - und die Messung faellt dabei.
sm.set_measurement(mess, "c1", hours=[{"hour": 1, "p075": 208}])
ok("Bestaetigen: vorher stehen wieder Zahlen da",
   sm.entry_for(mess, "c1").get("hours") is not None)
bestaetigt = sm.reanchor(mess, "c1", verschoben)
check("Bestaetigen: danach sitzt die Markierung wieder",
      sm.drift(bestaetigt, verschoben), None)
check("Bestaetigen: die Marken bleiben",
      bestaetigt.get("marks"), {"endurance": [0, 600]})
check("Bestaetigen: die Messung auf dem alten Ausschnitt faellt",
      bestaetigt.get("hours"), None)
raises("Bestaetigen: ein weggefallener Abschnitt wird NICHT bestaetigt",
       lambda: sm.reanchor(mess, "c1", [lap for lap in verschoben
                                        if lap.get("start_index") != 600]),
       "neu zu setzen")


# --- 7 · Lesewege -------------------------------------------------------------
print("\n=== 7 · Lesewege: nachsichtig, und in sich stimmig ===")

check("Lesen: entries sortiert nach Datum, nicht nach ID", [
    row.get("activity_id") for row in sm.entries(
        {"section_marks": {
            "z9": {"date": "2026-01-01", "marks": {"tempo": [0]}},
            "a1": {"date": "2026-06-01", "marks": {"tempo": [0]}}}})
], ["z9", "a1"])
check("Lesen: ein fehlender Block ist kein Fehler", sm.entries({}), [])
check("Lesen: ein kaputter Eintrag auch nicht",
      sm.entry_for({"section_marks": {"a": "text"}}, "a"), None)
check("Lesen: marked() ueber alle Familien",
      sm.marked({"marks": {"tempo": [600], "long": [0, 600]}}), [0, 600])
check("Lesen: marked_blocks ohne Bloecke", sm.marked_blocks(eintrag, None), [])
check("Lesen: vier Familien, der Stufentest ist keine davon",
      (len(sm.FAMILIES), "ramp" in sm.FAMILIES), (4, False))

# --- 8 · mask_ranges: die zweite Haelfte des Schluessels -----------------------
print("\n=== 8 · mask_ranges: start_index allein schneidet nichts ===")

bereiche, fehlt = sm.mask_ranges(LAPS, [600, 1290])
check("Maske: je Marke ein Bereich [start, end)", bereiche, [(600, 1200), (1290, 1890)])
check("Maske: und nichts fehlt", fehlt, [])

# DIE KONVENTION, und sie ist die aus dfa_blocks: `end_index` zeigt auf die
# Stelle NACH dem Abschnitt. Mit `<=` liefe der erste Wert des Folgeabschnitts
# mit - bei einem Intervall waere das der erste Wert der Pause.
check("Maske: das Ende ist exklusiv, der Folgeabschnitt bleibt draussen",
      [stop for start, stop in sm.mask_ranges(LAPS, [600])[0]],
      [lap.get("end_index") for lap in LAPS if lap.get("start_index") == 600])

# DER PUNKT DER FUNKTION: was NICHT zu maskieren ist, wird GEMELDET. Still
# weniger zu maskieren als markiert wurde hiesse, auf einem anderen Ausschnitt
# zu messen als der Athlet gewaehlt hat - und das Ergebnis saehe richtig aus.
check("Maske: ein Abschnitt, den es in diesen Laps nicht gibt, wird benannt",
      sm.mask_ranges(LAPS, [600, 9999]), ([(600, 1200)], [9999]))
check("Maske: ein Lap ohne end_index taugt nicht zum Schneiden und wird benannt",
      sm.mask_ranges([{"start_index": 0, "moving_time": 600}], [0]), ([], [0]))
check("Maske: ein Ende vor dem Anfang ebenfalls",
      sm.mask_ranges([{"start_index": 600, "end_index": 100}], [600]), ([], [600]))
check("Maske: ohne Laps ist ALLES gemeldet, nicht stillschweigend nichts",
      sm.mask_ranges(None, [0, 600]), ([], [0, 600]))
check("Maske: ohne Marken gibt es nichts zu melden", sm.mask_ranges(LAPS, []), ([], []))
check("Maske: die Bereiche kommen sortiert und entdoppelt",
      sm.mask_ranges(LAPS, [1290, 600, 600])[0], [(600, 1200), (1290, 1890)])

# KEIN 120-Sekunden-Verwerfen: das gehoert zur BLOCKmessung. Ein stiller
# zweiter Abzug an dieser Stelle waere eine Rechnung, die niemand angeordnet
# hat - und sie faende sich spaeter als "die Stunden passen nicht zu den
# Bloecken" wieder.
check("Maske: der Bereich beginnt am Abschnitt, nicht hinter dem Anlauf",
      sm.mask_ranges(LAPS, [600])[0][0][0] if sm.mask_ranges(LAPS, [600])[0] else None,
      600)

# Und der Durchstich: derive.dfa_hours nimmt genau diese Form entgegen.
mask_h = derive.dfa_hours(DFA, WATTS, HR, keep=sm.mask_ranges(LAPS, [600, 1290])[0])
voll_h = derive.dfa_hours(DFA, WATTS, HR)
check("Maske: dfa_hours nimmt die Bereiche unveraendert an",
      (len(mask_h), len(voll_h)), (1, 1))
check("Maske: und schliesst genau die uebrigen Sekunden aus",
      (mask_h[0].get("excluded") if mask_h else None), 2400 - 1200)


# --- 9 · measured_at: 'nie gemessen' gegen 'Auswahl geaendert' -----------------
print("\n=== 9 · die zweite Aussage: schon einmal gemessen ===")

# DER HALBE MECHANISMUS STAND SCHON: set_mark und unset_mark setzen `hours` auf
# None. Was fehlte, ist die UNTERSCHEIDUNG - wer schon gemessen hat, soll nach
# einem Umhaken nicht "noch nicht gemessen" lesen, als waere sein Klick nie
# angekommen (§7, zweiundzwanzigster Fall: ein Zustand ohne Pruefung ist
# gebaut und nicht ausgeliefert).
ma = {"section_marks": {}}
sm.set_mark(ma, "d1", "2026-09-12", "endurance", 0, LAPS, set_at="2026-09-12")
check("Messzustand: vor der ersten Messung steht nichts da",
      sm.entry_for(ma, "d1").get("measured_at"), None)

sm.set_measurement(ma, "d1", hours=[{"hour": 1, "p075": 200}], measured_at="2026-09-15")
check("Messzustand: die Messung haelt fest, WANN",
      sm.entry_for(ma, "d1").get("measured_at"), "2026-09-15")

sm.set_mark(ma, "d1", "2026-09-12", "endurance", 600, LAPS, set_at="2026-09-16")
check("Messzustand: ein weiterer Haken loescht die Zahlen",
      sm.entry_for(ma, "d1").get("hours"), None)
check("Messzustand: aber NICHT die Aussage, dass gemessen wurde",
      sm.entry_for(ma, "d1").get("measured_at"), "2026-09-15")
sm.unset_mark(ma, "d1", "endurance", 600)
check("Messzustand: eine Ruecknahme ebensowenig",
      sm.entry_for(ma, "d1").get("measured_at"), "2026-09-15")
check("Messzustand: bestaetigen nimmt die Zahlen, nicht die Aussage",
      (sm.reanchor(ma, "d1", LAPS).get("hours"),
       sm.entry_for(ma, "d1").get("measured_at")), (None, "2026-09-15"))

# EIN FEHLSCHLAG IST KEINE MESSUNG. Sonst hiesse er spaeter "die Auswahl hat
# sich geaendert", und das waere schlicht falsch.
fehl = {"section_marks": {}}
sm.set_mark(fehl, "d2", "2026-09-12", "tempo", 600, LAPS, set_at="2026-09-12")
sm.set_measurement(fehl, "d2", hours=None, reason="Kein alpha im markierten Bereich.",
                   measured_at="2026-09-15")
check("Messzustand: ein gescheiterter Versuch zaehlt nicht als gemessen",
      sm.entry_for(fehl, "d2").get("measured_at"), None)
check("Messzustand: sein Grund steht aber da",
      sm.entry_for(fehl, "d2").get("reason"), "Kein alpha im markierten Bereich.")
check("Messzustand: eine leere Stundenliste ebenfalls nicht",
      sm.set_measurement(fehl, "d2", hours=[], measured_at="2026-09-15").get("measured_at"),
      None)

# Die beiden Saetze sind ZWEI, und sie kommen aus dem Modul - nicht aus dem
# Frontend (fuenfte Bauregel, 0.52.0).
ok("Messzustand: es gibt einen eigenen Satz fuer 'neu zu messen'",
   isinstance(sm.REMEASURE, str) and sm.REMEASURE != sm.NOT_MEASURED)
ok("Messzustand: und er sagt, dass sich die AUSWAHL geaendert hat",
   "Auswahl" in sm.REMEASURE)

# Der Leseweg nimmt die alte Messung nicht an: sie sass auf einem anderen
# Ausschnitt.
check("Messzustand: nach dem Umhaken gibt usable_hours nichts mehr her",
      sm.usable_hours(sm.entry_for(ma, "d1"), LAPS), None)


# --- 10 · die stillgelegten Familien ------------------------------------------
print("\n=== 10 · Schwelle und lange Fahrt: stillgelegt, nicht verschwiegen ===")

check("Stillgelegt: sie stehen nicht mehr in FAMILIES",
      [name for name in sm.RETIRED if name in sm.FAMILIES], [])
raises("Stillgelegt: das Schreiben nimmt sie nicht mehr an",
       lambda: sm.set_mark({"section_marks": {}}, "e1", "2026-09-12", "long", 0, LAPS),
       "Familie")
raises("Stillgelegt: und die Ruecknahme auch nicht",
       lambda: sm.unset_mark({"section_marks": {}}, "e1", "threshold", 0), "Familie")

# EINE MIGRATION, DIE ETWAS WEGWIRFT, SAGT ES. Die Schleife ueber FAMILIES
# wuerde eine Alt-Marke einfach nicht mitnehmen - der Eintrag saehe danach aus,
# als haette dort nie jemand gehakt. Das ist die Klasse, die dieses Projekt
# mehrfach getroffen hat.
alt = {"e2": {"date": "2026-08-20", "marks": {"endurance": [0], "long": [600]},
              "anchor": {"laps": 5, "sections": [{"i": 0, "s": 600}, {"i": 600, "s": 600}]},
              "hours": [{"hour": 1, "p075": 190}], "reason": "", "set_at": "2026-08-20",
              "v": sm.MEASURE_VERSION}}
nach = sm.migrate(copy.deepcopy(alt))
check("Stillgelegt: die Alt-Marke ist fort", (nach or {}).get("e2", {}).get("marks"),
      {"endurance": [0]})
ok("Stillgelegt: und der Wegfall STEHT DA, statt still zu geschehen",
   sm.RETIRED_REASON in ((nach or {}).get("e2", {}).get("reason") or ""))
check("Stillgelegt: die Messung darauf gilt nicht mehr",
      (nach or {}).get("e2", {}).get("hours"), None)
check("Stillgelegt: die uebrige Familie behaelt ihren Anker",
      [s_.get("i") for s_ in
       (nach or {}).get("e2", {}).get("anchor", {}).get("sections", [])], [0])

# GEGENPROBE: ein Eintrag OHNE stillgelegte Familie bekommt den Satz nicht -
# sonst traegt ihn jede Fahrt und er sagt nichts mehr.
sauber = {"e3": {"date": "2026-08-20", "marks": {"tempo": [600]},
                 "anchor": {"laps": 5, "sections": [{"i": 600, "s": 600}]},
                 "hours": [{"hour": 1, "p075": 190}], "reason": "", "set_at": "2026-08-20",
                 "measured_at": "2026-08-21", "v": sm.MEASURE_VERSION}}
check("Stillgelegt Gegenprobe: eine unberuehrte Fahrt bekommt keinen Satz",
      sm.migrate(copy.deepcopy(sauber)), None)

# DIE EINE LAGE, IN DER ES NICHT SICHTBAR WIRD, und sie ist benannt statt
# uebersehen: trug die Fahrt NUR stillgelegte Familien, faellt der ganze
# Eintrag (P3d - ein Rumpf ist kein Eintrag) und mit ihm der Hinweis. Am
# Bestand vom 15.09.2026 sind das null Fahrten.
nur = {"e4": {"date": "2026-08-20", "marks": {"threshold": [600]},
              "anchor": {"laps": 5, "sections": [{"i": 600, "s": 600}]},
              "hours": None, "reason": "", "set_at": "2026-08-20",
              "v": sm.MEASURE_VERSION}}
check("Stillgelegt: eine Fahrt mit NUR stillgelegten Familien faellt ganz",
      sm.migrate(copy.deepcopy(nur)), {})


print(f"test_section_marks: {CHECKS} Prüfungen, {len(FAILURES)} Fehler")
for failure in FAILURES:
    print("   ✗ " + failure)
print("FEHLER: keine" if not FAILURES else "")
sys.exit(1 if FAILURES else 0)
