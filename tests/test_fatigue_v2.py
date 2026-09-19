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
check("Der Hinweis nennt die Neumessung mit Zahlen",
      ("58" in v2.SWITCH_NOTE and "28" in v2.SWITCH_NOTE), True)

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
check("Setzungen: alle sechs stehen in der Liste", len(v2.SETTINGS_NOTE), 6)
check("Setzungen: der Stundenschnitt ist als quellenlos benannt",
      any("keine Quelle" in line for line in v2.SETTINGS_NOTE), True)
check("Setzungen: die Umrechnung steht mit ihrer Spanne da",
      any("0,9 bis 7,7" in line for line in v2.SETTINGS_NOTE), True)
check("Setzungen: die quadratische Zusammenlegung ist benannt",
      any("quadratisch" in line for line in v2.SETTINGS_NOTE), True)

print()
print(f"test_fatigue_v2: {CHECKS} Prüfungen, {len(failures)} Fehler")
print("FEHLER:", failures if failures else "keine")
sys.exit(1 if failures else 0)
