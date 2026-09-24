"""Die Ermuedungsrechnung v2 prueft sich selbst.
Lauf: python3 tests/test_fatigue_v2.py

Geprueft wird, was die Kachel behauptet: die Kette, das Band mit seinen zwei
Anteilen, der Verlauf, der Cluster-Waechter und die Gruppen. Zu jeder Aussage
gehoert eine Gegenprobe - eine Welt, in der das Ergebnis NICHT eintreten darf.
"""
import sys
from pathlib import Path

import coldcache  # noqa: F401  - MUSS vor jedem Bauteil-Import stehen (§9)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                      / "custom_components" / "intervals_icu"))

import derive  # noqa: E402
import fatigue  # noqa: E402  - die Studienform der Kette kommt von dort
import fatigue_v2 as v2  # noqa: E402
from const import STEERING_T90  # noqa: E402

CHECKS = 0
failures: list[str] = []


def check(name, got, want):
    global CHECKS
    CHECKS += 1
    if got == want:
        print(f"PASS  {name}: {got}")
    else:
        print(f"FAIL  {name}: {got}  (erwartet {want})")
        failures.append(name)


# ---------------------------------------------------------------------------
# DER SCHALTER. Aus ist die Vorgabe, und aus kostet nichts.
check("Schalter: ohne Einstellungen ist er aus", v2.v2_on({}), False)
check("Schalter: aus liefert Fensterbreite null", v2.watt_window({}), 0)
check("Schalter: an liefert Andriolos 120 s",
      v2.watt_window({"settings": {v2.V2_SWITCH: True}}), 120)
check("Schalter: umgedreht ist wirklich umgedreht",
      v2.v2_on(v2.flipped({"settings": {v2.V2_SWITCH: True}})), False)
check("Schalter: das Umdrehen laesst den Bestand in Ruhe",
      v2.flipped({"activities": {"a": 1}, "settings": {}})["activities"], {"a": 1})
# 0.63.1: die Zahlen stehen nicht mehr im Satz, sondern kommen aus dem
# Bestand - und der Satz TRENNT: eingelesen wird alles mit alpha-Daten,
# gerechnet wird mit den markierten Fahrten. Der alte Text las sich, als
# liefen alle 58 in die Kurve.
check("Der Hinweis fuehrt keine Zahl als Text",
      any(ch.isdigit() for ch in v2.SWITCH_NOTE.replace("120", "").replace("0,75", "")), False)
check("Der Hinweis trennt Einlesen von Rechnen",
      ("EINGELESEN" in v2.SWITCH_NOTE and "FÜR DIE KURVE" in v2.SWITCH_NOTE), True)
check("Der Hinweis sagt, was sich NICHT aendert",
      "bleiben unberührt" in v2.SWITCH_NOTE, True)
_hin = v2.switch_note({"activities": {}, "dfa": {}, "section_marks": {},
                       "settings": {}}, rides=60, batch=25)
check("Der Hinweis nennt die Neumessung mit Zahlen aus dem Bestand",
      ("60 Fahrten werden neu EINGELESEN" in _hin and "also 3 Abgleiche" in _hin), True)
check("Der Hinweis nennt die Zahl der Fahrten, die die Kurve tragen",
      "nur deine 0 markierten Fahrten" in _hin, True)
# Gegenprobe: ein anderer Bestand, andere Zahlen - sonst prueft die Zeile oben
# nur, dass ueberhaupt Text herauskommt.
_hin2 = v2.switch_note({"activities": {}, "dfa": {}, "section_marks": {},
                        "settings": {}}, rides=26, batch=25)
check("Der Hinweis Gegenprobe: andere Zahlen schlagen durch",
      ("26 Fahrten" in _hin2 and "also 2 Abgleiche" in _hin2), True)

# ---------------------------------------------------------------------------
# DIE WATTACHSE, EINE REGEL. Bis 0.63.0 kannte nur der Importweg den
# Rechenschalter; der Messweg der Markierungen mass ungefenstert weiter. Stand
# der Kurvenschalter auf "meine Markierungen" - so steht er bei Johannes -,
# hatte der Rechenschalter GAR KEINE Wirkung auf die Kurve, und beide Achsen
# lagen unter demselben Versionszaehler im selben Archiv.
import section_marks as sm  # noqa: E402

AUS = {"settings": {}}
AN = {"settings": {v2.V2_SWITCH: True}}
check("Achse: aus ist die Breite null", derive.watt_window(AUS), 0)
check("Achse: an ist sie die Fensterbreite", derive.watt_window(AN), derive.DFA_WATT_WINDOW_S)
check("Achse: fatigue_v2 reicht durch, es gibt keine zweite Fassung",
      (v2.watt_window(AUS), v2.watt_window(AN)),
      (derive.watt_window(AUS), derive.watt_window(AN)))
check("Achse: der Schluessel des Schalters steht in derive",
      v2.V2_SWITCH, derive.DFA_WATT_WINDOW_SETTING)

# FESTGEHALTENE SOLLWERTE. Sie ueberleben den Wegfall des Schalters: "aus =
# wie heute" ist dann kein Bezugspunkt mehr, diese Zahlen schon. Gerechnet am
# echten 1-Hz-Strom des Stufentests vom 16.09.2026.
import json  # noqa: E402
_STROM = json.loads((Path(__file__).resolve().parent / "data"
                     / "ramp_i187258578.json").read_text(encoding="utf-8"))
_A, _W, _H = _STROM["alpha1"], _STROM["watts"], _STROM["heartrate"]
_aus = derive.dfa_hours(_A, _W, _H, watt_window_s=0)[0]
_an = derive.dfa_hours(_A, _W, _H, watt_window_s=derive.DFA_WATT_WINDOW_S)[0]
check("Sollwert aus: p075", _aus["p075"], 169.9)
check("Sollwert aus: r2", _aus["r2"], 0.603)
check("Sollwert aus: load_w / load_n", (_aus["load_w"], _aus["load_n"]), (143.0, 401))
check("Sollwert an: p075", _an["p075"], 179.1)
check("Sollwert an: r2", _an["r2"], 0.81)
check("Sollwert an: load_w / load_n", (_an["load_w"], _an["load_n"]), (140.6, 519))
# DIE HF-SEITE FAELLT NICHT MIT - sie sitzt auf (alpha, Puls), da kommen keine
# Watt vor. Das ist die Haelfte der Kurve, die das Umlegen nicht anfasst.
check("Sollwert: hr075 ist in beiden Stellungen dieselbe Zahl",
      _aus["hr075"], _an["hr075"])
check("Fixture-Beweis: die beiden Stellungen unterscheiden sich wirklich",
      _aus["p075"] != _an["p075"], True)

# DIE FENSTERBREITE REIST MIT DER MESSUNG. Ohne dieses Feld sieht eine
# Messung von vorher aus wie eine von jetzt.
# Ein Geruest von Hand - `importer` zieht Home Assistant in den Lauf.
# Der Kurvenschalter steht AN ("meine Markierungen"), denn genau dort
# sass der Fehler.
_md = {"activities": {"M1": {"start_date_local": "2026-09-10T08:00:00",
                            "name": "volumen", "moving_time": 7200}},
       "section_marks": {}, "dfa": {},
       "settings": {fatigue.CURVE_SWITCH: True}}
sm.set_mark(_md, "M1", "2026-09-10", "endurance", 0,
            [{"n": 0, "start_index": 0, "end_index": 60, "moving_time": 60}])
sm.set_measurement(_md, "M1", family="endurance",
                   hours=[{"hour": 1, "p075": 150.0}], window_s=120)
check("Messung: die Breite steht im Eintrag",
      sm.window_of(sm.entry_for(_md, "M1"), "endurance"), 120)
check("Messung: ein Eintrag ohne das Feld gilt als ungefenstert",
      sm.window_of({"measure": {"endurance": {"hours": [1]}}}, "endurance"), 0)
check("Messung: die Versionsmarke steht auf 4",
      sm.entry_for(_md, "M1")["v"], sm.MEASURE_VERSION)
# DER VERSIONSZAEHLER MUSSTE STEIGEN. Die Stundenzeile traegt seit v2 die
# Ablesestelle (`load_*`); Messungen von vorher haben diese Felder gar nicht -
# am Livebestand stand die v2-Kachel deshalb auf NULL Fahrten, obwohl zwoelf
# markierte Fahrten gemessen waren. Geprueft wird das Verhalten, nicht die
# Zahl: eine Messung der VORIGEN Marke muss beim Laden fallen.
# DIE GUELTIGKEIT HAENGT AN `w`, NICHT AN `v` (0.63.3). In 0.63.1 hing sie am
# Versionszaehler, und das BLOSSE EINSPIELEN hat Johannes 17 Messungen
# geloescht - bei AUSGESCHALTETEM Schalter, fuer eine Aenderung, die fuer ihn
# gar nicht stattfand.
_OHNE_W = {"hours": [{"hour": 1, "p075": 150.0}], "blocks": None, "reason": ""}
_EINTRAG = {"date": "2026-09-10", "marks": {"endurance": [0]},
            "anchor": {"laps": 1, "sections": [{"i": 0, "s": 60}]},
            "measured_at": "2026-09-10", "set_at": "2026-09-10"}
def _bestand(measure, v, an):
    return {"activities": {"A1": {"start_date_local": "2026-09-10T08:00:00",
                                  "name": "volumen", "moving_time": 7200}},
            "dfa": {}, "section_marks": {"A1": {**_EINTRAG, "measure": measure, "v": v}},
            "settings": {fatigue.CURVE_SWITCH: True, **({v2.V2_SWITCH: True} if an else {})}}

_aus = fatigue.rides(_bestand({"endurance": _OHNE_W}, 3, False))
check("Schalter aus + Messung ohne w: sie GILT",
      [r["activity_id"] for r in _aus["used"]], ["A1"])
check("Schalter aus + Messung ohne w: keine Meldung", _aus["dropped"], {})
_an = fatigue.rides(_bestand({"endurance": _OHNE_W}, 3, True))
check("Schalter an + Messung ohne w: sie faellt",
      [r["activity_id"] for r in _an["used"]], [])
check("Schalter an + Messung ohne w: mit remeasure_window",
      list(_an["dropped"]), [fatigue.WINDOW_CHANGED_REASON])

# DER WAECHTER GEGEN DIE NAECHSTE AUSLIEFERUNG, DIE DATEN LOESCHT.
# Die Marke steht hier als LITERAL und nicht als sm.MEASURE_VERSION: wird der
# Zaehler hochgezogen, faellt diese Pruefung - und genau das soll sie.
# Johannes' frisch gemessene Eintraege tragen `v: 4` aus 0.63.2; sie duerfen
# durch die Ruecknahme NICHT fallen, deshalb der zweite Fall.
for _marke, _wort in ((3, "unter der heutigen Marke"), (4, "unter einer neueren Marke")):
    _block = {"A1": {**_EINTRAG, "measure": {"endurance": dict(_OHNE_W)}, "v": _marke}}
    _nach = sm.migrate(_block) or _block
    check(f"Einspielen ({_wort}): die Messung bleibt stehen",
          bool(_nach["A1"]["measure"].get("endurance")), True)
    check(f"Einspielen ({_wort}): kein Verwerfungsgrund wird gesetzt",
          _nach["A1"].get("lost"), None)
    check(f"Einspielen ({_wort}): die Marke wird nicht nach unten geschrieben",
          _nach["A1"]["v"] >= _marke, True)
# Eine WIRKLICH aeltere Messung faellt weiter - der Zaehler bleibt scharf fuer
# das, wofuer er da ist (Fall 2: nachweislich falsch gerechnet).
_alt = {"A1": {**_EINTRAG, "measure": {"endurance": dict(_OHNE_W)}, "v": 1}}
_nach_alt = sm.migrate(_alt) or _alt
check("Einspielen: eine wirklich aeltere Messung faellt",
      _nach_alt["A1"]["measure"], {})
check("Einspielen: mit Grund", _nach_alt["A1"].get("lost"), sm.LOST_VERSION)
check("Einspielen: die Marken bleiben in jedem Fall stehen",
      _nach_alt["A1"]["marks"], {"endurance": [0]})

# UND DER LESEWEG NIMMT SIE NICHT MIT, wenn die Achse nicht stimmt.
_raus = fatigue.rides({**_md, "settings": {fatigue.CURVE_SWITCH: True}})
check("Leseweg: die 120er-Messung zaehlt bei ausgeschalteter Rechnung NICHT",
      [r["activity_id"] for r in _raus["used"]], [])
check("Leseweg: und sie wird mit EIGENEM Grund benannt",
      list(_raus["dropped"]), [fatigue.WINDOW_CHANGED_REASON])
_rein = fatigue.rides({**_md, "settings": {fatigue.CURVE_SWITCH: True, v2.V2_SWITCH: True}})
check("Leseweg: mit eingeschalteter Rechnung zaehlt sie",
      [r["activity_id"] for r in _rein["used"]], ["M1"])
check("Leseweg Gegenprobe: dann ist nichts verworfen", _rein["dropped"], {})
check("Grund: er hat ein Wort und einen Satz",
      all(fatigue.DROPPED_WORDS[fatigue.WINDOW_CHANGED_REASON]), True)
check("Grund: er ist NICHT der Versionssprung",
      fatigue.WINDOW_CHANGED_REASON != fatigue.LOST_REASON[sm.LOST_VERSION], True)

# ---------------------------------------------------------------------------
# DIE KETTE: Anker Stunde 1, danach der gemessene Verlauf. Die Formelzeile
# unter der Zahl muss die Zahl ergeben - das ist der ganze Grund fuer B.
BY_HOUR = {1: {"alpha": 1.330, "n": 18, "sd": 0.120},
           2: {"alpha": 1.260, "n": 13, "sd": 0.086},
           3: {"alpha": 1.143, "n": 4, "sd": 0.076},
           4: {"alpha": 1.050, "n": 3, "sd": 0.208}}
kette = v2.chain(156.6, BY_HOUR)
gemessen = [row for row in kette if row["measured"]]
geschaetzt = [row for row in kette if not row["measured"]]
check("Kette: Anker plus Verlauf, Stunde fuer Stunde",
      [(row["hours"], row["watts"]) for row in gemessen],
      [(1, 156.6), (2, 154.2), (3, 151.8), (4, 149.4)])
check("Kette: die Formelzeile ergibt die Zahl",
      round(156.6 - 3 * v2.BRIDGE_FLAT, 1), gemessen[-1]["watts"])
check("Kette: ohne Anker gibt es keine Kette", v2.chain(None, BY_HOUR), [])
check("Kette: alpha reist je Stunde mit",
      [row["alpha"] for row in gemessen], [1.330, 1.260, 1.143, 1.050])

# ---------------------------------------------------------------------------
# DIE SCHAETZUNG JENSEITS DES BESTANDS. Zwei Reihen, beide HIER gerechnet: die
# Fortschreibung des eigenen Schritts und die Studienform an Stunde 1. Das
# Panel rechnet keine von beiden nach - wenn eine Zahl dort entsteht, gibt es
# zwei Wahrheiten.
check("Schaetzung: die Kette reicht bis zum Horizont",
      [row["hours"] for row in kette], list(range(1, v2.PLAN_HORIZON_HOURS + 1)))
check("Schaetzung: sie beginnt hinter der letzten gemessenen Stunde",
      geschaetzt[0]["hours"], max(BY_HOUR) + 1)
check("Schaetzung: die Fortschreibung setzt den eigenen Schritt fort",
      [row["watts"] for row in geschaetzt],
      [round(156.6 - (h - 1) * v2.BRIDGE_FLAT, 1)
       for h in range(max(BY_HOUR) + 1, v2.PLAN_HORIZON_HOURS + 1)])
check("Schaetzung: die Studienform haengt an Stunde 1",
      geschaetzt[0]["form_watts"],
      round(156.6 / fatigue.literature_factor(1.0)
            * fatigue.literature_factor(float(geschaetzt[0]["hours"])), 1))
# KEINE SCHAETZUNG DARF ALS MESSUNG DURCHGEHEN. Drei Merkmale, einzeln:
# kein Band, keine Belegung, und die Kennzeichnung selbst.
check("Schaetzung: kein Band - es gibt nichts zu streuen",
      [row["band"] for row in geschaetzt], [None] * len(geschaetzt))
check("Schaetzung: keine Belegung", {row["n"] for row in geschaetzt}, {0})
check("Schaetzung: kein alpha", {row["alpha"] for row in geschaetzt}, {None})
check("Schaetzung: als geschaetzt gekennzeichnet",
      {row["measured"] for row in geschaetzt}, {False})
# Trefferzusicherung: die gemessenen Zeilen tragen sehr wohl ein Band - sonst
# prueften die vier Zeilen oben nur, dass ueberall nichts steht.
check("Schaetzung Fixture-Beweis: die gemessenen Stunden tragen Baender",
      all(row["band"] is not None for row in gemessen), True)
# WELCHE DER BEIDEN DIE VORSICHTIGE IST, steht als ZAHL fest. Heute faellt
# Johannes flacher als die Studie, also liegt die Studienform tiefer.
check("Schaetzung: heute liegt die Studienform tiefer",
      {row["lower"] for row in geschaetzt}, {"form"})
check("Schaetzung: gemessene Stunden kennen die Frage nicht",
      {row["lower"] for row in gemessen}, {None})
# RANDFALL: wird der eigene Abfall steiler als die Studie, kippt `lower` - und
# der Satz auf der Kachel kippt mit, ohne dass jemand ihn umschreibt.
steil = [row for row in v2.chain(156.6, BY_HOUR, step_watts=12.0) if not row["measured"]]
check("Schaetzung Randfall: bei steilerem Abfall liegt die Fortschreibung tiefer",
      {row["lower"] for row in steil}, {"chain"})
check("Schaetzung Randfall Fixture-Beweis: der steile Fall dreht die Reihenfolge wirklich",
      steil[0]["watts"] < steil[0]["form_watts"], True)

# DAS NACHWACHSEN. Kommt eine 6-Stunden-Fahrt dazu, waechst der gemessene
# Bereich auf 6 h und die Schaetzung rueckt auf 7-8 h - ohne dass eine Grenze
# im Code steht.
LANG = dict(BY_HOUR)
LANG[5] = {"alpha": 0.980, "n": 2, "sd": 0.150}
LANG[6] = {"alpha": 0.910, "n": 2, "sd": 0.160}
lang = v2.chain(156.6, LANG)
check("Nachwachsen: der gemessene Bereich waechst auf sechs Stunden",
      [row["hours"] for row in lang if row["measured"]], [1, 2, 3, 4, 5, 6])
check("Nachwachsen: die Schaetzung rueckt auf sieben und acht",
      [row["hours"] for row in lang if not row["measured"]], [7, 8])
check("Nachwachsen: die neue Stunde traegt ein Band",
      lang[5]["band"] is not None, True)
# GEGENPROBE: ohne die lange Fahrt bleibt alles, wie es ist.
check("Nachwachsen Gegenprobe: ohne die lange Fahrt endet der Bestand bei vier",
      [row["hours"] for row in gemessen], [1, 2, 3, 4])

# ---------------------------------------------------------------------------
# DAS BAND, zwei Anteile. Bei Stunde 1 ist die Umrechnung noch nicht im Spiel -
# das ist die Gegenprobe gegen einen Anteil, der aus dem Nichts kommt.
band1 = v2.band(1, BY_HOUR[1])
check("Band: bei Stunde 1 traegt die Umrechnung nichts bei",
      band1["from_bridge"], 0.0)
check("Band: bei Stunde 1 ist die Spanne reine Streuung",
      band1["half"], band1["from_spread"])
check("Band: die Spanne je Stunde",
      [v2.band(h, BY_HOUR[h])["half"] for h in (1, 2, 3, 4)],
      [5.1, 5.0, 8.0, 16.9])
# Bei Stunde 4 stehen beide Anteile nebeneinander, und keiner ist zu
# vernachlaessigen: 13,5 W aus der Streuung ueber drei Fahrten, 10,2 W aus der
# Umrechnung. Wer einen davon weglaesst, zeigt eine zu schmale Spanne.
check("Band: bei Stunde 4 tragen beide Anteile spuerbar",
      (v2.band(4, BY_HOUR[4])["from_spread"], v2.band(4, BY_HOUR[4])["from_bridge"]),
      (13.5, 10.2))
check("Band: unter zwei Fahrten gibt es keine Toleranz",
      v2.band(2, {"alpha": 1.2, "n": 1, "sd": 0.0}), None)
check("Band: keine Streuung heisst nicht keine Spanne - die Umrechnung bleibt",
      v2.band(4, {"alpha": 1.2, "n": 3, "sd": 0.0})["half"], 10.2)
check("Band: die t-Tabelle ist DIESELBE wie bei den Familien",
      v2.T90 is STEERING_T90, True)

# ---------------------------------------------------------------------------
# DER VERLAUF. Je Fahrt ein Schritt, nicht je Stundenpaar.
def _ride(name, alphas, start=1):
    return {"activity_id": name, "date": name,
            "hours": [{"hour": start + i, "alpha": a, "n": 50, "load_w": 140.0}
                      for i, a in enumerate(alphas)],
            "first": alphas[0], "last": alphas[-1],
            "span": len(alphas) - 1, "carries_trend": len(alphas) >= 2}


ROWS = [_ride("a", [1.30, 1.20]), _ride("b", [1.30, 1.10]),
        _ride("c", [1.30, 1.25, 1.10]), _ride("d", [1.40])]
tr = v2.decline(ROWS)
check("Verlauf: nur Fahrten mit Verlauf zaehlen", tr["n"], 3)
check("Verlauf: eine lange Fahrt zaehlt EINMAL, nicht je Stundenpaar",
      tr["alpha_per_hour"], -0.1)
check("Verlauf: gezaehlt wird auch, wie viele fallen", tr["falling"], 3)
check("Verlauf: GEGENPROBE - ohne Abfall kommt null heraus",
      v2.decline([_ride("x", [1.30, 1.30]), _ride("y", [1.20, 1.20])])["alpha_per_hour"],
      0.0)
check("Verlauf: GEGENPROBE - ohne Fahrt mit zwei Stunden gibt es keinen Verlauf",
      v2.decline([_ride("z", [1.30])])["alpha_per_hour"], None)

# ---------------------------------------------------------------------------
# DER CLUSTER-WAECHTER. Eine Stunde ohne Punkte im Ableseort bekommt keine
# Zahl - das ist der 20.08., an dem der Fit 187,4 W aus null Punkten machte.
DATA = {"activities": {}, "dfa": {}, "settings": {}}
leer = {"used": [{"activity_id": "i1", "date": "2026-08-20",
                  "hours": [{"hour": 1, "load_alpha": None, "load_n": 3,
                             "load_w": 152.1}]}]}
_echt = fatigue.rides
try:
    fatigue.rides = lambda data: leer
    check("Waechter: eine Stunde ohne Punkte liefert gar keine Fahrt",
          v2.reading_rows(DATA), [])
    voll = {"used": [{"activity_id": "i1", "date": "2026-08-20",
                      "hours": [{"hour": 1, "load_alpha": 1.43, "load_n": 286,
                                 "load_w": 152.1},
                                {"hour": 2, "load_alpha": None, "load_n": 3,
                                 "load_w": 152.1}]}]}
    fatigue.rides = lambda data: voll
    rows = v2.reading_rows(DATA)
    check("Waechter: die belegte Stunde bleibt, die leere faellt weg",
          [h["hour"] for h in rows[0]["hours"]], [1])
    check("Waechter: eine einzige Stunde traegt keinen Verlauf",
          rows[0]["carries_trend"], False)
finally:
    fatigue.rides = _echt

# ---------------------------------------------------------------------------
# DIE GRUPPEN.
gr = v2.groups(ROWS, 3)
check("Gruppen: wer den Verlauf traegt", len(gr["carries"]), 3)
check("Gruppen: wer nur die Hoehe stuetzt", len(gr["supports"]), 1)
check("Gruppen: die Fahrt ohne Verlauf ist die kurze",
      gr["supports"][0]["date"], "d")
check("Gruppen: je Fahrt steht alpha von und bis da",
      (gr["carries"][0]["alpha_from"], gr["carries"][0]["alpha_to"]), (1.30, 1.20))

# ---------------------------------------------------------------------------
# DIE SETZUNGEN stehen woertlich da und werden nicht stillschweigend weniger.
# 0.64.0: die Grenze alpha 1,0 kommt als siebte dazu. Gezaehlt wird gegen
# die Liste selbst, nicht gegen eine Zahl im Test.
check("Setzungen: jede traegt einen Satz",
      all(isinstance(x, str) and x.strip() for x in v2.SETTINGS_NOTE), True)
check("Setzungen: sie sind paarweise verschieden",
      len(set(v2.SETTINGS_NOTE)), len(v2.SETTINGS_NOTE))
check("Setzungen: die Grenze der Umkehrung steht darin",
      any("alpha 1,0" in x for x in v2.SETTINGS_NOTE), True)
check("Setzungen: der Stundenschnitt ist als quellenlos benannt",
      any("keine Quelle" in line for line in v2.SETTINGS_NOTE), True)
# 0.67.0: die Umrechnung ist eine Setzung aus dem Stufentest - die alte Zeile
# ("0,9 bis 7,7 W je Stunde", zwei Verfahren) beschrieb die gemittelten Bruecken.
check("Setzungen: die Umrechnung steht als Setzung aus dem Stufentest da",
      any("Stufentest" in line and "Setzung" in line for line in v2.SETTINGS_NOTE), True)
check("Setzungen: die quadratische Zusammenlegung ist benannt",
      any("quadratisch" in line for line in v2.SETTINGS_NOTE), True)

print()
# ---------------------------------------------------------------------------
# DIE UMKEHRUNG (0.64.0): die Mindestbelegung und die Zusammensetzung des Bands.
# Beides sind Entscheidungen, keine Nebenwirkungen - also werden sie geprueft.
# Gerechnet wird mit der PRODUKTIONSFUNKTION, nicht mit einem Nachbau im Test -
# sonst prueft die Suite ihre eigene Kopie und nicht das, was ausgeliefert wird.
# Seit 0.64.3 gehen die FERTIGEN Wattzahlen hinein, nicht die alphas.
def _zahlen(alphas, last=139.6, bruecke=101.2):
    return [last + (a - v2.ALPHA_FLOOR) * bruecke for a in alphas]
check("Umkehrung: die Mindestbelegung steht auf vier", v2.MIN_RIDES_FOR_BAND, 4)
check("Umkehrung: die Grenze steht auf 1,0", v2.ALPHA_FLOOR, 1.0)
check("Umkehrung: drei Fahrten tragen KEIN Band",
      v2.reversal_band(_zahlen([1.20, 1.25, 1.30]), 2.0), None)
_b = v2.reversal_band(_zahlen([1.20, 1.25, 1.30, 1.35]), 2.0)
check("Umkehrung Gegenprobe: vier Fahrten tragen eines", _b is not None, True)
# DAS BAND HAT ZWEI ANTEILE, und sie stehen getrennt: die Streuung ZWISCHEN DEN
# FAHRTEN (sie enthaelt jetzt Last UND alpha) und der systematische Abstand der
# beiden Umrechnungen.
check("Umkehrung Band: Fahrten und Umrechnung sind beide darin",
      (_b["from_spread"] > 0, _b["from_bridge"] > 0), (True, True))
check("Umkehrung Band: quadratisch zusammengelegt",
      _b["half"] > _b["from_spread"], True)
_ohne = v2.reversal_band(_zahlen([1.20, 1.25, 1.30, 1.35]), 0.0)
check("Umkehrung Band Fixture-Beweis: ohne Umrechnungsanteil ist es schmaler",
      _ohne["half"] < _b["half"], True)
# DIE STREUUNG DER LAST GEHT MIT EIN - das war der Fehler bis 0.64.2. Zwei
# Bestaende mit DEMSELBEN alpha, aber verschieden streuender Last, muessen
# verschiedene Baender ergeben.
_gleich = v2.reversal_band([170.0, 172.0, 174.0, 176.0], 0.0)
_streut = v2.reversal_band([150.0, 165.0, 180.0, 195.0], 0.0)
check("Umkehrung Band: streuende Last verbreitert es",
      _streut["half"] > _gleich["half"] * 2, True)
# DIE TABELLENSEITE: zweiseitig, nicht einseitig. Geprueft am Wert selbst,
# damit ein Zurueckdrehen auf STEERING_T90 auffaellt.
check("Umkehrung Band: das t-Quantil ist das ZWEISEITIGE",
      v2.T90_TWO_SIDED[3] > STEERING_T90[3], True)
_glatt = v2.reversal_band([170.0, 172.0, 174.0, 176.0], 0.0)
_sd = (sum((x - 173.0) ** 2 for x in [170.0, 172.0, 174.0, 176.0]) / 3) ** 0.5
check("Umkehrung Band: und es wird auch benutzt",
      _glatt["from_spread"],
      round(v2.T90_TWO_SIDED[3] * _sd * (1 + 1 / 4) ** 0.5, 1))
# DIE QUOTE STEHT NUR DA, WO SIE NACHPRUEFBAR IST.
check("Umkehrung Band: unter neun Fahrten keine Quote", _b["quote_shown"], False)
# WAS DER KETTE UEBERGEBEN WIRD, ist die zweite Haelfte der Reparatur: eine
# Pruefung der Funktion allein faengt nicht, wenn der Aufrufer wieder alphas
# schickt. Deshalb am SYNTAXBAUM, wie beim Fensterbreiten-Waechter.
import ast as _ast  # noqa: E402
_baum = _ast.parse((Path(__file__).resolve().parents[1] / "custom_components"
                    / "intervals_icu" / "fatigue_v2.py").read_text(encoding="utf-8"))
_rufe = [n for n in _ast.walk(_baum)
         if isinstance(n, _ast.Call) and isinstance(n.func, _ast.Name)
         and n.func.id == "reversal_band"]
check("Umkehrung Band: genau ein Aufruf in der Kette", len(_rufe), 1)
_arg = _ast.dump(_rufe[0].args[0]) if _rufe and _rufe[0].args else ""
check("Umkehrung Band: die FERTIGEN Wattzahlen gehen hinein, nicht die alphas",
      ("ALPHA_FLOOR" in _arg and _arg.count("BinOp") >= 2), True)
check("Umkehrung Band Fixture-Beweis: der Wortlaut kommt im Aufruf wirklich vor",
      "ALPHA_FLOOR" in _arg, True)
check("Umkehrung Band Gegenprobe: ab neun schon",
      v2.reversal_band(_zahlen([1.2 + i * 0.01 for i in range(9)]), 0.0)["quote_shown"], True)


# ---------------------------------------------------------------------------
# DER TROCKENLAUF. Er rechnet beide Wattachsen aus denselben Stroemen und
# fasst das Archiv NICHT an - das ist die eine Zusicherung, die er geben muss,
# und sie wird erzwungen statt behauptet.
import copy  # noqa: E402
_TROCKEN = {"activities": {"T1": {"start_date_local": "2026-09-16T08:00:00",
                                  "name": "volumen", "moving_time": 7200,
                                  "icu_zone_times": [{"id": "Z1", "secs": 3600}, {"id": "Z2", "secs": 3600}]}},
            "dfa": {}, "section_marks": {}, "settings": {}}
_VORHER = copy.deepcopy(_TROCKEN)
_erg = v2.dry_run(_TROCKEN, {"T1": {"dfa_a1": _A, "watts": _W, "heartrate": _H}})
check("Trockenlauf: das Archiv ist unveraendert", _TROCKEN, _VORHER)
_std = _erg["rides"][0]["hours"][0]
check("Trockenlauf: beide Achsen stehen nebeneinander",
      (_std["p075"]["off"], _std["p075"]["on"]), (169.9, 179.1))
check("Trockenlauf: die Ablesestelle auch",
      (_std["load_n"]["off"], _std["load_n"]["on"]), (401, 519))
check("Trockenlauf: die HF-Seite steht in beiden Spalten gleich",
      _std["hr075"]["off"], _std["hr075"]["on"])
check("Trockenlauf: alle sieben Felder sind da", sorted(_erg["fields"]), sorted(v2.DRY_FIELDS))
check("Trockenlauf: beide Kachelseiten kommen zurueck", sorted(_erg["tiles"]), ["off", "on"])
check("Trockenlauf: die Breiten stehen dran",
      (_erg["tiles"]["off"]["window_s"], _erg["tiles"]["on"]["window_s"]),
      (0, derive.DFA_WATT_WINDOW_S))
check("Trockenlauf: die Kopfzahl der Kurve unterscheidet sich zwischen beiden",
      _erg["tiles"]["off"]["anchor_watts"] != _erg["tiles"]["on"]["anchor_watts"], True)
# 0.64.0/0.64.1: der Trockenlauf zeigt, was die KACHEL zeigt - die Umkehrung.
check("Trockenlauf: beide Seiten tragen die Umkehrung",
      [("reversal" in _erg["tiles"][k]) for k in ("off", "on")], [True, True])
# OHNE BRUECKE KEINE WATTZAHL. Dieser Bestand hat weder Stufentest noch
# Bloecke - dann bleibt die Kette leer, statt eine Umrechnung zu erfinden.
# 0.67.0: ohne Bruecke bleibt der VERLAUF IN ALPHA - eine Zeile je belegter
# Stunde, ohne Watt. Vorher war die Kette leer.
check("Trockenlauf ohne Bruecke: der alpha-Verlauf bleibt, ohne Watt",
      [[r.get("watts") for r in ((_erg["tiles"][k].get("reversal") or {}).get("plan") or [])] for k in ("off", "on")], [[None], [None]])
check("Trockenlauf ohne Bruecke: und keine Umrechnung",
      ((_erg["tiles"]["on"].get("reversal") or {}).get("bridges") or {}).get("mid"), None)
# MIT Stufentest entsteht sie. Die Kette reicht dann bis zum Horizont.
_MIT = {**_TROCKEN, "ramp_tests": {"T1": {
    "activity_id": "T1", "date": "2026-09-16", "set_at": "2026-09-16", "v": 2,
    "result": {"hrvt1": {"alpha": 0.75, "watts": 213.0},
               "hrvt1_pers": {"alpha": 1.081, "watts": 183.0}}}}}
_ergM = v2.dry_run(_MIT, {"T1": {"dfa_a1": _A, "watts": _W, "heartrate": _H}})
_rvM = _ergM["tiles"]["on"].get("reversal") or {}
check("Trockenlauf mit Bruecke: die Umrechnung steht da",
      (_rvM.get("bridges") or {}).get("ramp"), round(abs((213.0 - 183.0) / (1.081 - 0.75)), 1))
check("Trockenlauf mit Bruecke: die gemessene Stunde traegt eine Zahl",
      (len(_rvM.get("plan") or []), (_rvM.get("plan") or [{}])[0].get("hours"),
       (_rvM.get("plan") or [{}])[0].get("observed")),
      (1, 1, True))
check("Trockenlauf mit Bruecke: die Zahl ergibt sich aus Last, alpha und Umrechnung",
      (_rvM.get("plan") or [{}])[0].get("watts"),
      round((_rvM.get("plan") or [{"load_w": 0, "alpha": 1.0}])[0]["load_w"]
            + ((_rvM["plan"][0]["alpha"] - v2.ALPHA_FLOOR)
               * (_rvM.get("bridges") or {}).get("mid", 0)), 1) if _rvM.get("plan") else None)
# EINE STUNDE TRAEGT KEINE FORTSCHREIBUNG. Eine Gerade durch einen Punkt gibt
# es nicht, also endet die Kette dort - statt eine Richtung zu erfinden.
check("Trockenlauf: eine einzige Stunde wird nicht fortgeschrieben",
      (_rvM.get("slope_per_hour"), _rvM.get("covered_until_hours")), (None, 1))
check("Trockenlauf mit Bruecke: die Studienform steht auch an der einen Zeile",
      bool(_rvM.get("plan")) and _rvM["plan"][0]["form_watts"] is not None, True)
# DIE LUECKE VON 0.64.0, geschlossen: der Trockenlauf hatte seine eigene Liste
# der Kachelzahlen und trug deshalb nach dem Umbau weiter die alte Kette. Jetzt
# ruft er `tile_numbers`, und diese Pruefung haelt seine Ausgabe GEGEN einen
# direkten Aufruf auf demselben Bestand - Feld fuer Feld.
for _seite, _w in (("off", 0), ("on", derive.DFA_WATT_WINDOW_S)):
    _schein = v2._shadow(_TROCKEN, {"T1": derive.dfa_hours(_A, _W, _H, watt_window_s=_w)}, _w)
    _direkt = v2.tile_numbers(_schein)
    _direkt["window_s"] = _w
    check(f"Trockenlauf {_seite}: dieselben Kachelzahlen wie ein direkter Aufruf",
          _erg["tiles"][_seite], _direkt)
# Trefferzusicherung: die beiden Seiten sind NICHT gleich - sonst prueft die
# Zeile oben nur, dass zweimal dasselbe herauskommt.
check("Trockenlauf Fixture-Beweis: die Stellungen unterscheiden sich",
      _erg["tiles"]["off"] != _erg["tiles"]["on"], True)
# Und jedes Feld, das die Kachel liest, ist auch da.
for _feld in ("alpha_floor", "floor_step_watts", "min_rides_for_band",
              "covered_until_hours", "slope_per_hour", "bridges", "plan",
              "groups", "rides"):
    check(f"Trockenlauf: die Umkehrung traegt '{_feld}'",
          _feld in (_erg["tiles"]["on"].get("reversal") or {}), True)
# Er haengt NICHT am Schalter: derselbe Bestand mit umgelegtem Schalter gibt
# dieselben zwei Spalten. Sonst waere er nach dem Wegfall der Schalter nutzlos.
_erg2 = v2.dry_run({**_TROCKEN, "settings": {v2.V2_SWITCH: True}},
                   {"T1": {"dfa_a1": _A, "watts": _W, "heartrate": _H}})
check("Trockenlauf: die Schalterstellung aendert sein Ergebnis nicht",
      _erg2["rides"], _erg["rides"])
check("Trockenlauf: auch die Kachelzahlen nicht", _erg2["tiles"], _erg["tiles"])



# ============ B · EINE STELLE, ZWEI QUANTILE (0.66.0) ============
# Bis 0.65.2 fuehrte fatigue_v2 die zweiseitige Tabelle SELBST, waehrend der
# Kommentar ueber `T90` behauptete, es gebe nur eine. Beide stehen jetzt in
# const.py. Verhalten darf sich dabei NICHT aendern.
import const as _C  # noqa: E402
import inspect as _insp  # noqa: E402
check("B1: die einseitige Tabelle kommt aus const", bool(v2.T90 is _C.T90_ONE_SIDED), True)
check("B2: die zweiseitige kommt aus derselben Stelle", bool(v2.T90_TWO_SIDED is _C.T90_TWO_SIDED), True)
check("B3: der alte Name zeigt auf die einseitige, er fuehrt keine zweite Liste", bool(_C.STEERING_T90 is _C.T90_ONE_SIDED), True)
check("B4: und beide Quantile sind noch verschieden",
      (_C.T90_ONE_SIDED[3], _C.T90_TWO_SIDED[3]), (1.638, 2.353))
# KEINE ZWEITE LISTE MEHR IM MODUL. Das ist die eigentliche Bauregel - ein
# Zeiger ist erlaubt, eine zweite Zahlenreihe nicht.
_srcB = _insp.getsource(v2)
check("B5: fatigue_v2 fuehrt keine eigene Zahlenreihe mehr", bool("6.314" not in _srcB and "2.353" not in _srcB and "1.886" not in _srcB), True)
check("B6: und der Kommentar behauptet nicht mehr, es gebe nur eine Tabelle", bool("Keine zweite Quelle" not in _srcB), True)
# ZUSICHERUNG: DIE ZAHLEN BEIDER KACHELN BLEIBEN BITGLEICH. Die Quantile
# unten stehen von Hand da - so prueft sich der Code nicht gegen sich selbst.
_werteB = [258.0, 251.0, 236.0, 250.0]
_mB = sum(_werteB) / 4
_sdB = (sum((x - _mB) ** 2 for x in _werteB) / 3) ** 0.5
check("B7 Blockband bitgleich (einseitig, t=1,638)",
      round(_C.T90_ONE_SIDED[3] * _sdB * (1 + 1 / 4) ** 0.5, 2),
      round(1.638 * _sdB * (1 + 1 / 4) ** 0.5, 2))
check("B8 Ermuedungsband bitgleich (zweiseitig, t=2,353)",
      v2.reversal_band(_werteB)["from_spread"],
      round(2.353 * _sdB * (1 + 1 / 4) ** 0.5, 1))
check("B9 Trefferzusicherung: die zwei Quantile ergeben verschiedene Breiten", bool(round(1.638 * _sdB * (1 + 1 / 4) ** 0.5, 1) != v2.reversal_band(_werteB)["from_spread"]), True)


# ═══ 0.67.0 · DAS UMRECHNUNGS-PAKET (Entscheidung 23.09.) ═══════════════════
# Rote Pruefungen an 0.66.3. Die Fixture stellt Umkehrung und Bruecken direkt:
# `reversal(data, today)` liest ramp_tests und blocks.series - hier gestubbt,
# damit die Leiter (Tempo+SweetSpot) und der Stufentest bekannte Zahlen tragen.
import blocks as _bl  # noqa: E402
import ramp_tests as _rt  # noqa: E402
_LIVE_RAMP = {"date": "2026-09-16", "result": {"hrvt1": {"alpha": 0.75, "watts": 213.0, "seconds": 1630},
                                                "hrvt1_pers": {"alpha": 1.081, "watts": 183.0, "seconds": 1324},
                                                "hrvt2": {"alpha": 0.5, "watts": 233.0, "seconds": 1861}}}
def _fam(pts): return {"points": [{"block_alphas": a, "block_watts": w} for a, w in pts]}
_LIVE_FAMS = {"vo2max": _fam([([1.032, 0.571, 0.497, 0.409, 0.477], [278, 264, 260, 256, 246]),
                              ([0.426, 0.399, 0.338, 0.431], [260, 251, 236, 230])]),
              "sweetspot": _fam([([0.651, 0.657], [188, 167]), ([0.809, 0.696], [194, 189]), ([0.73, 0.68], [194, 190]),
                                 ([0.915, 0.699], [194, 192]), ([0.869, 0.658], [198, 194])]),
              "tempo": _fam([([1.346, 0.868], [172, 169])])}
_series_saved, _latest_saved = _bl.series, _rt.latest
def _stell(fams, ramp):
    _bl.series = lambda data, with_other=False: {"families": fams}
    _rt.latest = lambda data: ramp
# Stundenzeilen wie am Livebestand (load_w / alpha je Stunde, n Fahrten)
_STD = {1: (139.6, 1.336, 18), 2: (139.6, 1.259, 13), 3: (139.8, 1.107, 4), 4: (138.7, 1.078, 3), 5: (146.8, 0.834, 1)}
def _rows():
    out = []
    for i in range(18):
        hours = [{"hour": h, "alpha": a, "load_w": w} for h, (w, a, n) in _STD.items() if i < n]
        out.append({"activity_id": f"R{i}", "date": "2026-08-01", "hours": hours, "first": hours[0]["alpha"], "last": hours[-1]["alpha"]})
    return out
_rr_saved = v2.reading_rows
v2.reading_rows = lambda data: _rows()

print("\n=== U1. DIE LEITER FAELLT WEG: nur der Stufentest rechnet ===")
_stell(_LIVE_FAMS, _LIVE_RAMP)
_br = v2.bridges_alpha({}, today="2026-09-24")
check("U1 Fixture: der Stufentest ergibt 90,6", _br.get("ramp"), 90.6)
check("U1 Fixture: die Leiter (Tempo+SweetSpot) ergibt 111,7", _br.get("ladder"), 111.7)
check("U1 Treffer: verwendet wird der Stufentest allein", _br.get("mid"), 90.6)
check("U1 Treffer: keine Spanne zwischen zwei Quellen mehr", _br.get("spread") in (None, 0, 0.0), True)
check("U1 Treffer: die Quelle heisst Stufentest, sonst nichts", _br.get("sources"), ["Stufentest"])
_rv = v2.reversal({}, today="2026-09-24")
check("U1 Kette am Livebestand: 170,0 / 163,1 / 149,5 / 145,8 / 131,8",
      [r["watts"] for r in _rv["plan"][:5]], [170.0, 163.1, 149.5, 145.8, 131.8])
check("U1: das Band traegt keinen Bruecken-Anteil mehr",
      {(r["band"] or {}).get("from_bridge") for r in _rv["plan"] if r.get("band")}, {0.0})
check("U1: 0,1 alpha sind rund 9,1 W", _rv.get("floor_step_watts"), 9.1)
# Randfall: kein Stufentest -> KEIN Rueckfall auf die Leiter, keine Wattzahl, die Kachel sagt es
_stell(_LIVE_FAMS, None)
_br0 = v2.bridges_alpha({}, today="2026-09-24")
check("U1 Randfall ohne Stufentest: keine Umrechnung", _br0.get("mid"), None)
check("U1 Randfall ohne Stufentest: die Leiter rechnet NICHT ein", _br0.get("ladder") == 111.7 and _br0.get("mid") is None, True)
check("U1 Randfall ohne Stufentest: der Grund steht dran", bool(_br0.get("missing")), True)
_rv0 = v2.reversal({}, today="2026-09-24")
check("U1 Randfall ohne Stufentest: der Verlauf in alpha bleibt sichtbar (Stunden mit alpha, ohne Watt)",
      [(r["hours"], r["alpha"], r["watts"]) for r in _rv0["plan"][:2]], [(1, 1.336, None), (2, 1.259, None)])

print("\n=== U2. DIE LEITER ALS GEGENPROBE: sichtbar, ohne eine Kachelzahl zu beruehren ===")
_stell(_LIVE_FAMS, _LIVE_RAMP)
_brL = v2.bridges_alpha({}, today="2026-09-24")
check("U2: die Leiter steht mit ihrer Zahl im Rechenweg", _brL.get("ladder"), 111.7)
check("U2: ... und mit dem Satz, warum sie nicht rechnet", bool(_brL.get("ladder_note")), True)
# Stoerungsprobe: die Leiter um das Doppelte verschoben -> keine Kachelzahl bewegt sich
_fams2 = dict(_LIVE_FAMS); _fams2["tempo"] = _fam([([1.346, 0.868], [172, 120])])
_stell(_fams2, _LIVE_RAMP)
_rv2 = v2.reversal({}, today="2026-09-24")
check("U2 Stoerung: eine andere Leiter aendert keine Wattzahl",
      [r["watts"] for r in _rv2["plan"][:5]], [170.0, 163.1, 149.5, 145.8, 131.8])
check("U2 Stoerung: ... aber die Gegenprobe zeigt es", _rv2["bridges"].get("ladder") != 111.7, True)

print("\n=== U3. DIE UMRECHNUNG IST EINE SETZUNG ===")
_stell(_LIVE_FAMS, _LIVE_RAMP)
_rv3 = v2.reversal({}, today="2026-09-24")
check("U3: keine Zeile traegt mehr `measured`", any("measured" in r for r in _rv3["plan"]), False)
check("U3: belegte Stunden heissen `observed`, fortgeschriebene nicht",
      ([r.get("observed") for r in _rv3["plan"][:5]], _rv3["plan"][-1].get("observed")), ([True] * 5, False))
check("U3: die Umrechnung heisst Setzung", "Setzung" in v2.REVERSAL_WORDS["state"] and "gemessen" not in v2.REVERSAL_WORDS["state"], True)
check("U3: der Rechenweg nennt die vier Arbeiten", all(n in v2.REVERSAL_WORDS.get("literature", "")
      for n in ("Rassel", "Gronwald", "Ajayi", "Rogers")), True)
check("U3: die Setzung steht in den Setzungen der Kachel", any("Stufentest" in x and "Setzung" in x for x in v2.SETTINGS_NOTE), True)
check("U3: die Zahl der Rampe ist beschriftet (Datum, Rampe, Strecke)",
      all(k in _rv3["bridges"] for k in ("ramp_date", "ramp_note")), True)

print("\n=== U4. VERFALL: sechs Monate ohne Stufentest ===")
check("U4: die Frist ist eine benannte Konstante", getattr(v2, "RAMP_BRIDGE_MAX_AGE_MONTHS", None), 6)
_stell(_LIVE_FAMS, _LIVE_RAMP)
_vor = v2.reversal({}, today="2027-03-15")
_nach = v2.reversal({}, today="2027-03-16")
check("U4 knapp davor (15.03.2027): die Kette steht", [r["watts"] for r in _vor["plan"][:2]], [170.0, 163.1])
check("U4 am Stichtag (16.03.2027): keine Wattzahl mehr", [r["watts"] for r in _nach["plan"][:2]], [None, None])
check("U4 am Stichtag: der Verlauf in alpha bleibt", [r["alpha"] for r in _nach["plan"][:2]], [1.336, 1.259])
check("U4 am Stichtag: die Kachel sagt, dass ein Test fehlt", "expired" in str(_nach["bridges"].get("missing")) or bool(_nach["bridges"].get("ramp_expired")), True)
check("U4 Gegenprobe: ein frischer Test hebt den Verfall auf",
      [r["watts"] for r in (_stell(_LIVE_FAMS, {**_LIVE_RAMP, "date": "2027-03-10"}) or v2.reversal({}, today="2027-03-16"))["plan"][:1]], [170.0])

print("\n=== U5. TEMPO: gemessen, traegt nichts ===")
_stell({"vo2max": _LIVE_FAMS["vo2max"], "sweetspot": _LIVE_FAMS["sweetspot"]}, _LIVE_RAMP)
_rv5 = v2.reversal({}, today="2026-09-24")
check("U5 Randfall Tempo nicht markiert: dieselbe Kette", [r["watts"] for r in _rv5["plan"][:2]], [170.0, 163.1])
_stell({"sweetspot": _LIVE_FAMS["sweetspot"]}, _LIVE_RAMP)
_rv5b = v2.reversal({}, today="2026-09-24")
check("U5 Randfall nur eine Familie markiert: dieselbe Kette, Leiter leer",
      ([r["watts"] for r in _rv5b["plan"][:2]], _rv5b["bridges"].get("ladder")), ([170.0, 163.1], None))
_bl.series, _rt.latest, v2.reading_rows = _series_saved, _latest_saved, _rr_saved


# ═══ 0.68.0 · DIE GA-EINHEIT LIEST DIE UMKEHRUNG (Entscheidung 24.09.) ══════════
# Ziel = Last + (alpha - ZIEL_ALPHA) x Umrechnung, Grenze = Last + (alpha - 1,0) x
# Umrechnung - EIN Erzeuger mit der Kachel. Die alpha-Werte sind EINSTELLUNGEN
# (Options-Flow), nicht Code. Rot an 0.67.4. Livezahlen als Sollwerte.
_stell(_LIVE_FAMS, _LIVE_RAMP)
v2.reading_rows = lambda data: _rows()
_ga = v2.ga_targets({}, today="2026-09-24", limit_alpha=1.0, target_alpha=1.3)
check("GA: der Erzeuger ist die Umkehrung (mid 90,6)", _ga.get("mid"), 90.6)
check("GA Livebestand, Ziel 1,3 / Grenze 1,0 je Stunde 1-4",
      [(r["hours"], r["target_w"], r["limit_w"], r["n"]) for r in _ga["hours"][:4]],
      [(1, 142.9, 170.0, 18), (2, 135.9, 163.1, 13), (3, 122.3, 149.5, 4), (4, 118.6, 145.8, 3)])
check("GA Probe: bei 1 h haelt er 139,6 W bei alpha 1,336 - das Ziel liegt daneben, nicht darauf",
      _ga["hours"][0]["load_w"] == 139.6 and _ga["hours"][0]["alpha"] == 1.336 and 140 <= _ga["hours"][0]["target_w"] <= 146, True)
_nur = v2.ga_targets({}, today="2026-09-24", limit_alpha=1.0, target_alpha=None)
check("GA ohne Ziel: nur die Grenze, kein Ziel", [(r["target_w"], r["limit_w"]) for r in _nur["hours"][:1]], [(None, 170.0)])
_stell(_LIVE_FAMS, None)
check("GA ohne Stufentest: keine Zahlen, Grund dabei", (v2.ga_targets({}, today="2026-09-24", limit_alpha=1.0, target_alpha=1.3)["hours"], bool(v2.ga_targets({}, today="2026-09-24", limit_alpha=1.0, target_alpha=1.3).get("missing"))), ([], True))
_stell(_LIVE_FAMS, _LIVE_RAMP)
check("GA: die Woerter nennen die Setzung und die alpha-Regel des Athleten",
      "Setzung" in v2.GA_WORDS["state"] and "0,75" in v2.GA_WORDS["literature"], True)
_bl.series, _rt.latest, v2.reading_rows = _series_saved, _latest_saved, _rr_saved

print(f"test_fatigue_v2: {CHECKS} Prüfungen, {len(failures)} Fehler")
print("FEHLER:", failures if failures else "keine")
sys.exit(1 if failures else 0)
